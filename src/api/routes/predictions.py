"""Predictions API routes."""

from fastapi import APIRouter, HTTPException

from src.scrapers.aggregator import DataAggregator
from src.llm.betting_analyzer import BettingAnalyzer
from src.database.persistence import DatabasePersistence
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
async def get_predictions(limit: int = 20):
    """Get all recent predictions from database."""
    try:
        db = DatabasePersistence()
        predictions = db.get_recent_predictions(limit=limit)
        return {"predictions": predictions, "count": len(predictions)}
    except Exception as e:
        logger.error(f"Failed to get predictions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/analyze")
async def analyze_upcoming_fixtures():
    """Trigger analysis for all upcoming fixtures."""
    try:
        aggregator = DataAggregator()
        analyzer = BettingAnalyzer()

        fixtures = await aggregator.get_upcoming_fixtures(days=7)
        team_stats = await aggregator.get_team_stats()
        news = await aggregator.get_news()
        odds = await aggregator.get_odds()

        team_stats_dict = {t["name"]: t for t in team_stats}
        results = await analyzer.analyze_fixtures(fixtures, team_stats_dict, news, odds)

        # Save predictions to database
        db = DatabasePersistence()
        for result in results:
            if result.get("predicted_outcome") != "unknown":
                try:
                    db.save_prediction(result)
                except Exception as e:
                    logger.warning(f"Failed to save prediction: {e}")

        return {"analyzed": len(results), "predictions": results}
    except Exception as e:
        logger.error(f"Failed to analyze fixtures: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/match")
async def analyze_match(home_team: str, away_team: str):
    """Analyze a specific match with full context."""
    try:
        aggregator = DataAggregator()
        analyzer = BettingAnalyzer()

        context = await aggregator.get_match_context(home_team, away_team)

        fixture = {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": None
        }

        result = await analyzer.analyze_match(
            fixture=fixture,
            home_team_data=context["home_team_data"],
            away_team_data=context["away_team_data"],
            news_context=context.get("news_context"),
            odds_data=context.get("odds_data"),
            injuries=context.get("injuries"),
            weather_data=context.get("weather"),
        )

        # Save to database
        if result.get("predicted_outcome") != "unknown":
            try:
                db = DatabasePersistence()
                db.save_prediction(result)
            except Exception as e:
                logger.warning(f"Failed to save prediction: {e}")

        return result
    except Exception as e:
        logger.error(f"Failed to analyze match: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/performance")
async def get_prediction_performance():
    """Get prediction accuracy statistics."""
    try:
        db = DatabasePersistence()
        return db.get_prediction_stats()
    except Exception as e:
        logger.error(f"Failed to get performance: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{fixture_id}")
async def get_fixture_prediction(fixture_id: int):
    """Get prediction for a specific fixture."""
    try:
        db = DatabasePersistence()
        predictions = db.get_recent_predictions(limit=100)
        match = [p for p in predictions if p.get("fixture_id") == fixture_id]
        if match:
            return match[0]
        return {"fixture_id": fixture_id, "prediction": None, "message": "No prediction found"}
    except Exception as e:
        logger.error(f"Failed to get prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))
