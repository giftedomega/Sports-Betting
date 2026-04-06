"""Intelligence API routes."""

from fastapi import APIRouter, HTTPException
from src.database.persistence import DatabasePersistence
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/insights")
async def get_insights(category: str = None, team: str = None, limit: int = 50):
    """Get recent intelligence insights."""
    try:
        db = DatabasePersistence()
        insights = db.get_insights(category=category, entity_name=team, limit=limit)
        return {"insights": insights, "count": len(insights)}
    except Exception as e:
        logger.error(f"Failed to get insights: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/{team_name}")
async def get_team_intelligence(team_name: str):
    """Get intelligence profile for a team."""
    try:
        db = DatabasePersistence()
        insights = db.get_team_insights(team_name, limit=20)

        # Get the latest team profile if it exists
        profiles = db.get_insights(category="team_profile", entity_name=team_name, limit=1)
        profile = profiles[0] if profiles else None

        return {
            "team": team_name,
            "profile": profile,
            "recent_insights": insights,
            "count": len(insights),
        }
    except Exception as e:
        logger.error(f"Failed to get team intelligence: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/season-prediction")
async def get_season_prediction():
    """Get latest season prediction."""
    try:
        db = DatabasePersistence()
        predictions = db.get_insights(category="season_prediction", limit=1)
        if predictions:
            import json
            pred = predictions[0]
            try:
                pred["parsed"] = json.loads(pred.get("summary", "{}"))
            except (json.JSONDecodeError, TypeError):
                pred["parsed"] = None
            return pred
        return {"message": "No season prediction available yet"}
    except Exception as e:
        logger.error(f"Failed to get season prediction: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/refresh")
async def refresh_intelligence():
    """Trigger intelligence pipeline manually."""
    try:
        from src.llm.intelligence import IntelligencePipeline
        pipeline = IntelligencePipeline()
        db = DatabasePersistence()

        teams = db.get_teams()
        count = 0
        for team in teams[:20]:
            try:
                await pipeline.aggregate_team_profile(team["name"])
                count += 1
            except Exception as e:
                logger.warning(f"Intelligence failed for {team['name']}: {e}")

        return {"profiles_updated": count}
    except Exception as e:
        logger.error(f"Intelligence refresh failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/season-prediction/generate")
async def generate_season_prediction():
    """Generate a new season prediction."""
    try:
        from src.llm.intelligence import IntelligencePipeline
        pipeline = IntelligencePipeline()
        result = await pipeline.generate_season_prediction()
        return result
    except Exception as e:
        logger.error(f"Season prediction generation failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
