"""Predictions API routes."""

from fastapi import APIRouter, HTTPException, BackgroundTasks

from src.scrapers.aggregator import DataAggregator
from src.llm.betting_analyzer import BettingAnalyzer
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
async def get_predictions():
    """Get all recent predictions."""
    # Placeholder - would query database
    return {
        "predictions": [],
        "count": 0,
        "message": "Predictions stored in database"
    }


@router.post("/analyze")
async def analyze_upcoming_fixtures():
    """Trigger analysis for all upcoming fixtures."""
    try:
        aggregator = DataAggregator()
        analyzer = BettingAnalyzer()

        # Get fixtures and team stats
        fixtures = await aggregator.get_upcoming_fixtures(days=7)
        team_stats = await aggregator.get_team_stats()
        news = await aggregator.get_news()

        # Convert team stats to dict for lookup
        team_stats_dict = {t["name"]: t for t in team_stats}

        # Analyze fixtures
        results = await analyzer.analyze_fixtures(fixtures, team_stats_dict, news)

        return {
            "analyzed": len(results),
            "predictions": results
        }
    except Exception as e:
        logger.error(f"Failed to analyze fixtures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match")
async def analyze_match(home_team: str, away_team: str):
    """Analyze a specific match."""
    try:
        aggregator = DataAggregator()
        analyzer = BettingAnalyzer()

        # Get context
        context = await aggregator.get_match_context(home_team, away_team)

        # Create fixture dict
        fixture = {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": None
        }

        # Analyze
        result = await analyzer.analyze_match(
            fixture=fixture,
            home_team_data=context["home_team_data"],
            away_team_data=context["away_team_data"],
            news_context=context["news_context"]
        )

        return result
    except Exception as e:
        logger.error(f"Failed to analyze match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_prediction_performance():
    """Get prediction accuracy statistics."""
    # Placeholder - would query database
    return {
        "total_predictions": 0,
        "correct_predictions": 0,
        "accuracy": 0,
        "total_profit_loss": 0,
        "message": "Track prediction outcomes in database"
    }


@router.get("/{fixture_id}")
async def get_fixture_prediction(fixture_id: int):
    """Get prediction for a specific fixture."""
    # Placeholder - would query database
    return {
        "fixture_id": fixture_id,
        "prediction": None,
        "message": "Would fetch from database"
    }
