"""SofaScore scraper using ScraperFC library for comprehensive football data."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from concurrent.futures import ThreadPoolExecutor

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Premier League identifier for ScraperFC
PREMIER_LEAGUE = "England Premier League"


class ScraperFCSofaScore(BaseScraper):
    """Comprehensive SofaScore scraper using ScraperFC library."""

    def __init__(self):
        """Initialize ScraperFC SofaScore scraper."""
        # 30 second rate limit to avoid Cloudflare blocks
        super().__init__(rate_limit_seconds=30)
        self._scraper = None
        self._executor = ThreadPoolExecutor(max_workers=1)
        self._current_season = None
        logger.info("Initialized ScraperFC SofaScore scraper")

    @property
    def scraper(self):
        """Lazy load ScraperFC Sofascore."""
        if self._scraper is None:
            try:
                from ScraperFC import Sofascore
                self._scraper = Sofascore()
                logger.info("ScraperFC Sofascore initialized")
            except ImportError:
                logger.error("ScraperFC not installed. Run: pip install ScraperFC")
                raise
        return self._scraper

    def _get_current_season(self) -> str:
        """Get current Premier League season in YY/YY format (e.g., '24/25')."""
        if self._current_season:
            return self._current_season

        now = datetime.now()
        # Season starts in August, so if before August use previous year as start
        if now.month < 8:
            start_year = now.year - 1
        else:
            start_year = now.year

        end_year = start_year + 1
        # Format as "YY/YY" (e.g., "24/25" for 2024/25 season)
        self._current_season = f"{start_year % 100:02d}/{end_year % 100:02d}"
        return self._current_season

    async def _run_sync(self, func, *args, **kwargs):
        """Run synchronous ScraperFC function in thread pool."""
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(
            self._executor,
            lambda: func(*args, **kwargs)
        )

    async def fetch_fixtures(self, days: int = 14) -> List[Dict]:
        """Fetch Premier League fixtures.

        Args:
            days: Number of days ahead to fetch (used for filtering)

        Returns:
            List of fixture dicts
        """
        cache_key = f"fixtures_{days}"
        cached = self._get_cached(cache_key, CacheConfig.FIXTURES)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            year = self._get_current_season()
            logger.info(f"Fetching EPL fixtures for {year} season from SofaScore")

            # Get all matches for the season
            match_dicts = await self._run_sync(
                self.scraper.get_match_dicts,
                year=year,
                league=PREMIER_LEAGUE
            )

            fixtures = []
            now = datetime.now()
            cutoff = now + timedelta(days=days)

            for match in match_dicts:
                # Parse match date
                match_date = None
                start_time = match.get("startTimestamp")
                if start_time:
                    match_date = datetime.fromtimestamp(start_time)

                # Get team names
                home_team = match.get("homeTeam", {}).get("name")
                away_team = match.get("awayTeam", {}).get("name")

                # Get scores
                home_score = match.get("homeScore", {}).get("current")
                away_score = match.get("awayScore", {}).get("current")

                # Determine status
                status_code = match.get("status", {}).get("code", 0)
                if status_code == 0:
                    status = "scheduled"
                elif status_code == 100:
                    status = "finished"
                else:
                    status = "live"

                fixture = {
                    "sofascore_id": match.get("id"),
                    "home_team": home_team,
                    "away_team": away_team,
                    "match_date": match_date,
                    "home_score": home_score,
                    "away_score": away_score,
                    "status": status,
                    "round": match.get("roundInfo", {}).get("round"),
                    "venue": match.get("venue", {}).get("name") if match.get("venue") else None,
                    "league": "Premier League"
                }
                fixtures.append(fixture)

            # Sort by date
            fixtures.sort(key=lambda x: x.get("match_date") or datetime.max)

            logger.info(f"Fetched {len(fixtures)} total fixtures from SofaScore")
            self._set_cache(cache_key, fixtures)
            return fixtures

        except Exception as e:
            logger.error(f"Failed to fetch fixtures from SofaScore: {e}")
            return []

    async def fetch_team_stats(self) -> List[Dict]:
        """Fetch Premier League team statistics/standings.

        Returns:
            List of team stats dicts
        """
        cache_key = "team_stats"
        cached = self._get_cached(cache_key, CacheConfig.LEAGUE_TABLE)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            year = self._get_current_season()
            logger.info(f"Fetching EPL team stats for {year} season from SofaScore")

            # Get team league stats
            team_stats_df = await self._run_sync(
                self.scraper.scrape_team_league_stats,
                year=year,
                league=PREMIER_LEAGUE
            )

            teams = []
            if team_stats_df is not None and not team_stats_df.empty:
                # Log column names and index for debugging
                logger.info(f"Team stats DataFrame columns: {list(team_stats_df.columns)}")
                logger.info(f"Team stats DataFrame index names: {team_stats_df.index.names}")
                if len(team_stats_df) > 0:
                    logger.info(f"Sample row index: {team_stats_df.index[0]}")
                    logger.info(f"Sample row data: {team_stats_df.iloc[0].to_dict()}")

                for idx, row in team_stats_df.iterrows():
                    # Convert row to dict for easier access
                    row_dict = row.to_dict()

                    # Team name is in 'teamName' column for ScraperFC
                    team_name = row_dict.get("teamName", "")

                    # Fall back to index if not in columns
                    if not team_name:
                        if isinstance(idx, tuple):
                            team_name = idx[-1] if idx else ""
                        else:
                            team_name = str(idx) if idx else ""

                    # ScraperFC returns advanced stats, not standings
                    # We have goalsScored/goalsConceded but NOT W/D/L/Pts
                    # These will be filled from FBref fallback or database
                    team = {
                        "name": team_name,
                        "played": int(row_dict.get("matches", 0)),
                        "won": 0,  # Not available from ScraperFC team_league_stats
                        "drawn": 0,
                        "lost": 0,
                        "goals_for": int(row_dict.get("goalsScored", 0)),
                        "goals_against": int(row_dict.get("goalsConceded", 0)),
                        "points": 0,  # Not available - need standings endpoint
                        "position": None,
                        # Include advanced stats from SofaScore
                        "shots": int(row_dict.get("shots", 0)),
                        "shots_on_target": int(row_dict.get("shotsOnTarget", 0)),
                        "possession": float(row_dict.get("averageBallPossession", 0)),
                        "clean_sheets": int(row_dict.get("cleanSheets", 0)),
                        "avg_rating": float(row_dict.get("avgRating", 0)),
                    }
                    teams.append(team)

            # Sort by points (descending) then goal difference
            teams.sort(key=lambda x: (x.get("points", 0), x.get("goals_for", 0) - x.get("goals_against", 0)), reverse=True)

            # Assign positions
            for i, team in enumerate(teams, 1):
                if not team.get("position"):
                    team["position"] = i

            logger.info(f"Fetched stats for {len(teams)} teams from SofaScore")
            self._set_cache(cache_key, teams)
            return teams

        except Exception as e:
            logger.error(f"Failed to fetch team stats from SofaScore: {e}")
            return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Fetch Premier League player statistics.

        Args:
            team_name: Optional team filter

        Returns:
            List of player stats dicts
        """
        cache_key = f"players_{team_name or 'all'}"
        cached = self._get_cached(cache_key, CacheConfig.PLAYER_INFO)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            year = self._get_current_season()
            logger.info(f"Fetching EPL player stats for {year} season from SofaScore")

            # Get player league stats (per90 for meaningful comparisons)
            player_stats_df = await self._run_sync(
                self.scraper.scrape_player_league_stats,
                year=year,
                league=PREMIER_LEAGUE,
                accumulation="total"
            )

            players = []
            if player_stats_df is not None and not player_stats_df.empty:
                for _, row in player_stats_df.iterrows():
                    player_team = row.get("team", "")

                    # Filter by team if specified
                    if team_name and team_name.lower() not in player_team.lower():
                        continue

                    player = {
                        "name": row.get("player", row.get("name", "")),
                        "team": player_team,
                        "position": row.get("position", ""),
                        "appearances": int(row.get("appearances", row.get("matches", 0))),
                        "goals": int(row.get("goals", 0)),
                        "assists": int(row.get("assists", 0)),
                        "minutes_played": int(row.get("minutesPlayed", 0)),
                        "yellow_cards": int(row.get("yellowCards", 0)),
                        "red_cards": int(row.get("redCards", 0)),
                        "rating": float(row.get("rating", 0)) if row.get("rating") else None,
                    }
                    players.append(player)

            # Sort by goals then assists
            players.sort(key=lambda x: (x.get("goals", 0), x.get("assists", 0)), reverse=True)

            logger.info(f"Fetched {len(players)} players from SofaScore")
            self._set_cache(cache_key, players)
            return players

        except Exception as e:
            logger.error(f"Failed to fetch player stats from SofaScore: {e}")
            return []

    async def fetch_match_stats(self, match_id: int) -> Optional[Dict]:
        """Fetch detailed stats for a specific match.

        Args:
            match_id: SofaScore match ID

        Returns:
            Match stats dict
        """
        cache_key = f"match_stats_{match_id}"
        cached = self._get_cached(cache_key, CacheConfig.LIVE_MATCH)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            # Get team match stats
            team_stats = await self._run_sync(
                self.scraper.scrape_team_match_stats,
                match_id
            )

            # Get player match stats
            player_stats = await self._run_sync(
                self.scraper.scrape_player_match_stats,
                match_id
            )

            result = {
                "match_id": match_id,
                "team_stats": team_stats.to_dict() if team_stats is not None else {},
                "player_stats": player_stats.to_dict() if player_stats is not None else {},
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to fetch match stats for {match_id}: {e}")
            return None

    async def fetch_lineups(self, match_id: int) -> Dict:
        """Fetch lineups and average positions for a match.

        Args:
            match_id: SofaScore match ID

        Returns:
            Lineups dict with formations and players
        """
        cache_key = f"lineups_{match_id}"
        cached = self._get_cached(cache_key, CacheConfig.MATCH_DAY_LINEUPS)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            # Get player IDs first
            player_ids = await self._run_sync(
                self.scraper.get_player_ids,
                match_id
            )

            # Get average positions
            positions = await self._run_sync(
                self.scraper.scrape_player_average_positions,
                match_id
            )

            # Get team names
            team_names = await self._run_sync(
                self.scraper.get_team_names,
                match_id
            )

            result = {
                "match_id": match_id,
                "home_team": team_names.get("home") if team_names else None,
                "away_team": team_names.get("away") if team_names else None,
                "player_ids": player_ids.to_dict() if player_ids is not None else {},
                "positions": positions.to_dict() if positions is not None else {},
                "confirmed": True if positions is not None and not positions.empty else False,
            }

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to fetch lineups for match {match_id}: {e}")
            return {"match_id": match_id, "confirmed": False}

    async def fetch_shots(self, match_id: int) -> List[Dict]:
        """Fetch shot data for a match.

        Args:
            match_id: SofaScore match ID

        Returns:
            List of shot dicts with coordinates and outcomes
        """
        await self._rate_limit_wait()

        try:
            shots_df = await self._run_sync(
                self.scraper.scrape_match_shots,
                match_id
            )

            if shots_df is None or shots_df.empty:
                return []

            return shots_df.to_dict("records")

        except Exception as e:
            logger.error(f"Failed to fetch shots for match {match_id}: {e}")
            return []

    async def get_valid_seasons(self) -> Dict:
        """Get available seasons and their IDs.

        Returns:
            Dict mapping years to season IDs
        """
        try:
            seasons = await self._run_sync(
                self.scraper.get_valid_seasons,
                PREMIER_LEAGUE
            )
            return seasons if seasons else {}
        except Exception as e:
            logger.error(f"Failed to get valid seasons: {e}")
            return {}

    async def close(self):
        """Close resources."""
        self._executor.shutdown(wait=False)
