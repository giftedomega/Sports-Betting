"""Base scraper with caching and rate limiting."""

import asyncio
import time
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional
from pathlib import Path

from src.utils.logger import get_logger

logger = get_logger(__name__)


class CacheConfig:
    """Cache TTL configuration (in seconds)."""

    # Static/slow-changing data
    TEAM_INFO = 86400           # 24 hours
    PLAYER_INFO = 86400         # 24 hours
    HISTORICAL_H2H = 86400      # 24 hours

    # Match-related
    FIXTURES = 3600             # 1 hour
    LEAGUE_TABLE = 1800         # 30 mins

    # Real-time data
    LINEUPS = 600               # 10 mins
    NEWS = 900                  # 15 mins
    LIVE_ODDS = 300             # 5 mins

    # Match day
    MATCH_DAY_LINEUPS = 120     # 2 mins
    LIVE_MATCH = 60             # 1 min


class BaseScraper(ABC):
    """Abstract base class for all scrapers."""

    def __init__(self, rate_limit_seconds: float = 3.0):
        """Initialize scraper with rate limiting.

        Args:
            rate_limit_seconds: Minimum seconds between requests
        """
        self.rate_limit = rate_limit_seconds
        self._last_request_time = 0
        self._cache: Dict[str, Dict[str, Any]] = {}

    async def _rate_limit_wait(self):
        """Wait if necessary to respect rate limit."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.rate_limit:
            wait_time = self.rate_limit - elapsed
            logger.debug(f"Rate limiting: waiting {wait_time:.2f}s")
            await asyncio.sleep(wait_time)
        self._last_request_time = time.time()

    def _get_cached(self, cache_key: str, ttl_seconds: int) -> Optional[Any]:
        """Get data from cache if not expired.

        Args:
            cache_key: Cache key
            ttl_seconds: Cache TTL in seconds

        Returns:
            Cached data or None if expired/missing
        """
        if cache_key in self._cache:
            cached = self._cache[cache_key]
            if datetime.now() - cached["timestamp"] < timedelta(seconds=ttl_seconds):
                logger.debug(f"Cache hit: {cache_key}")
                return cached["data"]
        return None

    def _set_cache(self, cache_key: str, data: Any):
        """Store data in cache.

        Args:
            cache_key: Cache key
            data: Data to cache
        """
        self._cache[cache_key] = {
            "data": data,
            "timestamp": datetime.now()
        }
        logger.debug(f"Cached: {cache_key}")

    def clear_cache(self, cache_key: Optional[str] = None):
        """Clear cache.

        Args:
            cache_key: Specific key to clear, or None to clear all
        """
        if cache_key:
            self._cache.pop(cache_key, None)
        else:
            self._cache.clear()

    @abstractmethod
    async def fetch_fixtures(self) -> List[Dict]:
        """Fetch upcoming fixtures."""
        pass

    @abstractmethod
    async def fetch_team_stats(self) -> List[Dict]:
        """Fetch team statistics."""
        pass

    @abstractmethod
    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Fetch player statistics."""
        pass
