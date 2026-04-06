"""Odds API routes."""

from fastapi import APIRouter, HTTPException
from src.scrapers.aggregator import DataAggregator
from src.database.persistence import DatabasePersistence
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/upcoming")
async def get_upcoming_odds():
    """Get odds for all upcoming fixtures."""
    try:
        db = DatabasePersistence()
        fixtures = db.get_upcoming_fixtures(days=14)
        # Filter to fixtures with odds
        with_odds = [f for f in fixtures if f.get("home_win_odds")]
        return {"fixtures": with_odds, "count": len(with_odds)}
    except Exception as e:
        logger.error(f"Failed to get odds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/fixture/{fixture_id}")
async def get_fixture_odds(fixture_id: int):
    """Get odds for a specific fixture."""
    try:
        db = DatabasePersistence()
        fixtures = db.get_upcoming_fixtures(days=30)
        fixture = next((f for f in fixtures if f.get("id") == fixture_id), None)
        if not fixture:
            raise HTTPException(status_code=404, detail="Fixture not found")
        return {
            "fixture_id": fixture_id,
            "home_team": fixture.get("home_team"),
            "away_team": fixture.get("away_team"),
            "home_win_odds": fixture.get("home_win_odds"),
            "draw_odds": fixture.get("draw_odds"),
            "away_win_odds": fixture.get("away_win_odds"),
            "over_2_5_odds": fixture.get("over_2_5_odds"),
            "under_2_5_odds": fixture.get("under_2_5_odds"),
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get fixture odds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_odds():
    """Manually refresh odds data."""
    try:
        aggregator = DataAggregator()
        odds = await aggregator.get_odds()
        return {"updated": len(odds), "odds": odds}
    except Exception as e:
        logger.error(f"Failed to refresh odds: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/value-bets")
async def get_value_bets():
    """Get intelligence-identified value bets."""
    try:
        db = DatabasePersistence()
        insights = db.get_insights(category="odds_analysis", limit=20)
        return {"value_bets": insights, "count": len(insights)}
    except Exception as e:
        logger.error(f"Failed to get value bets: {e}")
        raise HTTPException(status_code=500, detail=str(e))
