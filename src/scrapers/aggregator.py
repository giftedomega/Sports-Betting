"""Data aggregator combining all scraper sources."""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional

from src.scrapers.fbref_scraper import FBrefScraper
from src.scrapers.news_scraper import NewsScraper
from src.scrapers.sofascore_scraper import SofaScoreScraper
from src.scrapers.scraperfc_sofascore import ScraperFCSofaScore
from src.scrapers.odds_scraper import OddsScraper
from src.scrapers.injury_scraper import InjuryScraper
from src.scrapers.weather_scraper import WeatherScraper
from src.database.persistence import DatabasePersistence
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)


class DataAggregator:
    """Aggregates data from all scraper sources with database persistence."""

    def __init__(self, use_db: bool = True):
        config = get_config()
        self.fbref = FBrefScraper()
        self.news = NewsScraper()
        self.sofascore = SofaScoreScraper()
        self.scraperfc = ScraperFCSofaScore()
        self.odds = OddsScraper()
        self.injuries = InjuryScraper()
        self.weather = WeatherScraper()
        self.use_db = use_db
        self._intelligence = None

        logger.info("DataAggregator initialized with all scrapers")

        if use_db:
            try:
                self.db = DatabasePersistence()
            except Exception as e:
                logger.warning(f"Database initialization failed: {e}")
                self.db = None
                self.use_db = False

    @property
    def intelligence(self):
        """Lazy-load intelligence pipeline."""
        if self._intelligence is None:
            try:
                from src.llm.intelligence import IntelligencePipeline
                self._intelligence = IntelligencePipeline()
            except Exception as e:
                logger.warning(f"Intelligence pipeline unavailable: {e}")
        return self._intelligence

    # ── Fixtures ───────────────────────────────────────────

    async def get_upcoming_fixtures(self, days: int = 7) -> List[Dict]:
        """Get upcoming fixtures with enriched data."""
        now = datetime.now()
        upcoming = []
        all_fixtures = []

        try:
            logger.info("[AGGREGATOR] Fetching fixtures from ScraperFC...")
            scraperfc_fixtures = await self.scraperfc.fetch_fixtures(days=days)
            if scraperfc_fixtures:
                logger.info(f"[AGGREGATOR] ScraperFC returned {len(scraperfc_fixtures)} total fixtures")
                all_fixtures = scraperfc_fixtures

                for fixture in scraperfc_fixtures:
                    match_date = fixture.get("match_date")
                    status = fixture.get("status", "")
                    if status == "scheduled" or (match_date and match_date > now):
                        days_until = (match_date - now).days if match_date else 0
                        if days_until <= days:
                            upcoming.append(fixture)

                logger.info(f"[AGGREGATOR] ScraperFC has {len(upcoming)} upcoming fixtures")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] ScraperFC fixtures failed: {e}")

        if not upcoming:
            try:
                logger.info("[AGGREGATOR] No upcoming from ScraperFC, trying FBref...")
                fbref_fixtures = await self.fbref.fetch_fixtures()
                if fbref_fixtures:
                    logger.info(f"[AGGREGATOR] FBref returned {len(fbref_fixtures)} total fixtures")
                    if not all_fixtures:
                        all_fixtures = fbref_fixtures

                    for fixture in fbref_fixtures:
                        match_date = fixture.get("match_date")
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
                self.db.log_scraping("aggregator", "fixtures", "success", len(all_fixtures))
            except Exception as e:
                logger.error(f"Failed to persist fixtures: {e}")

        # Populate H2H from finished fixtures
        if all_fixtures:
            await self._populate_h2h(all_fixtures)

        logger.info(f"[AGGREGATOR] Returning {len(upcoming)} upcoming fixtures within {days} days")
        return upcoming

    # ── Team Stats ─────────────────────────────────────────

    async def get_team_stats(self) -> List[Dict]:
        """Get team statistics from all sources. FBref is PRIMARY."""
        teams = []

        try:
            logger.info("[AGGREGATOR] Fetching team stats from FBref (primary)")
            teams = await self.fbref.fetch_team_stats()
            if teams:
                logger.info(f"[AGGREGATOR] FBref returned {len(teams)} teams")
                if self.use_db and self.db:
                    try:
                        self.db.save_teams(teams)
                        self.db.log_scraping("fbref", "team_stats", "success", len(teams))
                    except Exception as e:
                        logger.error(f"Failed to persist team stats: {e}")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] FBref team stats failed: {e}")

        # Enrich with ScraperFC advanced stats
        try:
            logger.info("[AGGREGATOR] Fetching advanced stats from ScraperFC")
            scraperfc_teams = await self.scraperfc.fetch_team_stats()
            if scraperfc_teams and teams:
                advanced_by_name = {t.get("name", "").lower(): t for t in scraperfc_teams}
                for team in teams:
                    team_name_lower = team.get("name", "").lower()
                    advanced = advanced_by_name.get(team_name_lower)
                    if advanced:
                        team["shots"] = advanced.get("shots", 0)
                        team["shots_on_target"] = advanced.get("shots_on_target", 0)
                        team["possession"] = advanced.get("possession", 0)
                        team["clean_sheets"] = advanced.get("clean_sheets", 0)
                        team["avg_rating"] = advanced.get("avg_rating", 0)
                logger.info("[AGGREGATOR] Enriched teams with ScraperFC advanced stats")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] ScraperFC advanced stats failed: {e}")

        # Enrich with xG data from FBref
        try:
            xg_data = await self.fbref.fetch_advanced_stats()
            if xg_data and teams:
                xg_by_team = {}
                for p in xg_data:
                    team_name = p.get("team", "")
                    if team_name not in xg_by_team:
                        xg_by_team[team_name] = {"xg": 0, "xa": 0}
                    xg_by_team[team_name]["xg"] += p.get("xg", 0) or 0
                    xg_by_team[team_name]["xa"] += p.get("xa", 0) or 0

                for team in teams:
                    name = team.get("name", "")
                    if name in xg_by_team:
                        team["team_xg"] = round(xg_by_team[name]["xg"], 2)

                if self.use_db and self.db:
                    self.db.save_teams(teams)
                logger.info("[AGGREGATOR] Enriched teams with xG data")
        except Exception as e:
            logger.warning(f"[AGGREGATOR] xG enrichment failed: {e}")

        if not teams:
            try:
                logger.info("[AGGREGATOR] FBref failed, falling back to ScraperFC")
                teams = await self.scraperfc.fetch_team_stats()
                if self.use_db and self.db:
                    self.db.save_teams(teams)
            except Exception as e:
                logger.error(f"[AGGREGATOR] Both sources failed: {e}")

        # Process through intelligence pipeline
        if teams and self.intelligence:
            try:
                await self.intelligence.process_team_stats_batch(teams)
            except Exception as e:
                logger.warning(f"[AGGREGATOR] Intelligence processing failed: {e}")

        return teams

    # ── Player Stats ───────────────────────────────────────

    async def get_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Get player statistics."""
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
            logger.warning(f"ScraperFC player stats failed, falling back to FBref: {e}")

        players = await self.fbref.fetch_player_stats(team_name)
        if self.use_db and self.db and not team_name:
            try:
                self.db.save_players(players)
                self.db.log_scraping("fbref", "player_stats", "success", len(players))
            except Exception as e:
                logger.error(f"Failed to persist player stats: {e}")
        return players

    # ── Odds ───────────────────────────────────────────────

    async def get_odds(self) -> List[Dict]:
        """Get latest odds for upcoming matches."""
        try:
            odds_data = await self.odds.fetch_odds()
            if odds_data and self.use_db and self.db:
                self.db.save_odds(odds_data)
                self.db.log_scraping("odds_api", "odds", "success", len(odds_data))

            # Process through intelligence pipeline
            if odds_data and self.intelligence:
                try:
                    await self.intelligence.process_odds_batch(odds_data)
                except Exception as e:
                    logger.warning(f"[AGGREGATOR] Odds intelligence failed: {e}")

            return odds_data
        except Exception as e:
            logger.error(f"[AGGREGATOR] Odds fetch failed: {e}")
            return []

    # ── Injuries ───────────────────────────────────────────

    async def get_injuries(self) -> List[Dict]:
        """Get latest injury/availability data."""
        try:
            injury_data = await self.injuries.fetch_injuries()
            if injury_data and self.use_db and self.db:
                self.db.save_injuries(injury_data)
                self.db.log_scraping("fpl", "injuries", "success", len(injury_data))
            return injury_data
        except Exception as e:
            logger.error(f"[AGGREGATOR] Injuries fetch failed: {e}")
            return []

    # ── Weather ────────────────────────────────────────────

    async def get_weather(self, fixtures: List[Dict] = None) -> List[Dict]:
        """Get weather for upcoming fixtures."""
        if not fixtures:
            if self.use_db and self.db:
                fixtures = self.db.get_upcoming_fixtures(days=7)
        if not fixtures:
            return []

        try:
            weather_data = await self.weather.fetch_fixtures_weather(fixtures)
            if weather_data and self.use_db and self.db:
                self.db.save_weather(weather_data)
                self.db.log_scraping("weather", "forecast", "success", len(weather_data))
            return weather_data
        except Exception as e:
            logger.error(f"[AGGREGATOR] Weather fetch failed: {e}")
            return []

    # ── News ───────────────────────────────────────────────

    async def get_news(self) -> List[Dict]:
        """Get latest news from all sources."""
        articles = await self.news.fetch_news()

        if self.use_db and self.db:
            try:
                saved = self.db.save_news(articles)
                self.db.log_scraping("rss", "news", "success", saved)
            except Exception as e:
                logger.error(f"Failed to persist news: {e}")

        # Process through intelligence pipeline
        if articles and self.intelligence:
            try:
                await self.intelligence.process_news_batch(articles)
            except Exception as e:
                logger.warning(f"[AGGREGATOR] News intelligence failed: {e}")

        return articles

    async def get_team_news(self, team_name: str) -> List[Dict]:
        """Get news for a specific team."""
        return await self.news.fetch_team_news(team_name)

    # ── Match Context ──────────────────────────────────────

    async def get_match_context(self, home_team: str, away_team: str) -> Dict:
        """Get full context for a match for AI analysis."""
        # Fetch all data in parallel
        team_stats, home_news, away_news, lineups, odds_data, injuries_data = await asyncio.gather(
            self.get_team_stats(),
            self.get_team_news(home_team),
            self.get_team_news(away_team),
            self.get_predicted_lineups(home_team, away_team),
            self.get_odds(),
            self.get_injuries(),
        )

        # Find team stats
        home_data = next((t for t in team_stats if t["name"] == home_team), {"name": home_team})
        away_data = next((t for t in team_stats if t["name"] == away_team), {"name": away_team})

        # Get odds for this specific match
        match_odds = None
        for o in odds_data:
            if o.get("home_team") == home_team and o.get("away_team") == away_team:
                match_odds = o
                break

        # Build injuries dict
        injuries = {"home": [], "away": []}
        for inj in injuries_data:
            desc = f"{inj['name']} ({inj.get('injury_description', 'unavailable')})"
            if inj.get("team") == home_team:
                injuries["home"].append(desc)
            elif inj.get("team") == away_team:
                injuries["away"].append(desc)

        # Get weather
        weather = None
        if self.use_db and self.db:
            fixtures = self.db.get_upcoming_fixtures(days=14)
            for f in fixtures:
                if f.get("home_team") == home_team and f.get("away_team") == away_team:
                    if f.get("temperature") is not None:
                        weather = {
                            "temperature": f["temperature"],
                            "precipitation_prob": f.get("precipitation_prob"),
                            "wind_speed": f.get("wind_speed"),
                        }
                    break

        # Combine news
        all_news = sorted(
            home_news[:5] + away_news[:5],
            key=lambda x: x.get("published_at") or datetime.min,
            reverse=True
        )[:10]

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_team_data": home_data,
            "away_team_data": away_data,
            "lineups": lineups,
            "news_context": all_news,
            "odds_data": match_odds,
            "injuries": injuries,
            "weather": weather,
            "fetched_at": datetime.now().isoformat()
        }

    # ── Lineups ────────────────────────────────────────────

    async def get_predicted_lineups(self, home_team: str, away_team: str) -> Dict:
        """Get predicted or confirmed lineups for a match."""
        try:
            sofascore_lineups = await self.sofascore.fetch_predicted_lineups(home_team, away_team)
            if sofascore_lineups.get("confirmed"):
                logger.info(f"Got confirmed lineups from SofaScore for {home_team} vs {away_team}")
                return {
                    "home_team": home_team, "away_team": away_team,
                    "home_formation": sofascore_lineups.get("home_formation", "4-3-3"),
                    "away_formation": sofascore_lineups.get("away_formation", "4-3-3"),
                    "home_probable_xi": sofascore_lineups.get("home_lineup", []),
                    "away_probable_xi": sofascore_lineups.get("away_lineup", []),
                    "home_subs": sofascore_lineups.get("home_subs", []),
                    "away_subs": sofascore_lineups.get("away_subs", []),
                    "confidence": 95, "is_predicted": False, "source": "sofascore"
                }
        except Exception as e:
            logger.warning(f"SofaScore lineup fetch failed: {e}")

        home_players = await self.get_player_stats(home_team)
        away_players = await self.get_player_stats(away_team)
        home_players.sort(key=lambda x: x.get("appearances", 0), reverse=True)
        away_players.sort(key=lambda x: x.get("appearances", 0), reverse=True)

        return {
            "home_team": home_team, "away_team": away_team,
            "home_formation": self._get_default_formation(home_team),
            "away_formation": self._get_default_formation(away_team),
            "home_probable_xi": home_players[:11],
            "away_probable_xi": away_players[:11],
            "confidence": 60, "is_predicted": True, "source": "fbref_stats"
        }

    # ── H2H ────────────────────────────────────────────────

    async def _populate_h2h(self, fixtures: List[Dict]):
        """Populate H2H records from finished fixtures."""
        if not self.use_db or not self.db:
            return

        h2h_records = []
        for f in fixtures:
            if f.get("home_score") is not None and f.get("away_score") is not None:
                home = f.get("home_team", "")
                away = f.get("away_team", "")
                hs = f["home_score"]
                As = f["away_score"]
                winner = home if hs > As else (away if As > hs else "draw")
                h2h_records.append({
                    "team_a": home, "team_b": away,
                    "match_date": f.get("match_date"),
                    "venue": f.get("venue"),
                    "team_a_score": hs, "team_b_score": As,
                    "winner": winner,
                })

        if h2h_records:
            try:
                saved = self.db.save_h2h(h2h_records)
                if saved:
                    logger.info(f"[AGGREGATOR] Populated {saved} H2H records")
            except Exception as e:
                logger.warning(f"[AGGREGATOR] H2H population failed: {e}")

    # ── Refresh All ────────────────────────────────────────

    async def refresh_all_data(self) -> Dict:
        """Refresh all data sources and persist to database."""
        results = {
            "fixtures": 0, "teams": 0, "players": 0,
            "news": 0, "odds": 0, "injuries": 0, "weather": 0,
            "errors": [], "db_persisted": self.use_db
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

        try:
            odds_data = await self.get_odds()
            results["odds"] = len(odds_data)
        except Exception as e:
            results["errors"].append(f"odds: {str(e)}")

        try:
            injury_data = await self.get_injuries()
            results["injuries"] = len(injury_data)
        except Exception as e:
            results["errors"].append(f"injuries: {str(e)}")

        try:
            weather_data = await self.get_weather()
            results["weather"] = len(weather_data)
        except Exception as e:
            results["errors"].append(f"weather: {str(e)}")

        results["refreshed_at"] = datetime.now().isoformat()
        logger.info(f"Data refresh complete: {results}")
        return results

    def get_from_database(self) -> Dict:
        """Get all data from database."""
        if not self.use_db or not self.db:
            return {"error": "Database not available"}
        return {
            "teams": self.db.get_teams(),
            "fixtures": self.db.get_upcoming_fixtures(),
            "predictions": self.db.get_recent_predictions()
        }

    def _get_default_formation(self, team_name: str) -> str:
        formations = {
            "Manchester City": "4-3-3", "Arsenal": "4-3-3", "Liverpool": "4-3-3",
            "Manchester United": "4-2-3-1", "Chelsea": "4-2-3-1", "Tottenham": "4-3-3",
            "Newcastle": "4-3-3", "Brighton": "4-2-3-1", "Aston Villa": "4-2-3-1",
            "West Ham": "4-2-3-1", "Brentford": "4-3-3", "Crystal Palace": "4-3-3",
            "Fulham": "4-2-3-1", "Wolves": "3-4-3", "Wolverhampton": "3-4-3",
            "Bournemouth": "4-4-2", "Nottingham Forest": "4-2-3-1",
            "Everton": "4-4-2", "Leicester": "4-2-3-1",
            "Southampton": "4-4-2", "Ipswich": "4-2-3-1",
        }
        return formations.get(team_name, "4-3-3")

    async def close(self):
        """Close all scrapers."""
        await self.news.close()
        await self.sofascore.close()
        await self.scraperfc.close()
        await self.odds.close()
        await self.injuries.close()
        await self.weather.close()
