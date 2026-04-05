"""SportMonks API scraper for football data."""

from datetime import datetime, timedelta
from typing import List, Dict, Optional

import httpx

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)

# Premier League ID on SportMonks
PREMIER_LEAGUE_ID = 8

# Season ID for 2024/25 Premier League
CURRENT_SEASON_ID = 23614  # Will be fetched dynamically if needed


class SportMonksScraper(BaseScraper):
    """Scraper for SportMonks Football API v3."""

    BASE_URL = "https://api.sportmonks.com/v3/football"

    def __init__(self):
        """Initialize SportMonks scraper."""
        config = get_config()
        super().__init__(rate_limit_seconds=1)  # SportMonks allows more requests

        self.api_key = config.sportmonks.api_key if hasattr(config, 'sportmonks') else None
        if not self.api_key:
            self.api_key = "MWFcyIhPSVKmLnn9OfGcEgzCdRgRgwzwxKTkau70OfmwWI2SOe0HleZRmfd8"

        self._http_client = None
        self._current_season_id = None
        logger.info("Initialized SportMonks scraper")

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                timeout=30.0,
                follow_redirects=True
            )
        return self._http_client

    async def _make_request(self, endpoint: str, params: Dict = None) -> Optional[Dict]:
        """Make authenticated request to SportMonks API.

        Args:
            endpoint: API endpoint path
            params: Query parameters

        Returns:
            JSON response data or None
        """
        await self._rate_limit_wait()

        url = f"{self.BASE_URL}/{endpoint}"
        params = params or {}
        # Add API token as query parameter (SportMonks v3 auth method)
        params["api_token"] = self.api_key

        try:
            response = await self.http_client.get(url, params=params)

            if response.status_code == 200:
                return response.json()
            elif response.status_code == 401:
                logger.error("SportMonks API: Unauthorized - check API key")
            elif response.status_code == 429:
                logger.warning("SportMonks API: Rate limited")
            else:
                logger.error(f"SportMonks API error {response.status_code}: {response.text[:200]}")

            return None

        except Exception as e:
            logger.error(f"SportMonks request failed: {e}")
            return None

    async def _get_current_season_id(self) -> int:
        """Get current Premier League season ID."""
        if self._current_season_id:
            return self._current_season_id

        # Get league info with current season
        data = await self._make_request(
            f"leagues/{PREMIER_LEAGUE_ID}",
            params={"include": "currentSeason"}
        )

        if data and "data" in data:
            league = data["data"]
            current_season = league.get("currentSeason") or league.get("current_season")
            if current_season:
                self._current_season_id = current_season.get("id")
                logger.info(f"Got current Premier League season ID: {self._current_season_id}")
                return self._current_season_id

        # Fallback to hardcoded
        logger.warning("Could not get current season, using fallback")
        return CURRENT_SEASON_ID

    async def fetch_fixtures(self, days: int = 14) -> List[Dict]:
        """Fetch upcoming Premier League fixtures.

        Args:
            days: Number of days ahead to fetch

        Returns:
            List of fixture dicts
        """
        cache_key = f"fixtures_{days}"
        cached = self._get_cached(cache_key, CacheConfig.FIXTURES)
        if cached:
            return cached

        start_date = datetime.now().strftime("%Y-%m-%d")
        end_date = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")

        # Get fixtures by date range for Premier League
        data = await self._make_request(
            f"fixtures/between/{start_date}/{end_date}",
            params={
                "include": "participants;venue;scores;state;round",
                "filters": f"fixtureLeagues:{PREMIER_LEAGUE_ID}",
                "per_page": 50
            }
        )

        if not data or "data" not in data:
            logger.warning("No fixtures data from SportMonks")
            return []

        fixtures = []
        for match in data.get("data", []):
            participants = match.get("participants", [])
            home_team = None
            away_team = None

            for p in participants:
                meta = p.get("meta", {})
                if meta.get("location") == "home":
                    home_team = p.get("name")
                elif meta.get("location") == "away":
                    away_team = p.get("name")

            # Parse scores
            scores = match.get("scores", [])
            home_score = None
            away_score = None
            for score in scores:
                if score.get("description") == "CURRENT":
                    participant_id = score.get("participant_id")
                    for p in participants:
                        if p.get("id") == participant_id:
                            if p.get("meta", {}).get("location") == "home":
                                home_score = score.get("score", {}).get("goals")
                            else:
                                away_score = score.get("score", {}).get("goals")

            # Parse datetime
            starting_at = match.get("starting_at")
            match_date = None
            if starting_at:
                try:
                    match_date = datetime.fromisoformat(starting_at.replace("Z", "+00:00"))
                except:
                    pass

            fixture = {
                "sportmonks_id": match.get("id"),
                "home_team": home_team,
                "away_team": away_team,
                "match_date": match_date,
                "venue": match.get("venue", {}).get("name") if match.get("venue") else None,
                "home_score": home_score,
                "away_score": away_score,
                "status": match.get("state", {}).get("state") if match.get("state") else "scheduled",
                "gameweek": match.get("round_id"),
                "league": "Premier League"
            }
            fixtures.append(fixture)

        logger.info(f"Fetched {len(fixtures)} fixtures from SportMonks")
        self._set_cache(cache_key, fixtures)
        return fixtures

    async def fetch_team_stats(self) -> List[Dict]:
        """Fetch Premier League standings/team stats.

        Returns:
            List of team stats dicts
        """
        cache_key = "team_stats"
        cached = self._get_cached(cache_key, CacheConfig.LEAGUE_TABLE)
        if cached:
            return cached

        # Get current season ID dynamically
        season_id = await self._get_current_season_id()

        # Get current season standings
        data = await self._make_request(
            f"standings/seasons/{season_id}",
            params={"include": "participant;form"}
        )

        if not data or "data" not in data:
            logger.warning("No standings data from SportMonks")
            return []

        teams = []
        standings_data = data.get("data", [])

        # Find the overall standings
        for standing_group in standings_data:
            if standing_group.get("type") == "total" or not standing_group.get("type"):
                for entry in standing_group.get("standings", []):
                    participant = entry.get("participant", {})
                    team = {
                        "sportmonks_id": participant.get("id"),
                        "name": participant.get("name"),
                        "short_name": participant.get("short_code"),
                        "position": entry.get("position"),
                        "played": entry.get("games_played", 0),
                        "won": entry.get("won", 0),
                        "drawn": entry.get("draw", 0),
                        "lost": entry.get("lost", 0),
                        "goals_for": entry.get("goals_scored", 0),
                        "goals_against": entry.get("goals_against", 0),
                        "points": entry.get("points", 0),
                        "form": entry.get("recent_form"),
                    }
                    teams.append(team)

        # If no structured standings, try alternate endpoint
        if not teams:
            data = await self._make_request(
                f"standings/live/leagues/{PREMIER_LEAGUE_ID}",
                params={"include": "participant"}
            )

            if data and "data" in data:
                for entry in data.get("data", []):
                    participant = entry.get("participant", {})
                    team = {
                        "sportmonks_id": participant.get("id"),
                        "name": participant.get("name"),
                        "short_name": participant.get("short_code"),
                        "position": entry.get("position"),
                        "played": entry.get("games_played", 0),
                        "won": entry.get("won", 0),
                        "drawn": entry.get("draw", 0),
                        "lost": entry.get("lost", 0),
                        "goals_for": entry.get("goals_scored", 0),
                        "goals_against": entry.get("goals_against", 0),
                        "points": entry.get("points", 0),
                        "form": entry.get("recent_form"),
                    }
                    teams.append(team)

        logger.info(f"Fetched stats for {len(teams)} teams from SportMonks")
        self._set_cache(cache_key, teams)
        return teams

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Fetch player statistics.

        Args:
            team_name: Optional team filter

        Returns:
            List of player stats dicts
        """
        cache_key = f"players_{team_name or 'all'}"
        cached = self._get_cached(cache_key, CacheConfig.PLAYER_INFO)
        if cached:
            return cached

        # Get current season ID dynamically
        season_id = await self._get_current_season_id()

        # Get top scorers for the league
        data = await self._make_request(
            f"topscorers/seasons/{season_id}",
            params={"include": "player;participant"}
        )

        if not data or "data" not in data:
            return []

        players = []
        for entry in data.get("data", []):
            player_data = entry.get("player", {})
            team_data = entry.get("participant", {})

            if team_name and team_data.get("name", "").lower() != team_name.lower():
                continue

            player = {
                "sportmonks_id": player_data.get("id"),
                "name": player_data.get("display_name") or player_data.get("name"),
                "team": team_data.get("name"),
                "position": entry.get("position"),
                "goals": entry.get("total", 0),
                "assists": 0,  # Would need separate request
                "appearances": 0,
            }
            players.append(player)

        logger.info(f"Fetched {len(players)} players from SportMonks")
        self._set_cache(cache_key, players)
        return players

    async def fetch_fixture_details(self, fixture_id: int) -> Optional[Dict]:
        """Fetch detailed info for a specific fixture.

        Args:
            fixture_id: SportMonks fixture ID

        Returns:
            Fixture details dict
        """
        data = await self._make_request(
            f"fixtures/{fixture_id}",
            params={"include": "participants;venue;lineups;events;statistics"}
        )

        if not data or "data" not in data:
            return None

        return data.get("data")

    async def fetch_lineups(self, fixture_id: int) -> Dict:
        """Fetch lineups for a fixture.

        Args:
            fixture_id: SportMonks fixture ID

        Returns:
            Lineups dict
        """
        data = await self._make_request(
            f"fixtures/{fixture_id}",
            params={"include": "lineups.player;formations"}
        )

        if not data or "data" not in data:
            return {"confirmed": False, "home_lineup": [], "away_lineup": []}

        match_data = data.get("data", {})
        lineups = match_data.get("lineups", [])
        formations = match_data.get("formations", [])

        home_lineup = []
        away_lineup = []
        home_formation = "4-3-3"
        away_formation = "4-3-3"

        # Parse formations
        for f in formations:
            if f.get("location") == "home":
                home_formation = f.get("formation", "4-3-3")
            elif f.get("location") == "away":
                away_formation = f.get("formation", "4-3-3")

        # Parse lineups
        for entry in lineups:
            player = entry.get("player", {})
            player_info = {
                "id": player.get("id"),
                "name": player.get("display_name") or player.get("name"),
                "position": entry.get("position"),
                "jersey_number": entry.get("jersey_number"),
                "substitute": entry.get("type_id") == 2,  # Check if sub
            }

            if entry.get("team_id"):
                # Need to determine home/away based on participant meta
                pass  # Would need more context

        return {
            "confirmed": len(lineups) > 0,
            "home_formation": home_formation,
            "away_formation": away_formation,
            "home_lineup": home_lineup,
            "away_lineup": away_lineup,
        }

    async def fetch_head_to_head(self, team_a_id: int, team_b_id: int) -> List[Dict]:
        """Fetch head-to-head history between two teams.

        Args:
            team_a_id: First team SportMonks ID
            team_b_id: Second team SportMonks ID

        Returns:
            List of past meetings
        """
        data = await self._make_request(
            f"fixtures/head-to-head/{team_a_id}/{team_b_id}",
            params={"include": "participants;scores"}
        )

        if not data or "data" not in data:
            return []

        matches = []
        for match in data.get("data", []):
            participants = match.get("participants", [])
            home_team = away_team = None
            home_score = away_score = None

            for p in participants:
                meta = p.get("meta", {})
                if meta.get("location") == "home":
                    home_team = p.get("name")
                    home_score = meta.get("score")
                else:
                    away_team = p.get("name")
                    away_score = meta.get("score")

            matches.append({
                "date": match.get("starting_at"),
                "home_team": home_team,
                "away_team": away_team,
                "home_score": home_score,
                "away_score": away_score,
            })

        return matches

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
