"""AI-powered betting analysis using Ollama/Gemma."""

import json
from datetime import datetime
from typing import Dict, List, Optional

from src.llm.client import OllamaClient
from src.llm.prompts import (
    BETTING_ANALYSIS_SYSTEM_PROMPT,
    BETTING_ANALYSIS_PROMPT,
    build_match_context
)
from src.utils.logger import get_logger

logger = get_logger(__name__)


class BettingAnalyzer:
    """AI-powered betting analysis using Gemma model."""

    def __init__(self):
        """Initialize betting analyzer."""
        self.client = OllamaClient()

    async def analyze_match(
        self,
        fixture: Dict,
        home_team_data: Dict,
        away_team_data: Dict,
        h2h_history: Optional[List[Dict]] = None,
        news_context: Optional[List[Dict]] = None,
        injuries: Optional[Dict] = None,
    ) -> Dict:
        """Perform comprehensive match analysis for betting predictions.

        Args:
            fixture: Match fixture details
            home_team_data: Home team stats and form
            away_team_data: Away team stats and form
            h2h_history: Head-to-head match history
            news_context: Recent news about teams
            injuries: Injury/suspension information

        Returns:
            Analysis dict with predictions and recommendations
        """
        home_team = fixture.get("home_team", home_team_data.get("name", "Home"))
        away_team = fixture.get("away_team", away_team_data.get("name", "Away"))

        try:
            # Build context
            context = build_match_context(
                home_team_data=home_team_data,
                away_team_data=away_team_data,
                h2h_history=h2h_history,
                news_articles=news_context,
                injuries=injuries
            )

            # Build prompt
            match_date = fixture.get("match_date")
            if hasattr(match_date, "strftime"):
                date_str = match_date.strftime("%Y-%m-%d %H:%M")
            else:
                date_str = str(match_date)

            prompt = BETTING_ANALYSIS_PROMPT.format(
                match=f"{home_team} vs {away_team}",
                date=date_str,
                context=context
            )

            # Generate analysis
            response = await self.client.generate_text(
                prompt=prompt,
                system_prompt=BETTING_ANALYSIS_SYSTEM_PROMPT,
                temperature=0.3,
            )

            # Parse response
            analysis = self._parse_response(response)

            # Add metadata
            analysis["fixture_id"] = fixture.get("id")
            analysis["home_team"] = home_team
            analysis["away_team"] = away_team
            analysis["analyzed_at"] = datetime.now().isoformat()

            logger.info(f"Completed analysis for {home_team} vs {away_team}")
            return analysis

        except Exception as e:
            logger.error(f"Match analysis failed: {e}")
            return {
                "error": str(e),
                "fixture_id": fixture.get("id"),
                "home_team": home_team,
                "away_team": away_team,
                "predicted_outcome": "unknown",
                "confidence": 0,
                "recommended_bets": [],
                "risk_level": "high"
            }

    def _parse_response(self, response: str) -> Dict:
        """Parse AI response into structured format.

        Args:
            response: Raw AI response text

        Returns:
            Parsed analysis dict
        """
        try:
            # Try to extract JSON from response
            json_text = None

            # Method 1: Look for ```json code block
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_text = response[start:end].strip()

            # Method 2: Look for ``` code block
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_text = response[start:end].strip()

            # Method 3: Find JSON object
            if not json_text or not json_text.startswith("{"):
                start_idx = response.find("{")
                if start_idx != -1:
                    # Find matching closing brace
                    brace_count = 0
                    end_idx = start_idx
                    for i, char in enumerate(response[start_idx:], start_idx):
                        if char == "{":
                            brace_count += 1
                        elif char == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                end_idx = i
                                break
                    if end_idx > start_idx:
                        json_text = response[start_idx:end_idx + 1]

            if json_text:
                analysis = json.loads(json_text)
                # Ensure required fields exist
                analysis.setdefault("predicted_outcome", "unknown")
                analysis.setdefault("confidence", 0)
                analysis.setdefault("recommended_bets", [])
                analysis.setdefault("risk_level", "medium")
                analysis.setdefault("key_factors", [])
                analysis.setdefault("summary", "")
                return analysis

            # Return default if parsing fails
            logger.warning("Failed to parse JSON from response")
            return {
                "predicted_outcome": "unknown",
                "confidence": 0,
                "reasoning": response[:500],
                "recommended_bets": [],
                "risk_level": "high",
                "key_factors": [],
                "summary": "Analysis parsing failed"
            }

        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}")
            return {
                "predicted_outcome": "unknown",
                "confidence": 0,
                "reasoning": response[:500],
                "recommended_bets": [],
                "risk_level": "high",
                "key_factors": [],
                "summary": "Analysis parsing failed"
            }

    async def analyze_fixtures(
        self,
        fixtures: List[Dict],
        team_stats: Dict[str, Dict],
        news: Optional[List[Dict]] = None
    ) -> List[Dict]:
        """Analyze multiple fixtures.

        Args:
            fixtures: List of fixtures to analyze
            team_stats: Dict of team name -> stats
            news: Recent news articles

        Returns:
            List of analysis results
        """
        results = []

        for fixture in fixtures:
            home_team = fixture.get("home_team")
            away_team = fixture.get("away_team")

            home_data = team_stats.get(home_team, {"name": home_team})
            away_data = team_stats.get(away_team, {"name": away_team})

            # Filter news for these teams
            fixture_news = []
            if news:
                for article in news:
                    teams_mentioned = article.get("teams_mentioned", [])
                    if home_team in teams_mentioned or away_team in teams_mentioned:
                        fixture_news.append(article)

            analysis = await self.analyze_match(
                fixture=fixture,
                home_team_data=home_data,
                away_team_data=away_data,
                news_context=fixture_news[:10]
            )
            results.append(analysis)

        return results

    async def quick_prediction(
        self,
        home_team: str,
        away_team: str,
        home_position: int = 10,
        away_position: int = 10
    ) -> Dict:
        """Quick prediction with minimal data.

        Args:
            home_team: Home team name
            away_team: Away team name
            home_position: Home team league position
            away_position: Away team league position

        Returns:
            Quick analysis dict
        """
        fixture = {
            "home_team": home_team,
            "away_team": away_team,
            "match_date": datetime.now()
        }

        home_data = {"name": home_team, "position": home_position}
        away_data = {"name": away_team, "position": away_position}

        return await self.analyze_match(
            fixture=fixture,
            home_team_data=home_data,
            away_team_data=away_data
        )
