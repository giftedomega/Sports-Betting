"""Players API routes."""

from typing import Optional
from fastapi import APIRouter, HTTPException, Query

from src.scrapers.aggregator import DataAggregator
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("")
async def get_players(
    team: Optional[str] = Query(default=None, description="Filter by team name")
):
    """Get all players or filter by team."""
    try:
        aggregator = DataAggregator()
        players = await aggregator.get_player_stats(team)
        return {
            "players": players,
            "count": len(players),
            "team_filter": team
        }
    except Exception as e:
        logger.error(f"Failed to get players: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-scorers")
async def get_top_scorers(limit: int = Query(default=20, ge=1, le=100)):
    """Get top scorers."""
    try:
        aggregator = DataAggregator()
        players = await aggregator.get_player_stats()
        # Sort by goals
        sorted_players = sorted(players, key=lambda x: x.get("goals", 0), reverse=True)
        return {
            "players": sorted_players[:limit],
            "count": min(limit, len(sorted_players))
        }
    except Exception as e:
        logger.error(f"Failed to get top scorers: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/top-assists")
async def get_top_assists(limit: int = Query(default=20, ge=1, le=100)):
    """Get top assist providers."""
    try:
        aggregator = DataAggregator()
        players = await aggregator.get_player_stats()
        # Sort by assists
        sorted_players = sorted(players, key=lambda x: x.get("assists", 0), reverse=True)
        return {
            "players": sorted_players[:limit],
            "count": min(limit, len(sorted_players))
        }
    except Exception as e:
        logger.error(f"Failed to get top assists: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{player_name}")
async def get_player(player_name: str):
    """Get player details by name."""
    try:
        aggregator = DataAggregator()
        players = await aggregator.get_player_stats()
        player = next(
            (p for p in players if player_name.lower() in p["name"].lower()),
            None
        )
        if not player:
            raise HTTPException(status_code=404, detail=f"Player not found: {player_name}")
        return player
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get player {player_name}: {e}")
        raise HTTPException(status_code=500, detail=str(e))
