"""Data aggregator combining all scraper sources."""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional

from src.scrapers.fbref_scraper import FBrefScraper
from src.scrapers.news_scraper import NewsScraper
from src.scrapers.sofascore_scraper import SofaScoreScraper
from src.scrapers.scraperfc_sofascore import ScraperFCSofaScore
from src.database.persistence import DatabasePersistence
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)


class DataAggregator:
    """Aggregates data from all scraper sources with database persistence."""

    def __init__(self, use_db: bool = True):
        """Initialize aggregator with all scrapers.

        Args:
            use_db: Whether to persist data to database
        """
        config = get_config()
        self.fbref = FBrefScraper()
        self.news = NewsScraper()
        self.sofascore = SofaScoreScraper()  # For lineups
        self.scraperfc = ScraperFCSofaScore()  # Primary source via ScraperFC
        self.use_db = use_db

        logger.info("Using ScraperFC SofaScore as primary data source")

        if use_db:
            try:
                self.db = DatabasePersistence()
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")
                self.db = None
                self.use_db = False

    async def get_upcoming_fixtures(self, days: int = 7) -> List[Dict]:
        """Get upcoming fixtures with enriched data.

        Args:
            days: Number of days ahead to fetch

        Returns:
            List of fixture dicts with team info
        """
        now = datetime.now()
        upcoming = []
        all_fixtures = []

        # Try ScraperFC SofaScore first
        try:
            logger.info("[AGGREGATOR] Fetching fixtures from ScraperFC...")
            scraperfc_fixtures = await self.scraperfc.fetch_fixtures(days=days)
            if scraperfc_fixtures:
                logger.info(f"[AGGREGATOR] ScraperFC returned {len(scraperfc_fixtures)} total fixtures")
                all_fixtures = scraperfc_fixtures

                # Filter to upcoming/scheduled matches only
                for fixture in scraperfc_fixtures:
                    match_date = fixture.get("match_date")
                    status = fixture.get("status", "")
                    # Include if scheduled OR if date is in future
                    if status == "scheduled" or (match_date and match_date > now):
                        days_until = (match_date - now).days if match_date else 0
                        if days_until <= days:
                            upcoming.append(fixture)

                logger.info(f"[AGGREGATOR] ScraperFC has {len(upcoming)} upcoming fixtures")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] ScraperFC fixtures failed: {e}")

        # If no upcoming fixtures from ScraperFC, fall back to FBref
        if not upcoming:
            try:
                logger.info("[AGGREGATOR] No upcoming from ScraperFC, trying FBref...")
                fbref_fixtures = await self.fbref.fetch_fixtures()
                if fbref_fixtures:
                    logger.info(f"[AGGREGATOR] FBref returned {len(fbref_fixtures)} total fixtures")

                    # Merge with ScraperFC data (prefer ScraperFC if both have the match)
                    if not all_fixtures:
                        all_fixtures = fbref_fixtures

                    # Filter to upcoming
                    for fixture in fbref_fixtures:
                        match_date = fixture.get("match_date")
                        # FBref doesn't have status field, check by scores being None
                        home_score = fixture.get("home_score")
                        away_score = fixture.get("away_score")
                        is_unplayed = home_score is None and away_score is None

                        if match_date and match_date > now and is_unplayed:
                            days_until = (match_date - now).days
                            if days_until <= days:
                                upcoming.append(fixture)

                    logger.info(f"[AGGREGATOR] FBref has {len(upcoming)} upcoming fixtures")
            except Exception as e:
                logger.warning(f"[AGGREGATOR] FBref fixtures also failed: {e}")

        # Persist to database
        if all_fixtures and self.use_db and self.db:
            try:
                self.db.save_fixtures(all_fixtures)
                source = "sofascore" if "sofascore_id" in (all_fixtures[0] if all_fixtures else {}) else "fbref"
                self.db.log_scraping(source, "fixtures", "success", len(all_fixtures))
            except Exception as e:
                logger.error(f"Failed to persist fixtures: {e}")

        logger.info(f"[AGGREGATOR] Returning {len(upcoming)} upcoming fixtures within {days} days")
        return upcoming

    async def get_team_stats(self) -> List[Dict]:
        """Get team statistics from all sources.

        FBref is PRIMARY for league table (has W/D/L/Pts).
        ScraperFC is used for advanced stats enrichment.

        Returns:
            List of team stats dicts
        """
        teams = []

        # Use FBref as PRIMARY for league table (has proper W/D/L/Pts standings)
        try:
            logger.info("[AGGREGATOR] Fetching team stats from FBref (primary for standings)")
            teams = await self.fbref.fetch_team_stats()
            if teams:
                logger.info(f"[AGGREGATOR] FBref returned {len(teams)} teams with standings")
                if self.use_db and self.db:
                    try:
                        self.db.save_teams(teams)
                        self.db.log_scraping("fbref", "team_stats", "success", len(teams))
                    except Exception as e:
                        logger.error(f"Failed to persist team stats: {e}")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] FBref team stats failed: {e}")

        # Try to enrich with ScraperFC advanced stats (shots, possession, etc.)
        try:
            logger.info("[AGGREGATOR] Fetching advanced stats from ScraperFC")
            scraperfc_teams = await self.scraperfc.fetch_team_stats()
            if scraperfc_teams and teams:
                # Build lookup by team name
                advanced_by_name = {t.get("name", "").lower(): t for t in scraperfc_teams}

                for team in teams:
                    team_name_lower = team.get("name", "").lower()
                    advanced = advanced_by_name.get(team_name_lower)
                    if advanced:
                        # Enrich with advanced stats from ScraperFC
                        team["shots"] = advanced.get("shots", 0)
                        team["shots_on_target"] = advanced.get("shots_on_target", 0)
                        team["possession"] = advanced.get("possession", 0)
                        team["clean_sheets"] = advanced.get("clean_sheets", 0)
                        team["avg_rating"] = advanced.get("avg_rating", 0)

                logger.info(f"[AGGREGATOR] Enriched teams with ScraperFC advanced stats")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] ScraperFC advanced stats failed (non-critical): {e}")

        # If FBref failed, try ScraperFC as fallback (won't have W/D/L/Pts but better than nothing)
        if not teams:
            try:
                logger.info("[AGGREGATOR] FBref failed, falling back to ScraperFC")
                teams = await self.scraperfc.fetch_team_stats()
                if self.use_db and self.db:
                    try:
                        self.db.save_teams(teams)
                        self.db.log_scraping("sofascore", "team_stats", "success", len(teams))
                    except Exception as e:
                        logger.error(f"Failed to persist team stats: {e}")
            except Exception as e:
                logger.error(f"[AGGREGATOR] Both FBref and ScraperFC failed: {e}")

        return teams

    async def get_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Get player statistics.

        Args:
            team_name: Optional team filter

        Returns:
            List of player stats dicts
        """
        # Use ScraperFC SofaScore as primary source
        try:
            players = await self.scraperfc.fetch_player_stats(team_name)
            if players:
                if self.use_db and self.db and not team_name:
                    try:
                        self.db.save_players(players)
                        self.db.log_scraping("sofascore", "player_stats", "success", len(players))
                    except Exception as e:
                        logger.error(f"Failed to persist player stats: {e}")
                return players
        except Exception as e:
            logger.warning(f"ScraperFC SofaScore player stats failed, falling back to FBref: {e}")

        # Fallback to FBref
        players = await self.fbref.fetch_player_stats(team_name)

        if self.use_db and self.db and not team_name:
            try:
                self.db.save_players(players)
                self.db.log_scraping("fbref", "player_stats", "success", len(players))
            except Exception as e:
                logger.error(f"Failed to persist player stats: {e}")

        return players

    async def get_news(self) -> List[Dict]:
        """Get latest news from all sources.

        Returns:
            List of news article dicts
        """
        articles = await self.news.fetch_news()

        # Persist to database
        if self.use_db and self.db:
            try:
                saved = self.db.save_news(articles)
                self.db.log_scraping("rss", "news", "success", saved)
            except Exception as e:
                logger.error(f"Failed to persist news: {e}")
                self.db.log_scraping("rss", "news", "failed", 0, str(e))

        return articles

    async def get_team_news(self, team_name: str) -> List[Dict]:
        """Get news for a specific team.

        Args:
            team_name: Team name

        Returns:
            List of news articles mentioning the team
        """
        return await self.news.fetch_team_news(team_name)

    async def get_match_context(
        self,
        home_team: str,
        away_team: str
    ) -> Dict:
        """Get full context for a match for AI analysis.

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Dict containing all relevant match context
        """
        # Fetch all data in parallel
        team_stats_task = self.get_team_stats()
        home_news_task = self.get_team_news(home_team)
        away_news_task = self.get_team_news(away_team)
        lineups_task = self.get_predicted_lineups(home_team, away_team)

        team_stats, home_news, away_news, lineups = await asyncio.gather(
            team_stats_task,
            home_news_task,
            away_news_task,
            lineups_task
        )

        # Find team stats
        home_data = next((t for t in team_stats if t["name"] == home_team), {"name": home_team})
        away_data = next((t for t in team_stats if t["name"] == away_team), {"name": away_team})

        # Combine news
        all_news = []
        all_news.extend(home_news[:5])
        all_news.extend(away_news[:5])

        # Sort news by date
        all_news.sort(
            key=lambda x: x.get("published_at") or datetime.min,
            reverse=True
        )

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_team_data": home_data,
            "away_team_data": away_data,
            "lineups": lineups,
            "news_context": all_news[:10],
            "fetched_at": datetime.now().isoformat()
        }

    async def get_predicted_lineups(
        self,
        home_team: str,
        away_team: str
    ) -> Dict:
        """Get predicted or confirmed lineups for a match.

        Uses SofaScore for real-time lineups, falls back to FBref player stats.

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Dict with predicted/confirmed lineups
        """
        # Try SofaScore first for real-time/confirmed lineups
        try:
            sofascore_lineups = await self.sofascore.fetch_predicted_lineups(home_team, away_team)

            if sofascore_lineups.get("confirmed"):
                logger.info(f"Got confirmed lineups from SofaScore for {home_team} vs {away_team}")
                return {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_formation": sofascore_lineups.get("home_formation", "4-3-3"),
                    "away_formation": sofascore_lineups.get("away_formation", "4-3-3"),
                    "home_probable_xi": sofascore_lineups.get("home_lineup", []),
                    "away_probable_xi": sofascore_lineups.get("away_lineup", []),
                    "home_subs": sofascore_lineups.get("home_subs", []),
                    "away_subs": sofascore_lineups.get("away_subs", []),
                    "confidence": 95,
                    "is_predicted": False,
                    "source": "sofascore"
                }
        except Exception as e:
            logger.warning(f"SofaScore lineup fetch failed: {e}")

        # Fallback to FBref player stats to predict likely starters
        home_players = await self.get_player_stats(home_team)
        away_players = await self.get_player_stats(away_team)

        # Sort by appearances to get likely starters
        home_players.sort(key=lambda x: x.get("appearances", 0), reverse=True)
        away_players.sort(key=lambda x: x.get("appearances", 0), reverse=True)

        # Get default formations based on common team tactics
        home_formation = self._get_default_formation(home_team)
        away_formation = self._get_default_formation(away_team)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_formation": home_formation,
            "away_formation": away_formation,
            "home_probable_xi": home_players[:11],
            "away_probable_xi": away_players[:11],
            "confidence": 60,
            "is_predicted": True,
            "source": "fbref_stats"
        }

    def _get_default_formation(self, team_name: str) -> str:
        """Get default formation for a team based on common tactics.

        Args:
            team_name: Team name

        Returns:
            Formation string
        """
        formations = {
            "Manchester City": "4-3-3",
            "Arsenal": "4-3-3",
            "Liverpool": "4-3-3",
            "Manchester United": "4-2-3-1",
            "Chelsea": "4-2-3-1",
            "Tottenham": "4-3-3",
            "Newcastle": "4-3-3",
            "Brighton": "4-2-3-1",
            "Aston Villa": "4-2-3-1",
            "West Ham": "4-2-3-1",
            "Brentford": "4-3-3",
            "Crystal Palace": "4-3-3",
            "Fulham": "4-2-3-1",
            "Wolves": "3-4-3",
            "Wolverhampton": "3-4-3",
            "Bournemouth": "4-4-2",
            "Nottingham Forest": "4-2-3-1",
            "Everton": "4-4-2",
            "Leicester": "4-2-3-1",
            "Southampton": "4-4-2",
            "Ipswich": "4-2-3-1",
        }
        return formations.get(team_name, "4-3-3")

    async def refresh_all_data(self) -> Dict:
        """Refresh all data sources and persist to database.

        Returns:
            Dict with refresh status and counts
        """
        results = {
            "fixtures": 0,
            "teams": 0,
            "players": 0,
            "news": 0,
            "errors": [],
            "db_persisted": self.use_db
        }

        try:
            teams = await self.get_team_stats()
            results["teams"] = len(teams)
        except Exception as e:
            results["errors"].append(f"teams: {str(e)}")

        try:
            fixtures = await self.get_upcoming_fixtures(days=30)
            results["fixtures"] = len(fixtures)
        except Exception as e:
            results["errors"].append(f"fixtures: {str(e)}")

        try:
            players = await self.get_player_stats()
            results["players"] = len(players)
        except Exception as e:
            results["errors"].append(f"players: {str(e)}")

        try:
            news = await self.get_news()
            results["news"] = len(news)
        except Exception as e:
            results["errors"].append(f"news: {str(e)}")

        results["refreshed_at"] = datetime.now().isoformat()
        logger.info(f"Data refresh complete: {results}")
        return results

    def get_from_database(self) -> Dict:
        """Get all data from database (for faster access).

        Returns:
            Dict with teams, fixtures, predictions from DB
        """
        if not self.use_db or not self.db:
            return {"error": "Database not available"}

        return {
            "teams": self.db.get_teams(),
            "fixtures": self.db.get_upcoming_fixtures(),
            "predictions": self.db.get_recent_predictions()
        }

    async def close(self):
        """Close all scrapers."""
        await self.news.close()
        await self.sofascore.close()
        await self.scraperfc.close()
