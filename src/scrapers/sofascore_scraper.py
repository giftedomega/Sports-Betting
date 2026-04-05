"""SofaScore scraper for real-time lineups and match data."""

import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional
import json

import httpx

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)

# Premier League team IDs on SofaScore
SOFASCORE_TEAM_IDS = {
    "Arsenal": 42,
    "Aston Villa": 40,
    "Bournemouth": 60,
    "Brentford": 50,
    "Brighton": 30,
    "Chelsea": 38,
    "Crystal Palace": 7,
    "Everton": 48,
    "Fulham": 43,
    "Ipswich": 48,  # May need updating
    "Leicester": 31,
    "Liverpool": 44,
    "Manchester City": 17,
    "Manchester United": 35,
    "Newcastle": 39,
    "Nottingham Forest": 14,
    "Southampton": 45,
    "Tottenham": 33,
    "West Ham": 37,
    "Wolves": 3,
    "Wolverhampton": 3,
}

# Premier League tournament ID on SofaScore
PREMIER_LEAGUE_ID = 17


class SofaScoreScraper(BaseScraper):
    """Scraper for SofaScore real-time data."""

    BASE_URL = "https://api.sofascore.com/api/v1"

    def __init__(self):
        """Initialize SofaScore scraper."""
        config = get_config()
        # SofaScore rate limit - be conservative
        rate_limit = config.scraping.rate_limits.get("sofascore", 12)
        super().__init__(rate_limit_seconds=rate_limit)

        self._http_client = None
        self._headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
            "Accept": "application/json",
            "Accept-Language": "en-US,en;q=0.9",
        }

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(
                headers=self._headers,
                timeout=30.0,
                follow_redirects=True
            )
        return self._http_client

    async def fetch_fixtures(self) -> List[Dict]:
        """Fetch upcoming fixtures - delegates to FBref."""
        # SofaScore is mainly for lineups, not fixtures
        return []

    async def fetch_team_stats(self) -> List[Dict]:
        """Fetch team stats - delegates to FBref."""
        return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Fetch player stats - delegates to FBref."""
        return []

    async def get_team_id(self, team_name: str) -> Optional[int]:
        """Get SofaScore team ID for a team name.

        Args:
            team_name: Team name

        Returns:
            SofaScore team ID or None
        """
        # Check our mapping first
        if team_name in SOFASCORE_TEAM_IDS:
            return SOFASCORE_TEAM_IDS[team_name]

        # Try variations
        for known_name, team_id in SOFASCORE_TEAM_IDS.items():
            if team_name.lower() in known_name.lower() or known_name.lower() in team_name.lower():
                return team_id

        return None

    async def fetch_team_next_match(self, team_name: str) -> Optional[Dict]:
        """Fetch next match for a team.

        Args:
            team_name: Team name

        Returns:
            Match data dict or None
        """
        team_id = await self.get_team_id(team_name)
        if not team_id:
            logger.warning(f"Unknown team: {team_name}")
            return None

        cache_key = f"next_match_{team_id}"
        cached = self._get_cached(cache_key, CacheConfig.FIXTURES)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            url = f"{self.BASE_URL}/team/{team_id}/events/next/0"
            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()
                events = data.get("events", [])

                if events:
                    match = events[0]
                    result = {
                        "id": match.get("id"),
                        "home_team": match.get("homeTeam", {}).get("name"),
                        "away_team": match.get("awayTeam", {}).get("name"),
                        "home_team_id": match.get("homeTeam", {}).get("id"),
                        "away_team_id": match.get("awayTeam", {}).get("id"),
                        "start_time": match.get("startTimestamp"),
                        "status": match.get("status", {}).get("type"),
                        "tournament": match.get("tournament", {}).get("name"),
                    }
                    self._set_cache(cache_key, result)
                    return result

            return None

        except Exception as e:
            logger.error(f"Failed to fetch next match for {team_name}: {e}")
            return None

    async def fetch_match_lineups(self, match_id: int) -> Dict:
        """Fetch lineups for a specific match.

        Args:
            match_id: SofaScore match ID

        Returns:
            Lineups dict with home and away formations
        """
        cache_key = f"lineup_{match_id}"
        cached = self._get_cached(cache_key, CacheConfig.MATCH_DAY_LINEUPS)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            url = f"{self.BASE_URL}/event/{match_id}/lineups"
            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()

                result = {
                    "match_id": match_id,
                    "confirmed": data.get("confirmed", False),
                    "home": self._parse_lineup(data.get("home", {})),
                    "away": self._parse_lineup(data.get("away", {}))
                }

                self._set_cache(cache_key, result)
                logger.info(f"Fetched lineups for match {match_id}")
                return result

            elif response.status_code == 404:
                # Lineups not yet available
                return {
                    "match_id": match_id,
                    "confirmed": False,
                    "home": {"formation": None, "players": []},
                    "away": {"formation": None, "players": []}
                }

            else:
                logger.warning(f"SofaScore returned {response.status_code} for match {match_id}")
                return None

        except Exception as e:
            logger.error(f"Failed to fetch lineups for match {match_id}: {e}")
            return None

    def _parse_lineup(self, lineup_data: Dict) -> Dict:
        """Parse lineup data from SofaScore response.

        Args:
            lineup_data: Raw lineup data

        Returns:
            Parsed lineup dict
        """
        players = []
        formation = lineup_data.get("formation")

        # Parse starting XI
        for player_data in lineup_data.get("players", []):
            player = player_data.get("player", {})
            players.append({
                "id": player.get("id"),
                "name": player.get("name"),
                "short_name": player.get("shortName"),
                "position": player_data.get("position"),
                "jersey_number": player_data.get("jerseyNumber"),
                "substitute": player_data.get("substitute", False),
                "captain": player_data.get("captain", False),
            })

        # Separate starters and subs
        starters = [p for p in players if not p.get("substitute")]
        substitutes = [p for p in players if p.get("substitute")]

        return {
            "formation": formation,
            "players": starters,
            "substitutes": substitutes
        }

    async def fetch_predicted_lineups(
        self,
        home_team: str,
        away_team: str
    ) -> Dict:
        """Fetch predicted or confirmed lineups for a match.

        Args:
            home_team: Home team name
            away_team: Away team name

        Returns:
            Lineups dict
        """
        # First, find the match
        home_match = await self.fetch_team_next_match(home_team)

        if not home_match:
            return {
                "home_team": home_team,
                "away_team": away_team,
                "home_formation": "4-3-3",
                "away_formation": "4-3-3",
                "home_lineup": [],
                "away_lineup": [],
                "confirmed": False,
                "source": "default"
            }

        # Check if this is the right match
        match_home = home_match.get("home_team", "").lower()
        match_away = home_match.get("away_team", "").lower()

        if home_team.lower() not in match_home and away_team.lower() not in match_away:
            logger.info(f"Next match doesn't match: {match_home} vs {match_away}")
            return {
                "home_team": home_team,
                "away_team": away_team,
                "home_formation": "4-3-3",
                "away_formation": "4-3-3",
                "home_lineup": [],
                "away_lineup": [],
                "confirmed": False,
                "source": "default"
            }

        # Fetch lineups
        match_id = home_match.get("id")
        if match_id:
            lineups = await self.fetch_match_lineups(match_id)

            if lineups and lineups.get("confirmed"):
                return {
                    "home_team": home_team,
                    "away_team": away_team,
                    "home_formation": lineups.get("home", {}).get("formation") or "4-3-3",
                    "away_formation": lineups.get("away", {}).get("formation") or "4-3-3",
                    "home_lineup": lineups.get("home", {}).get("players", []),
                    "away_lineup": lineups.get("away", {}).get("players", []),
                    "home_subs": lineups.get("home", {}).get("substitutes", []),
                    "away_subs": lineups.get("away", {}).get("substitutes", []),
                    "confirmed": True,
                    "source": "sofascore"
                }

        # Return default if no confirmed lineups
        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_formation": "4-3-3",
            "away_formation": "4-3-3",
            "home_lineup": [],
            "away_lineup": [],
            "confirmed": False,
            "source": "default"
        }

    async def fetch_live_match_stats(self, match_id: int) -> Optional[Dict]:
        """Fetch live statistics for a match.

        Args:
            match_id: SofaScore match ID

        Returns:
            Match statistics dict
        """
        cache_key = f"live_stats_{match_id}"
        cached = self._get_cached(cache_key, CacheConfig.LIVE_MATCH)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            url = f"{self.BASE_URL}/event/{match_id}/statistics"
            response = await self.http_client.get(url)

            if response.status_code == 200:
                data = response.json()

                # Parse statistics
                stats = {}
                for period in data.get("statistics", []):
                    period_name = period.get("period", "ALL")
                    groups = period.get("groups", [])

                    period_stats = {}
                    for group in groups:
                        for stat_item in group.get("statisticsItems", []):
                            stat_name = stat_item.get("name")
                            home_value = stat_item.get("home")
                            away_value = stat_item.get("away")
                            period_stats[stat_name] = {
                                "home": home_value,
                                "away": away_value
                            }

                    stats[period_name] = period_stats

                result = {
                    "match_id": match_id,
                    "statistics": stats
                }
                self._set_cache(cache_key, result)
                return result

            return None

        except Exception as e:
            logger.error(f"Failed to fetch live stats for match {match_id}: {e}")
            return None

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
