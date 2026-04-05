"""Prompt templates for AI betting analysis."""

BETTING_ANALYSIS_SYSTEM_PROMPT = """You are an expert football betting analyst specializing in Premier League matches.
You analyze team statistics, form, head-to-head records, injuries, lineups, and news to provide betting predictions.

Your analysis must be:
1. Data-driven and objective
2. Consider all available information
3. Identify value bets (where odds may be mispriced)
4. Provide clear confidence levels
5. Highlight key risk factors

IMPORTANT: Always respond with valid JSON in the specified format. No explanations outside the JSON structure."""

BETTING_ANALYSIS_PROMPT = """Analyze this Premier League match for betting opportunities:

**Match:** {match}
**Date:** {date}

{context}

Provide your analysis in the following JSON format:
{{
    "predicted_outcome": "home_win|draw|away_win",
    "predicted_score": {{"home": X, "away": Y}},
    "confidence": 0-100,
    "key_factors": [
        "Factor 1 influencing prediction",
        "Factor 2 influencing prediction",
        "Factor 3 influencing prediction"
    ],
    "recommended_bets": [
        {{
            "market": "1X2|Over/Under|BTTS|Correct Score|etc",
            "selection": "specific selection",
            "odds_value": "good|fair|poor",
            "confidence": 0-100,
            "reasoning": "why this bet is recommended"
        }}
    ],
    "value_bets": [
        {{
            "market": "market type",
            "selection": "selection",
            "min_odds": X.XX,
            "reasoning": "why odds should be higher"
        }}
    ],
    "risk_factors": [
        "Risk 1",
        "Risk 2"
    ],
    "risk_level": "low|medium|high",
    "summary": "2-3 sentence summary of the analysis and main betting recommendation"
}}"""

MATCH_CONTEXT_TEMPLATE = """
=== HOME TEAM: {home_team} ===
Position: {home_position}
Form (last 5): {home_form}
Played: {home_played} | Won: {home_won} | Drawn: {home_drawn} | Lost: {home_lost}
Goals: {home_gf} scored, {home_ga} conceded
Points: {home_points}

=== AWAY TEAM: {away_team} ===
Position: {away_position}
Form (last 5): {away_form}
Played: {away_played} | Won: {away_won} | Drawn: {away_drawn} | Lost: {away_lost}
Goals: {away_gf} scored, {away_ga} conceded
Points: {away_points}

=== HEAD-TO-HEAD ===
{h2h_summary}

=== RECENT NEWS ===
{news_summary}

=== INJURIES/SUSPENSIONS ===
{injuries_summary}
"""

NEWS_SUMMARY_TEMPLATE = """- [{source}] {title} ({sentiment}, {impact} impact)"""

H2H_SUMMARY_TEMPLATE = """Last {count} meetings:
{home_team} wins: {home_wins}
{away_team} wins: {away_wins}
Draws: {draws}
Recent results: {recent_results}"""


def build_match_context(
    home_team_data: dict,
    away_team_data: dict,
    h2h_history: list = None,
    news_articles: list = None,
    injuries: dict = None
) -> str:
    """Build context string for AI analysis.

    Args:
        home_team_data: Home team statistics
        away_team_data: Away team statistics
        h2h_history: Head-to-head match history
        news_articles: Recent news articles
        injuries: Injury/suspension information

    Returns:
        Formatted context string
    """
    # Build H2H summary
    h2h_summary = "No historical data available"
    if h2h_history:
        home_wins = sum(1 for m in h2h_history if m.get("winner") == home_team_data.get("name"))
        away_wins = sum(1 for m in h2h_history if m.get("winner") == away_team_data.get("name"))
        draws = len(h2h_history) - home_wins - away_wins

        recent_results = []
        for m in h2h_history[:5]:
            score = f"{m.get('team_a_score', '?')}-{m.get('team_b_score', '?')}"
            recent_results.append(score)

        h2h_summary = H2H_SUMMARY_TEMPLATE.format(
            count=len(h2h_history),
            home_team=home_team_data.get("name", "Home"),
            away_team=away_team_data.get("name", "Away"),
            home_wins=home_wins,
            away_wins=away_wins,
            draws=draws,
            recent_results=", ".join(recent_results) if recent_results else "N/A"
        )

    # Build news summary
    news_summary = "No recent news"
    if news_articles:
        news_lines = []
        for article in news_articles[:5]:
            news_lines.append(NEWS_SUMMARY_TEMPLATE.format(
                source=article.get("source", "Unknown"),
                title=article.get("title", "")[:80],
                sentiment=article.get("sentiment", "neutral"),
                impact=article.get("impact", "low")
            ))
        news_summary = "\n".join(news_lines)

    # Build injuries summary
    injuries_summary = "No reported injuries or suspensions"
    if injuries:
        injury_lines = []
        home_injuries = injuries.get("home", [])
        away_injuries = injuries.get("away", [])
        if home_injuries:
            injury_lines.append(f"{home_team_data.get('name', 'Home')}: {', '.join(home_injuries)}")
        if away_injuries:
            injury_lines.append(f"{away_team_data.get('name', 'Away')}: {', '.join(away_injuries)}")
        if injury_lines:
            injuries_summary = "\n".join(injury_lines)

    # Build full context
    context = MATCH_CONTEXT_TEMPLATE.format(
        home_team=home_team_data.get("name", "Home Team"),
        home_position=home_team_data.get("position", "N/A"),
        home_form=home_team_data.get("form", "N/A"),
        home_played=home_team_data.get("played", 0),
        home_won=home_team_data.get("won", 0),
        home_drawn=home_team_data.get("drawn", 0),
        home_lost=home_team_data.get("lost", 0),
        home_gf=home_team_data.get("goals_for", 0),
        home_ga=home_team_data.get("goals_against", 0),
        home_points=home_team_data.get("points", 0),
        away_team=away_team_data.get("name", "Away Team"),
        away_position=away_team_data.get("position", "N/A"),
        away_form=away_team_data.get("form", "N/A"),
        away_played=away_team_data.get("played", 0),
        away_won=away_team_data.get("won", 0),
        away_drawn=away_team_data.get("drawn", 0),
        away_lost=away_team_data.get("lost", 0),
        away_gf=away_team_data.get("goals_for", 0),
        away_ga=away_team_data.get("goals_against", 0),
        away_points=away_team_data.get("points", 0),
        h2h_summary=h2h_summary,
        news_summary=news_summary,
        injuries_summary=injuries_summary
    )

    return context
