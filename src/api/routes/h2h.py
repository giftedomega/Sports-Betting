"""Head-to-Head API routes."""

from fastapi import APIRouter, HTTPException, Query

from src.scrapers.aggregator import DataAggregator
from src.utils.logger import get_logger

logger = get_logger(__name__)
router = APIRouter()


@router.get("/{team_a}/{team_b}")
async def get_head_to_head(
    team_a: str,
    team_b: str,
    limit: int = Query(default=10, ge=1, le=50, description="Number of past meetings")
):
    """Get head-to-head history between two teams."""
    try:
        aggregator = DataAggregator()

        # Get fixtures that are finished to find H2H
        all_fixtures = await aggregator.fbref.fetch_fixtures()

        # Filter for matches between these two teams
        h2h_matches = []
        for fixture in all_fixtures:
            home = fixture.get("home_team", "")
            away = fixture.get("away_team", "")
            home_score = fixture.get("home_score")
            away_score = fixture.get("away_score")

            # Check if this is a match between the two teams
            if (home.lower() == team_a.lower() and away.lower() == team_b.lower()) or \
               (home.lower() == team_b.lower() and away.lower() == team_a.lower()):

                # Only include finished matches with scores
                if home_score is not None and away_score is not None:
                    # Determine winner
                    if home_score > away_score:
                        winner = home
                    elif away_score > home_score:
                        winner = away
                    else:
                        winner = "draw"

                    h2h_matches.append({
                        "date": fixture.get("match_date"),
                        "home_team": home,
                        "away_team": away,
                        "home_score": home_score,
                        "away_score": away_score,
                        "winner": winner,
                        "venue": fixture.get("venue"),
                        "competition": fixture.get("competition", "Premier League")
                    })

        # Sort by date (most recent first)
        h2h_matches.sort(key=lambda x: x.get("date") or "", reverse=True)
        h2h_matches = h2h_matches[:limit]

        # Calculate summary stats
        team_a_wins = sum(1 for m in h2h_matches if m["winner"].lower() == team_a.lower())
        team_b_wins = sum(1 for m in h2h_matches if m["winner"].lower() == team_b.lower())
        draws = sum(1 for m in h2h_matches if m["winner"] == "draw")

        # Goal stats
        team_a_goals = 0
        team_b_goals = 0
        for m in h2h_matches:
            if m["home_team"].lower() == team_a.lower():
                team_a_goals += m["home_score"]
                team_b_goals += m["away_score"]
            else:
                team_a_goals += m["away_score"]
                team_b_goals += m["home_score"]

        return {
            "team_a": team_a,
            "team_b": team_b,
            "total_matches": len(h2h_matches),
            "summary": {
                f"{team_a}_wins": team_a_wins,
                f"{team_b}_wins": team_b_wins,
                "draws": draws,
                f"{team_a}_goals": team_a_goals,
                f"{team_b}_goals": team_b_goals
            },
            "matches": h2h_matches
        }

    except Exception as e:
        logger.error(f"Failed to get H2H for {team_a} vs {team_b}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{team_a}/{team_b}/stats")
async def get_head_to_head_stats(team_a: str, team_b: str):
    """Get statistical summary of head-to-head record."""
    h2h_data = await get_head_to_head(team_a, team_b, limit=20)

    matches = h2h_data.get("matches", [])
    if not matches:
        return {
            "team_a": team_a,
            "team_b": team_b,
            "message": "No head-to-head matches found"
        }

    # Calculate additional stats
    total_goals = sum(m["home_score"] + m["away_score"] for m in matches)
    avg_goals = total_goals / len(matches) if matches else 0

    # Both teams scored
    btts = sum(1 for m in matches if m["home_score"] > 0 and m["away_score"] > 0)
    btts_percentage = (btts / len(matches) * 100) if matches else 0

    # Over 2.5 goals
    over_2_5 = sum(1 for m in matches if m["home_score"] + m["away_score"] > 2)
    over_2_5_percentage = (over_2_5 / len(matches) * 100) if matches else 0

    return {
        "team_a": team_a,
        "team_b": team_b,
        "total_matches": len(matches),
        "summary": h2h_data.get("summary"),
        "statistics": {
            "average_goals_per_match": round(avg_goals, 2),
            "btts_percentage": round(btts_percentage, 1),
            "over_2_5_percentage": round(over_2_5_percentage, 1),
            "most_common_result": _get_most_common_result(matches)
        }
    }


def _get_most_common_result(matches):
    """Get most common scoreline."""
    from collections import Counter

    results = []
    for m in matches:
        result = f"{m['home_score']}-{m['away_score']}"
        results.append(result)

    if not results:
        return None

    counter = Counter(results)
    most_common = counter.most_common(1)[0]
    return {
        "score": most_common[0],
        "occurrences": most_common[1]
    }
