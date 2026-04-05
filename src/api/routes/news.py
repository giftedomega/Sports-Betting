"""News API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from src.scrapers.aggregator import DataAggregator
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
async def get_news(
    limit: int = Query(default=20, ge=1, le=100, description="Number of articles")
):
    """Get latest news articles."""
    try:
        aggregator = DataAggregator()
        news = await aggregator.get_news()
        return {
            "articles": news[:limit],
            "count": min(limit, len(news))
        }
    except Exception as e:
        logger.error(f"Failed to get news: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/{team_name}")
async def get_team_news(
    team_name: str,
    limit: int = Query(default=10, ge=1, le=50)
):
    """Get news for a specific team."""
    try:
        aggregator = DataAggregator()
        news = await aggregator.get_team_news(team_name)
        return {
            "team": team_name,
            "articles": news[:limit],
            "count": min(limit, len(news))
        }
    except Exception as e:
        logger.error(f"Failed to get news for {team_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/high-impact")
async def get_high_impact_news():
    """Get high-impact news articles."""
    try:
        aggregator = DataAggregator()
        news = await aggregator.get_news()
        high_impact = [a for a in news if a.get("impact") == "high"]
        return {
            "articles": high_impact,
            "count": len(high_impact)
        }
    except Exception as e:
        logger.error(f"Failed to get high-impact news: {e}")
        raise HTTPException(status_code=500, detail=str(e))
