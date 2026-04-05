"""Formations API routes."""

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import HTMLResponse

from src.scrapers.aggregator import DataAggregator
from src.visualization.pitch_svg import PitchSVG, get_pitch_svg
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{home_team}/vs/{away_team}")
async def get_match_formations(
    home_team: str,
    away_team: str,
    home_formation: str = Query(default="4-3-3", description="Home team formation"),
    away_formation: str = Query(default="4-3-3", description="Away team formation")
):
    """Get predicted formations for a match."""
    try:
        aggregator = DataAggregator()
        lineups = await aggregator.get_predicted_lineups(home_team, away_team)

        return {
            "home_team": home_team,
            "away_team": away_team,
            "home_formation": lineups.get("home_formation", home_formation),
            "away_formation": lineups.get("away_formation", away_formation),
            "home_lineup": lineups.get("home_probable_xi", []),
            "away_lineup": lineups.get("away_probable_xi", []),
            "confidence": lineups.get("confidence", 50),
            "is_predicted": lineups.get("is_predicted", True)
        }
    except Exception as e:
        logger.error(f"Failed to get formations: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{home_team}/vs/{away_team}/svg", response_class=HTMLResponse)
async def get_match_formations_svg(
    home_team: str,
    away_team: str,
    home_formation: str = Query(default="4-3-3"),
    away_formation: str = Query(default="4-3-3")
):
    """Get SVG pitch visualization for a match."""
    try:
        aggregator = DataAggregator()
        lineups = await aggregator.get_predicted_lineups(home_team, away_team)

        # Get player data for lineup
        home_players = lineups.get("home_probable_xi", [])[:11]
        away_players = lineups.get("away_probable_xi", [])[:11]

        # Generate SVG
        svg = get_pitch_svg(
            home_team=home_team,
            away_team=away_team,
            home_formation=lineups.get("home_formation", home_formation),
            away_formation=lineups.get("away_formation", away_formation),
            home_players=home_players,
            away_players=away_players
        )

        return HTMLResponse(content=svg, media_type="image/svg+xml")
    except Exception as e:
        logger.error(f"Failed to generate formations SVG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/team/{team_name}/recent")
async def get_team_recent_formations(
    team_name: str,
    limit: int = Query(default=5, ge=1, le=20)
):
    """Get a team's recent formations."""
    # Note: This would query the database for historical formations
    # For now, return common formations for the team
    common_formations = {
        "Manchester City": ["4-3-3", "4-2-3-1", "3-2-4-1"],
        "Arsenal": ["4-3-3", "4-2-3-1"],
        "Liverpool": ["4-3-3", "4-2-3-1"],
        "Manchester United": ["4-2-3-1", "4-3-3"],
        "Chelsea": ["4-2-3-1", "3-4-2-1"],
        "Tottenham": ["4-3-3", "4-2-3-1", "3-4-3"],
        "Newcastle": ["4-3-3", "4-5-1"],
        "Brighton": ["4-2-3-1", "3-4-2-1"],
        "Aston Villa": ["4-2-3-1", "4-4-2"],
        "West Ham": ["4-2-3-1", "4-1-4-1"],
    }

    formations = common_formations.get(team_name, ["4-4-2", "4-3-3"])

    return {
        "team": team_name,
        "recent_formations": formations[:limit],
        "most_common": formations[0] if formations else "4-4-2"
    }


@router.get("/team/{team_name}/svg", response_class=HTMLResponse)
async def get_team_formation_svg(
    team_name: str,
    formation: str = Query(default="4-3-3")
):
    """Get SVG for a single team's formation."""
    try:
        aggregator = DataAggregator()
        players = await aggregator.get_player_stats(team_name)

        # Sort by appearances to get likely starters
        players.sort(key=lambda x: x.get("appearances", 0), reverse=True)

        pitch = PitchSVG()
        svg = pitch.generate_single_team(
            formation=formation,
            players=players[:11],
            team_name=team_name
        )

        return HTMLResponse(content=svg, media_type="image/svg+xml")
    except Exception as e:
        logger.error(f"Failed to generate team formation SVG: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/available")
async def get_available_formations():
    """Get list of supported formations."""
    return {
        "formations": [
            {"code": "4-4-2", "name": "4-4-2 (Classic)"},
            {"code": "4-3-3", "name": "4-3-3 (Attack)"},
            {"code": "4-2-3-1", "name": "4-2-3-1 (Modern)"},
            {"code": "3-5-2", "name": "3-5-2 (Wing-backs)"},
            {"code": "3-4-3", "name": "3-4-3 (Attack)"},
            {"code": "5-3-2", "name": "5-3-2 (Defensive)"},
            {"code": "4-1-4-1", "name": "4-1-4-1 (Holding)"},
        ]
    }
