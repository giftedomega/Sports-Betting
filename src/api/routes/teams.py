"""Teams API routes."""

from fastapi import APIRouter, HTTPException

from src.scrapers.aggregator import DataAggregator
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
async def get_teams():
    """Get all teams with current stats."""
    try:
        aggregator = DataAggregator()
        teams = await aggregator.get_team_stats()
        return {
            "teams": teams,
            "count": len(teams)
        }
    except Exception as e:
        logger.error(f"Failed to get teams: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/table")
async def get_league_table():
    """Get current league table."""
    try:
        aggregator = DataAggregator()
        teams = await aggregator.get_team_stats()
        # Teams are already sorted by position
        return {
            "table": teams,
            "competition": "Premier League"
        }
    except Exception as e:
        logger.error(f"Failed to get league table: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_name}")
async def get_team(team_name: str):
    """Get team details by name."""
    try:
        aggregator = DataAggregator()
        teams = await aggregator.get_team_stats()
        team = next((t for t in teams if t["name"].lower() == team_name.lower()), None)
        if not team:
            raise HTTPException(status_code=404, detail=f"Team not found: {team_name}")
        return team
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get team {team_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_name}/players")
async def get_team_players(team_name: str):
    """Get team squad."""
    try:
        aggregator = DataAggregator()
        players = await aggregator.get_player_stats(team_name)
        return {
            "team": team_name,
            "players": players,
            "count": len(players)
        }
    except Exception as e:
        logger.error(f"Failed to get players for {team_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_name}/news")
async def get_team_news(team_name: str):
    """Get recent news for a team."""
    try:
        aggregator = DataAggregator()
        news = await aggregator.get_team_news(team_name)
        return {
            "team": team_name,
            "articles": news,
            "count": len(news)
        }
    except Exception as e:
        logger.error(f"Failed to get news for {team_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
