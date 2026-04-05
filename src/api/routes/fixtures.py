"""Fixtures API routes."""

from datetime import datetime
from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from src.scrapers.aggregator import DataAggregator
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


def serialize_fixture(fixture: dict) -> dict:
    """Serialize fixture dict with proper datetime handling."""
    result = dict(fixture)
    if result.get("match_date") and isinstance(result["match_date"], datetime):
        result["match_date"] = result["match_date"].isoformat()
    return result


@router.get("")
async def get_fixtures(
    days: int = Query(default=7, ge=1, le=60, description="Days ahead to fetch"),
    all_fixtures: bool = Query(default=False, description="Return all fixtures, not just upcoming")
):
    """Get upcoming fixtures."""
    try:
        logger.info(f"[FIXTURES API] Request: days={days}, all_fixtures={all_fixtures}")
        aggregator = DataAggregator()

        # Always use the aggregator for consistent data handling
        # It will try ScraperFC first, then fall back to FBref
        fixtures = await aggregator.get_upcoming_fixtures(days=days if not all_fixtures else 60)
        logger.info(f"[FIXTURES API] Aggregator returned {len(fixtures)} upcoming fixtures")

        # If all_fixtures requested but we got none, try direct scraper access
        if all_fixtures and not fixtures:
            logger.info("[FIXTURES API] No upcoming, trying FBref directly for all fixtures...")
            try:
                all_fbref = await aggregator.fbref.fetch_fixtures()
                if all_fbref:
                    now = datetime.now()
                    # Get fixtures that are either upcoming or recent (last 7 days)
                    relevant = [f for f in all_fbref
                                if f.get("match_date") and f.get("match_date") > now]
                    fixtures = relevant[:20] if relevant else all_fbref[:20]
                    logger.info(f"[FIXTURES API] FBref returned {len(fixtures)} fixtures")
            except Exception as e:
                logger.error(f"[FIXTURES API] FBref direct fetch failed: {e}")

        # Serialize datetime objects for JSON
        serialized = [serialize_fixture(f) for f in fixtures]
        logger.info(f"[FIXTURES API] Returning {len(serialized)} fixtures")

        return {
            "fixtures": serialized,
            "count": len(serialized),
            "days": days
        }
    except Exception as e:
        logger.error(f"[FIXTURES API] Failed to get fixtures: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/gameweek/{gameweek}")
async def get_fixtures_by_gameweek(gameweek: int):
    """Get fixtures by gameweek."""
    try:
        aggregator = DataAggregator()
        all_fixtures = await aggregator.get_upcoming_fixtures(days=60)
        # Filter by gameweek
        fixtures = [f for f in all_fixtures if f.get("gameweek") == gameweek]
        return {
            "fixtures": fixtures,
            "count": len(fixtures),
            "gameweek": gameweek
        }
    except Exception as e:
        logger.error(f"Failed to get fixtures for gameweek {gameweek}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fixture_id}")
async def get_fixture(fixture_id: int):
    """Get fixture details by ID."""
    # Note: In a full implementation, this would query the database
    # For now, return a placeholder
    return {
        "id": fixture_id,
        "message": "Fixture details would be fetched from database"
    }


@router.get("/{fixture_id}/context")
async def get_fixture_context(fixture_id: int):
    """Get full context for a fixture (for AI analysis)."""
    # Placeholder - would query database for fixture, then get context
    return {
        "fixture_id": fixture_id,
        "message": "Full fixture context for AI analysis"
    }
