"""Prompt templates for the LLM intelligence pipeline."""

TEAM_STATS_ANALYSIS_PROMPT = """Analyze these Premier League team statistics and identify key insights:

{team_stats_data}

Respond with JSON:
{{
    "insights": [
        {{
            "team": "team name",
            "summary": "1-2 sentence insight",
            "trend": "improving|declining|stable",
            "key_stat": "the most notable statistic",
            "impact": "high|medium|low"
        }}
    ],
    "league_trends": "2-3 sentences about overall league trends",
    "surprise_findings": ["any unexpected patterns"]
}}"""

PLAYER_ANALYSIS_PROMPT = """Analyze these Premier League player statistics for betting-relevant insights:

{player_stats_data}

Focus on: standout performers, xG overperformance/underperformance (goals vs xG), injury impacts, form trends.

Respond with JSON:
{{
    "standout_players": [
        {{
            "name": "player name",
            "team": "team",
            "insight": "why notable",
            "xg_analysis": "overperforming/underperforming/on-par with xG",
            "impact": "high|medium|low"
        }}
    ],
    "regression_candidates": ["players likely to regress to mean"],
    "form_watches": ["players on hot/cold streaks"]
}}"""

NEWS_INTELLIGENCE_PROMPT = """Extract actionable betting intelligence from these football news articles:

{news_data}

Extract: confirmed injuries, transfer impacts, tactical changes, manager comments on team selection, any information that affects match outcomes.

Respond with JSON:
{{
    "actionable_intel": [
        {{
            "team": "team name",
            "category": "injury|tactical|transfer|selection|morale",
            "summary": "what happened",
            "betting_impact": "how this affects upcoming matches",
            "confidence": 0-100,
            "impact": "high|medium|low"
        }}
    ],
    "key_absences": [
        {{
            "player": "name",
            "team": "team",
            "reason": "injury/suspension/other",
            "expected_return": "date or timeframe if known"
        }}
    ]
}}"""

ODDS_ANALYSIS_PROMPT = """Analyze these Premier League match odds for value opportunities:

{odds_data}

Compare the odds to the underlying statistics and identify where the market may be mispricing.

Respond with JSON:
{{
    "value_opportunities": [
        {{
            "match": "Team A vs Team B",
            "market": "1X2|Over/Under|BTTS",
            "selection": "the value selection",
            "current_odds": 0.00,
            "fair_odds": 0.00,
            "reasoning": "why this is value",
            "confidence": 0-100
        }}
    ],
    "market_consensus": "brief summary of what the market is pricing in",
    "contrarian_picks": ["any matches where stats disagree with odds"]
}}"""

TEAM_PROFILE_SYNTHESIS_PROMPT = """Synthesize these individual insights into a comprehensive betting profile for {team_name}:

{insights_data}

Create a profile that would be useful for predicting their next match outcome.

Respond with JSON:
{{
    "team": "{team_name}",
    "current_form": "description of recent form",
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1", "weakness 2"],
    "key_players": ["player and why important"],
    "injury_impact": "how current injuries affect the team",
    "tactical_notes": "any tactical patterns or changes",
    "betting_angles": ["betting angle 1", "betting angle 2"],
    "risk_factors": ["factor 1", "factor 2"],
    "overall_rating": 0-100
}}"""

SEASON_PREDICTION_PROMPT = """Based on accumulated intelligence about all 20 Premier League teams, predict the end-of-season outcomes:

{league_data}

Respond with JSON:
{{
    "title_race": [
        {{"team": "name", "probability": 0-100, "reasoning": "why"}}
    ],
    "top_4": [
        {{"team": "name", "probability": 0-100}}
    ],
    "relegation": [
        {{"team": "name", "probability": 0-100, "reasoning": "why"}}
    ],
    "golden_boot": [
        {{"player": "name", "team": "team", "predicted_goals": 0, "probability": 0-100}}
    ],
    "predicted_table": [
        {{"position": 1, "team": "name", "predicted_points": 0}}
    ],
    "key_narratives": ["narrative 1", "narrative 2"]
}}"""
