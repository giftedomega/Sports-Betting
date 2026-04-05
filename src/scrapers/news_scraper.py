"""News scraper using RSS feeds."""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
import re

import feedparser
import httpx

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)

# Premier League team names for matching
PL_TEAMS = [
    "Arsenal", "Aston Villa", "Bournemouth", "Brentford", "Brighton",
    "Chelsea", "Crystal Palace", "Everton", "Fulham", "Ipswich",
    "Leicester", "Liverpool", "Manchester City", "Manchester United",
    "Newcastle", "Nottingham Forest", "Southampton", "Tottenham",
    "West Ham", "Wolves", "Wolverhampton"
]


class NewsScraper(BaseScraper):
    """Scraper for football news from RSS feeds."""

    def __init__(self):
        """Initialize news scraper."""
        config = get_config()
        rate_limit = config.scraping.rate_limits.get("rss", 1)
        super().__init__(rate_limit_seconds=rate_limit)

        self.sources = config.news.sources
        self._http_client = None

    @property
    def http_client(self) -> httpx.AsyncClient:
        """Get HTTP client."""
        if self._http_client is None:
            self._http_client = httpx.AsyncClient(timeout=30.0)
        return self._http_client

    def _extract_teams_mentioned(self, text: str) -> List[str]:
        """Extract team names mentioned in text.

        Args:
            text: Text to search

        Returns:
            List of team names found
        """
        teams_found = []
        text_lower = text.lower()

        for team in PL_TEAMS:
            if team.lower() in text_lower:
                teams_found.append(team)

        # Handle variations
        if "man city" in text_lower or "man. city" in text_lower:
            if "Manchester City" not in teams_found:
                teams_found.append("Manchester City")
        if "man utd" in text_lower or "man united" in text_lower or "man. united" in text_lower:
            if "Manchester United" not in teams_found:
                teams_found.append("Manchester United")
        if "spurs" in text_lower:
            if "Tottenham" not in teams_found:
                teams_found.append("Tottenham")
        if "hammers" in text_lower:
            if "West Ham" not in teams_found:
                teams_found.append("West Ham")
        if "gunners" in text_lower:
            if "Arsenal" not in teams_found:
                teams_found.append("Arsenal")
        if "toon" in text_lower or "magpies" in text_lower:
            if "Newcastle" not in teams_found:
                teams_found.append("Newcastle")

        return teams_found

    def _simple_sentiment(self, text: str) -> str:
        """Simple sentiment analysis based on keywords.

        Args:
            text: Text to analyze

        Returns:
            Sentiment: positive, negative, or neutral
        """
        text_lower = text.lower()

        positive_words = [
            "win", "victory", "triumph", "success", "brilliant", "excellent",
            "comeback", "hero", "stunning", "dominant", "unbeaten", "record"
        ]
        negative_words = [
            "loss", "defeat", "injury", "injured", "doubt", "crisis",
            "struggle", "concern", "blow", "setback", "suspension", "ban"
        ]

        positive_count = sum(1 for word in positive_words if word in text_lower)
        negative_count = sum(1 for word in negative_words if word in text_lower)

        if positive_count > negative_count:
            return "positive"
        elif negative_count > positive_count:
            return "negative"
        return "neutral"

    def _determine_impact(self, text: str, teams: List[str]) -> str:
        """Determine news impact level.

        Args:
            text: Article text
            teams: Teams mentioned

        Returns:
            Impact level: high, medium, or low
        """
        text_lower = text.lower()

        # High impact keywords
        high_impact = [
            "injury", "injured", "out for", "ruled out", "suspension",
            "transfer", "signing", "sold", "manager", "sacked", "appointed"
        ]

        if any(word in text_lower for word in high_impact):
            return "high"

        if len(teams) > 0:
            return "medium"

        return "low"

    async def _fetch_feed(self, source_name: str, url: str) -> List[Dict]:
        """Fetch and parse a single RSS feed.

        Args:
            source_name: Name of the source
            url: Feed URL

        Returns:
            List of article dicts
        """
        try:
            response = await self.http_client.get(url)
            response.raise_for_status()

            feed = feedparser.parse(response.text)
            articles = []

            for entry in feed.entries[:20]:  # Limit to 20 most recent
                title = entry.get("title", "")
                description = entry.get("summary", entry.get("description", ""))

                # Parse published date
                published_at = None
                if hasattr(entry, "published_parsed") and entry.published_parsed:
                    published_at = datetime(*entry.published_parsed[:6])
                elif hasattr(entry, "updated_parsed") and entry.updated_parsed:
                    published_at = datetime(*entry.updated_parsed[:6])

                # Combine title and description for analysis
                full_text = f"{title} {description}"
                teams_mentioned = self._extract_teams_mentioned(full_text)

                # Only include if Premier League related
                if not teams_mentioned and "premier league" not in full_text.lower():
                    continue

                article = {
                    "source": source_name,
                    "title": title,
                    "url": entry.get("link", ""),
                    "description": description[:500] if description else None,
                    "published_at": published_at,
                    "teams_mentioned": teams_mentioned,
                    "sentiment": self._simple_sentiment(full_text),
                    "impact": self._determine_impact(full_text, teams_mentioned),
                }
                articles.append(article)

            logger.info(f"Fetched {len(articles)} articles from {source_name}")
            return articles

        except Exception as e:
            logger.error(f"Failed to fetch {source_name}: {e}")
            return []

    async def fetch_fixtures(self) -> List[Dict]:
        """Not implemented for news scraper."""
        return []

    async def fetch_team_stats(self) -> List[Dict]:
        """Not implemented for news scraper."""
        return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Not implemented for news scraper."""
        return []

    async def fetch_news(self) -> List[Dict]:
        """Fetch news from all configured sources.

        Returns:
            List of news articles
        """
        cache_key = "news_all"
        cached = self._get_cached(cache_key, CacheConfig.NEWS)
        if cached:
            return cached

        all_articles = []

        for source in self.sources:
            await self._rate_limit_wait()
            articles = await self._fetch_feed(source.name, source.url)
            all_articles.extend(articles)

        # Sort by published date (newest first)
        all_articles.sort(
            key=lambda x: x.get("published_at") or datetime.min,
            reverse=True
        )

        # Remove duplicates by URL
        seen_urls = set()
        unique_articles = []
        for article in all_articles:
            if article["url"] not in seen_urls:
                seen_urls.add(article["url"])
                unique_articles.append(article)

        logger.info(f"Total unique articles: {len(unique_articles)}")
        self._set_cache(cache_key, unique_articles)
        return unique_articles

    async def fetch_team_news(self, team_name: str) -> List[Dict]:
        """Fetch news for a specific team.

        Args:
            team_name: Team name to filter by

        Returns:
            List of news articles mentioning the team
        """
        all_news = await self.fetch_news()
        team_news = [
            article for article in all_news
            if team_name in article.get("teams_mentioned", [])
        ]
        return team_news

    async def close(self):
        """Close HTTP client."""
        if self._http_client:
            await self._http_client.aclose()
            self._http_client = None
