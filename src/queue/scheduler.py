"""Background scheduler for continuous data updates."""

import asyncio
from datetime import datetime
from typing import Callable, Awaitable, Optional, Dict, Any

from src.scrapers.aggregator import DataAggregator
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BackgroundScheduler:
    """Continuous background data collection service."""

    def __init__(self, broadcast_fn: Optional[Callable[[Dict[str, Any]], Awaitable[None]]] = None):
        self.broadcast_fn = broadcast_fn
        self.config = get_config()
        self.aggregator = DataAggregator()

        self._running = False
        self._tasks = []

        self.intervals = {
            "fixtures": self.config.scheduler.fixtures_interval,
            "team_stats": self.config.scheduler.stats_interval,
            "news": self.config.scheduler.news_interval,
            "odds": self.config.scheduler.odds_interval,
            "injuries": self.config.scheduler.injury_interval,
            "weather": self.config.scheduler.weather_interval,
            "intelligence": self.config.scheduler.intelligence_interval,
        }

        self._last_updates: Dict[str, datetime] = {}

    async def start(self):
        """Start all background tasks."""
        self._running = True
        logger.info("Starting background scheduler...")

        self._tasks = [
            asyncio.create_task(self._update_loop("fixtures", self._update_fixtures)),
            asyncio.create_task(self._update_loop("team_stats", self._update_team_stats)),
            asyncio.create_task(self._update_loop("news", self._update_news)),
            asyncio.create_task(self._update_loop("odds", self._update_odds)),
            asyncio.create_task(self._update_loop("injuries", self._update_injuries)),
            asyncio.create_task(self._update_loop("weather", self._update_weather)),
            asyncio.create_task(self._update_loop("intelligence", self._update_intelligence)),
        ]

        logger.info(f"Started {len(self._tasks)} background update tasks")

    async def stop(self):
        """Stop all background tasks."""
        self._running = False
        for task in self._tasks:
            task.cancel()
        await asyncio.gather(*self._tasks, return_exceptions=True)
        await self.aggregator.close()
        logger.info("Background scheduler stopped")

    async def _update_loop(self, name: str, update_fn: Callable):
        """Generic update loop with error handling."""
        interval = self.intervals.get(name, 3600)

        # Stagger initial updates
        await asyncio.sleep(5 + hash(name) % 10)

        while self._running:
            try:
                logger.debug(f"Running {name} update...")
                result = await update_fn()
                self._last_updates[name] = datetime.now()

                if self.broadcast_fn:
                    await self.broadcast_fn({
                        "type": "background_update",
                        "task": name,
                        "status": "completed",
                        "timestamp": datetime.now().isoformat(),
                        "result": result
                    })

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in {name} update: {e}")
                if self.broadcast_fn:
                    await self.broadcast_fn({
                        "type": "background_update",
                        "task": name,
                        "status": "error",
                        "error": str(e),
                        "timestamp": datetime.now().isoformat()
                    })

            await asyncio.sleep(interval)

    async def _update_fixtures(self) -> Dict:
        fixtures = await self.aggregator.get_upcoming_fixtures(days=14)
        logger.info(f"Updated {len(fixtures)} fixtures")
        return {"count": len(fixtures)}

    async def _update_team_stats(self) -> Dict:
        stats = await self.aggregator.get_team_stats()
        logger.info(f"Updated stats for {len(stats)} teams")
        return {"count": len(stats)}

    async def _update_news(self) -> Dict:
        articles = await self.aggregator.get_news()
        logger.info(f"Fetched {len(articles)} news articles")
        return {"count": len(articles)}

    async def _update_odds(self) -> Dict:
        odds = await self.aggregator.get_odds()
        logger.info(f"Updated odds for {len(odds)} matches")
        return {"count": len(odds)}

    async def _update_injuries(self) -> Dict:
        injuries = await self.aggregator.get_injuries()
        logger.info(f"Updated {len(injuries)} injury records")
        return {"count": len(injuries)}

    async def _update_weather(self) -> Dict:
        weather = await self.aggregator.get_weather()
        logger.info(f"Updated weather for {len(weather)} fixtures")
        return {"count": len(weather)}

    async def _update_intelligence(self) -> Dict:
        """Run intelligence aggregation for all teams."""
        if not self.aggregator.intelligence:
            return {"count": 0, "message": "Intelligence pipeline unavailable"}

        try:
            teams = self.aggregator.db.get_teams() if self.aggregator.db else []
            count = 0
            for team in teams[:20]:
                try:
                    await self.aggregator.intelligence.aggregate_team_profile(team["name"])
                    count += 1
                except Exception as e:
                    logger.warning(f"Intelligence failed for {team['name']}: {e}")
            logger.info(f"Updated intelligence profiles for {count} teams")
            return {"count": count}
        except Exception as e:
            logger.error(f"Intelligence update failed: {e}")
            return {"count": 0, "error": str(e)}

    def get_status(self) -> Dict:
        return {
            "running": self._running,
            "tasks": list(self.intervals.keys()),
            "intervals": self.intervals,
            "last_updates": {k: v.isoformat() for k, v in self._last_updates.items()}
        }


class DataStore:
    """Centralized data store for cached scraped data."""

    def __init__(self):
        self._fixtures = []
        self._team_stats = {}
        self._news = []
        self._last_updated = {}

    async def store_fixtures(self, fixtures):
        self._fixtures = fixtures
        self._last_updated["fixtures"] = datetime.now()

    async def store_team_stats(self, stats):
        self._team_stats = {t["name"]: t for t in stats}
        self._last_updated["team_stats"] = datetime.now()

    async def store_news(self, articles):
        self._news = articles
        self._last_updated["news"] = datetime.now()

    def get_fixtures(self):
        return self._fixtures

    def get_team_stats(self):
        return self._team_stats

    def get_news(self):
        return self._news

    def get_last_updated(self):
        return {k: v.isoformat() for k, v in self._last_updated.items()}
