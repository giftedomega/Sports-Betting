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
        self._intelligence = None

    @property
    def intelligence(self):
        """Lazy-load intelligence pipeline."""
        if self._intelligence is None:
            try:
                from src.llm.intelligence import IntelligencePipeline
                self._intelligence = IntelligencePipeline()
            except Exception as e:
                logger.warning(f"Intelligence pipeline unavailable: {e}")
        return self._intelligence

    async def analyze_match(
        self,
        fixture: Dict,
        home_team_data: Dict,
        away_team_data: Dict,
        h2h_history: Optional[List[Dict]] = None,
        news_context: Optional[List[Dict]] = None,
        injuries: Optional[Dict] = None,
        odds_data: Optional[Dict] = None,
        weather_data: Optional[Dict] = None,
    ) -> Dict:
        """Perform comprehensive match analysis for betting predictions."""
        home_team = fixture.get("home_team", home_team_data.get("name", "Home"))
        away_team = fixture.get("away_team", away_team_data.get("name", "Away"))

        try:
            # Get intelligence profiles if available
            intel_home = None
            intel_away = None
            if self.intelligence:
                try:
                    intel_home = await self.intelligence.aggregate_team_profile(home_team)
                    intel_away = await self.intelligence.aggregate_team_profile(away_team)
                except Exception as e:
                    logger.warning(f"Intelligence profiles unavailable: {e}")

            # Build context with all available data
            context = build_match_context(
                home_team_data=home_team_data,
                away_team_data=away_team_data,
                h2h_history=h2h_history,
                news_articles=news_context,
                injuries=injuries,
                odds_data=odds_data,
                weather_data=weather_data,
                intelligence_home=intel_home,
                intelligence_away=intel_away,
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

            # Include odds in response if available
            if odds_data:
                analysis["odds"] = {
                    "home_win": odds_data.get("home_win_odds"),
                    "draw": odds_data.get("draw_odds"),
                    "away_win": odds_data.get("away_win_odds"),
                    "over_2_5": odds_data.get("over_2_5_odds"),
                    "under_2_5": odds_data.get("under_2_5_odds"),
                }

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
        """Parse AI response into structured format."""
        try:
            json_text = None

            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                json_text = response[start:end].strip()
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                json_text = response[start:end].strip()

            if not json_text or not json_text.startswith("{"):
                start_idx = response.find("{")
                if start_idx != -1:
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
                analysis.setdefault("predicted_outcome", "unknown")
                analysis.setdefault("confidence", 0)
                analysis.setdefault("recommended_bets", [])
                analysis.setdefault("risk_level", "medium")
                analysis.setdefault("key_factors", [])
                analysis.setdefault("summary", "")
                return analysis

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
        news: Optional[List[Dict]] = None,
        odds: Optional[List[Dict]] = None,
    ) -> List[Dict]:
        """Analyze multiple fixtures."""
        results = []

        # Build odds lookup
        odds_lookup = {}
        if odds:
            for o in odds:
                key = f"{o.get('home_team')}_{o.get('away_team')}"
                odds_lookup[key] = o

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

            # Get odds for this fixture
            fixture_odds = odds_lookup.get(f"{home_team}_{away_team}")

            analysis = await self.analyze_match(
                fixture=fixture,
                home_team_data=home_data,
                away_team_data=away_data,
                news_context=fixture_news[:10],
                odds_data=fixture_odds,
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
        """Quick prediction with minimal data."""
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
