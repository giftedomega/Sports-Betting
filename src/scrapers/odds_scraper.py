"""Odds scraper using The-Odds-API (free tier)."""

from datetime import datetime
from typing import List, Dict, Optional

import httpx

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Map The-Odds-API team names to our standard names
TEAM_NAME_MAP = {
    "Arsenal": "Arsenal",
    "Aston Villa": "Aston Villa",
    "AFC Bournemouth": "Bournemouth",
    "Brentford": "Brentford",
    "Brighton and Hove Albion": "Brighton",
    "Chelsea": "Chelsea",
    "Crystal Palace": "Crystal Palace",
    "Everton": "Everton",
    "Fulham": "Fulham",
    "Ipswich Town": "Ipswich",
    "Leicester City": "Leicester",
    "Liverpool": "Liverpool",
    "Manchester City": "Manchester City",
    "Manchester United": "Manchester United",
    "Newcastle United": "Newcastle",
    "Nottingham Forest": "Nottingham Forest",
    "Southampton": "Southampton",
    "Tottenham Hotspur": "Tottenham",
    "West Ham United": "West Ham",
    "Wolverhampton Wanderers": "Wolves",
}


class OddsScraper(BaseScraper):
    """Scraper for The-Odds-API (free tier: 500 req/month)."""

    def __init__(self):
        config = get_config()
        rate_limit = config.scraping.rate_limits.get("odds_api", 5)
        super().__init__(rate_limit_seconds=rate_limit)
        self.api_key = config.odds_api.api_key
        self.regions = config.odds_api.regions
        self.markets = config.odds_api.markets
        self.base_url = "https://api.the-odds-api.com/v4"
        self.client = httpx.AsyncClient(timeout=30.0)

    async def fetch_fixtures(self) -> List[Dict]:
        """Not used for odds scraper."""
        return []

    async def fetch_team_stats(self) -> List[Dict]:
        """Not used for odds scraper."""
        return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Not used for odds scraper."""
        return []

    async def fetch_odds(self) -> List[Dict]:
        """Fetch odds for upcoming Premier League matches.

        Returns:
            List of dicts with match odds data
        """
        if not self.api_key:
            logger.warning("[ODDS] No API key configured for The-Odds-API")
            return []

        cached = self._get_cached("odds_upcoming", CacheConfig.LIVE_ODDS)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            url = f"{self.base_url}/sports/soccer_epl/odds"
            params = {
                "apiKey": self.api_key,
                "regions": self.regions,
                "markets": "h2h,totals",
                "oddsFormat": "decimal",
            }

            response = await self.client.get(url, params=params)
            response.raise_for_status()
            data = response.json()

            results = []
            for event in data:
                home_team = self._normalize_team(event.get("home_team", ""))
                away_team = self._normalize_team(event.get("away_team", ""))

                if not home_team or not away_team:
                    continue

                odds = self._extract_best_odds(event.get("bookmakers", []))
                odds["home_team"] = home_team
                odds["away_team"] = away_team
                odds["commence_time"] = event.get("commence_time")
                odds["event_id"] = event.get("id")
                results.append(odds)

            self._set_cache("odds_upcoming", results)
            logger.info(f"[ODDS] Fetched odds for {len(results)} matches")
            return results

        except httpx.HTTPStatusError as e:
            if e.response.status_code == 401:
                logger.error("[ODDS] Invalid API key")
            elif e.response.status_code == 429:
                logger.warning("[ODDS] Rate limit exceeded")
            else:
                logger.error(f"[ODDS] HTTP error: {e}")
            return []
        except Exception as e:
            logger.error(f"[ODDS] Failed to fetch odds: {e}")
            return []

    def _normalize_team(self, name: str) -> str:
        """Normalize team name to our standard."""
        return TEAM_NAME_MAP.get(name, name)

    def _extract_best_odds(self, bookmakers: List[Dict]) -> Dict:
        """Extract best available odds across all bookmakers.

        Returns dict with best odds for each market.
        """
        best = {
            "home_win_odds": None,
            "draw_odds": None,
            "away_win_odds": None,
            "over_2_5_odds": None,
            "under_2_5_odds": None,
        }

        for bookie in bookmakers:
            for market in bookie.get("markets", []):
                key = market.get("key")

                if key == "h2h":
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price", 0)
                        name = outcome.get("name", "")
                        if name == bookie.get("title", ""):
                            continue
                        # h2h outcomes are: Home, Away, Draw
                        if outcome.get("name") == "Draw":
                            if best["draw_odds"] is None or price > best["draw_odds"]:
                                best["draw_odds"] = price
                        elif market.get("outcomes", []).index(outcome) == 0:
                            # First outcome is home
                            if best["home_win_odds"] is None or price > best["home_win_odds"]:
                                best["home_win_odds"] = price
                        else:
                            if best["away_win_odds"] is None or price > best["away_win_odds"]:
                                best["away_win_odds"] = price

                elif key == "totals":
                    for outcome in market.get("outcomes", []):
                        price = outcome.get("price", 0)
                        point = outcome.get("point", 0)
                        if point == 2.5:
                            if outcome.get("name") == "Over":
                                if best["over_2_5_odds"] is None or price > best["over_2_5_odds"]:
                                    best["over_2_5_odds"] = price
                            elif outcome.get("name") == "Under":
                                if best["under_2_5_odds"] is None or price > best["under_2_5_odds"]:
                                    best["under_2_5_odds"] = price

        return best

    async def close(self):
        """Close HTTP client."""
        await self.client.aclose()
