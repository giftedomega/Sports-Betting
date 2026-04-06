"""Injury/availability scraper using the Fantasy Premier League API."""

from datetime import datetime
from typing import List, Dict, Optional

import httpx

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# FPL team IDs mapped to our standard team names (updated each season)
FPL_TEAM_MAP = {
    1: "Arsenal",
    2: "Aston Villa",
    3: "Bournemouth",
    4: "Brentford",
    5: "Brighton",
    6: "Chelsea",
    7: "Crystal Palace",
    8: "Everton",
    9: "Fulham",
    10: "Ipswich",
    11: "Leicester",
    12: "Liverpool",
    13: "Manchester City",
    14: "Manchester United",
    15: "Newcastle",
    16: "Nottingham Forest",
    17: "Southampton",
    18: "Tottenham",
    19: "West Ham",
    20: "Wolves",
}


class InjuryScraper(BaseScraper):
    """Scraper for injury/availability data from the FPL API."""

    FPL_API_URL = "https://fantasy.premierleague.com/api/bootstrap-static/"

    def __init__(self):
        config = get_config()
        rate_limit = config.scraping.rate_limits.get("fpl", 2)
        super().__init__(rate_limit_seconds=rate_limit)
        self.client = httpx.AsyncClient(timeout=30.0)
        self._team_map = {}

    async def fetch_fixtures(self) -> List[Dict]:
        return []

    async def fetch_team_stats(self) -> List[Dict]:
        return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        return []

    async def fetch_injuries(self) -> List[Dict]:
        """Fetch all player injury/availability data from FPL API.

        Returns:
            List of dicts with player injury information
        """
        cached = self._get_cached("fpl_injuries", 1800)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            response = await self.client.get(self.FPL_API_URL)
            response.raise_for_status()
            data = response.json()

            # Build team ID -> name map from FPL response
            self._team_map = {}
            for team in data.get("teams", []):
                fpl_id = team.get("id")
                # Try our hardcoded map first, fall back to FPL name
                name = FPL_TEAM_MAP.get(fpl_id, team.get("name", ""))
                self._team_map[fpl_id] = name

            results = []
            for player in data.get("elements", []):
                status = player.get("status", "a")  # a=available, i=injured, s=suspended, d=doubtful, u=unavailable

                if status in ("i", "s", "d", "u"):
                    team_id = player.get("team")
                    team_name_val = self._team_map.get(team_id, "Unknown")

                    # Determine type
                    is_injured = status in ("i", "d", "u")
                    is_suspended = status == "s"

                    first_name = player.get("first_name", "")
                    second_name = player.get("second_name", "")
                    web_name = player.get("web_name", f"{first_name} {second_name}")

                    results.append({
                        "name": web_name,
                        "full_name": f"{first_name} {second_name}",
                        "team": team_name_val,
                        "fpl_id": player.get("id"),
                        "is_injured": is_injured,
                        "is_suspended": is_suspended,
                        "injury_description": player.get("news", ""),
                        "chance_of_playing_next": player.get("chance_of_playing_next_round"),
                        "chance_of_playing_this": player.get("chance_of_playing_this_round"),
                        "status": status,
                        "position": self._map_position(player.get("element_type", 0)),
                    })

            self._set_cache("fpl_injuries", results)
            logger.info(f"[INJURIES] Fetched {len(results)} injured/doubtful/suspended players")
            return results

        except Exception as e:
            logger.error(f"[INJURIES] Failed to fetch from FPL API: {e}")
            return []

    async def fetch_team_injuries(self, team_name: str) -> List[Dict]:
        """Get injuries for a specific team."""
        all_injuries = await self.fetch_injuries()
        return [p for p in all_injuries if p["team"] == team_name]

    def _map_position(self, element_type: int) -> str:
        """Map FPL element_type to position string."""
        return {1: "GK", 2: "DF", 3: "MF", 4: "FW"}.get(element_type, "Unknown")

    async def close(self):
        await self.client.aclose()
