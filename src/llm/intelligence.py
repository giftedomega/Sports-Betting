"""LLM Intelligence Pipeline - processes data batches through Gemma for insights."""

import hashlib
import json
from datetime import datetime, timedelta
from typing import List, Dict, Optional

from src.llm.client import OllamaClient
from src.llm.intelligence_prompts import (
    TEAM_STATS_ANALYSIS_PROMPT,
    PLAYER_ANALYSIS_PROMPT,
    NEWS_INTELLIGENCE_PROMPT,
    ODDS_ANALYSIS_PROMPT,
    TEAM_PROFILE_SYNTHESIS_PROMPT,
    SEASON_PREDICTION_PROMPT,
)
from src.database.persistence import DatabasePersistence
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class IntelligencePipeline:
    """Processes incoming data batches through LLM for summarization and insight extraction."""

    def __init__(self):
        self.client = OllamaClient()
        self.db = DatabasePersistence()
        self.config = get_config()

    def _hash_data(self, data) -> str:
        """Create a hash of input data to avoid reprocessing."""
        return hashlib.sha256(json.dumps(data, sort_keys=True, default=str).encode()).hexdigest()

    def _parse_json_response(self, response: str) -> Dict:
        """Extract JSON from LLM response."""
        try:
            if "```json" in response:
                start = response.find("```json") + 7
                end = response.find("```", start)
                return json.loads(response[start:end].strip())
            elif "```" in response:
                start = response.find("```") + 3
                end = response.find("```", start)
                return json.loads(response[start:end].strip())
            else:
                start = response.find("{")
                if start != -1:
                    brace_count = 0
                    for i, c in enumerate(response[start:], start):
                        if c == "{":
                            brace_count += 1
                        elif c == "}":
                            brace_count -= 1
                            if brace_count == 0:
                                return json.loads(response[start:i + 1])
        except json.JSONDecodeError:
            pass
        return {}

    async def process_team_stats_batch(self, teams: List[Dict]) -> List[Dict]:
        """Process a batch of team stats through LLM for insights."""
        if not teams:
            return []

        data_hash = self._hash_data(teams)

        # Format stats for the prompt
        stats_text = ""
        for t in teams:
            stats_text += (
                f"\n{t.get('name')}: Pos {t.get('position')}, "
                f"P{t.get('played')} W{t.get('won')} D{t.get('drawn')} L{t.get('lost')}, "
                f"GF{t.get('goals_for')} GA{t.get('goals_against')}, Pts{t.get('points')}, "
                f"Form: {t.get('form', 'N/A')}"
            )
            if t.get("team_xg"):
                stats_text += f", xG: {t['team_xg']:.1f}, xGA: {t.get('team_xga', 0):.1f}"
            if t.get("possession"):
                stats_text += f", Poss: {t['possession']:.1f}%"

        try:
            prompt = TEAM_STATS_ANALYSIS_PROMPT.format(team_stats_data=stats_text)
            response = await self.client.generate_text(prompt=prompt, temperature=0.3)
            parsed = self._parse_json_response(response)

            insights_saved = []
            for insight in parsed.get("insights", []):
                saved_id = self.db.save_insight({
                    "category": "team_analysis",
                    "entity_type": "team",
                    "entity_name": insight.get("team"),
                    "summary": insight.get("summary", ""),
                    "key_points": [insight.get("key_stat", "")],
                    "raw_data_hash": data_hash,
                    "sentiment": insight.get("trend"),
                    "impact_level": insight.get("impact", "medium"),
                    "model_used": self.config.llm.model,
                    "expires_at": datetime.now() + timedelta(hours=self.config.intelligence.insight_ttl_hours),
                })
                if saved_id:
                    insights_saved.append(insight)

            logger.info(f"[INTELLIGENCE] Processed team stats: {len(insights_saved)} insights saved")
            return insights_saved

        except Exception as e:
            logger.error(f"[INTELLIGENCE] Team stats processing failed: {e}")
            return []

    async def process_news_batch(self, articles: List[Dict]) -> List[Dict]:
        """Extract actionable intelligence from news articles."""
        if not articles:
            return []

        news_text = ""
        for a in articles[:15]:
            news_text += f"\n[{a.get('source')}] {a.get('title')} - {a.get('description', '')[:200]}"
            if a.get("teams_mentioned"):
                news_text += f" (Teams: {', '.join(a['teams_mentioned'])})"
            news_text += f" [Sentiment: {a.get('sentiment', 'neutral')}, Impact: {a.get('impact', 'low')}]"

        try:
            prompt = NEWS_INTELLIGENCE_PROMPT.format(news_data=news_text)
            response = await self.client.generate_text(prompt=prompt, temperature=0.3)
            parsed = self._parse_json_response(response)

            insights_saved = []
            for intel in parsed.get("actionable_intel", []):
                saved_id = self.db.save_insight({
                    "category": "news_intelligence",
                    "entity_type": "team",
                    "entity_name": intel.get("team"),
                    "summary": intel.get("summary", ""),
                    "key_points": [intel.get("betting_impact", "")],
                    "confidence": intel.get("confidence"),
                    "impact_level": intel.get("impact", "medium"),
                    "model_used": self.config.llm.model,
                    "expires_at": datetime.now() + timedelta(hours=48),
                })
                if saved_id:
                    insights_saved.append(intel)

            logger.info(f"[INTELLIGENCE] Processed news: {len(insights_saved)} actionable items")
            return insights_saved

        except Exception as e:
            logger.error(f"[INTELLIGENCE] News processing failed: {e}")
            return []

    async def process_odds_batch(self, odds_data: List[Dict]) -> List[Dict]:
        """Analyze odds for value opportunities."""
        if not odds_data:
            return []

        odds_text = ""
        for o in odds_data:
            odds_text += (
                f"\n{o.get('home_team')} vs {o.get('away_team')}: "
                f"H {o.get('home_win_odds', 'N/A')} / "
                f"D {o.get('draw_odds', 'N/A')} / "
                f"A {o.get('away_win_odds', 'N/A')}"
            )
            if o.get("over_2_5_odds"):
                odds_text += f" | O2.5 {o['over_2_5_odds']} U2.5 {o.get('under_2_5_odds', 'N/A')}"

        try:
            prompt = ODDS_ANALYSIS_PROMPT.format(odds_data=odds_text)
            response = await self.client.generate_text(prompt=prompt, temperature=0.3)
            parsed = self._parse_json_response(response)

            for opp in parsed.get("value_opportunities", []):
                self.db.save_insight({
                    "category": "odds_analysis",
                    "entity_type": "match",
                    "entity_name": opp.get("match"),
                    "summary": opp.get("reasoning", ""),
                    "key_points": [f"{opp.get('market')}: {opp.get('selection')}"],
                    "confidence": opp.get("confidence"),
                    "impact_level": "high",
                    "model_used": self.config.llm.model,
                    "expires_at": datetime.now() + timedelta(hours=24),
                })

            logger.info(f"[INTELLIGENCE] Processed odds: {len(parsed.get('value_opportunities', []))} value opportunities")
            return parsed.get("value_opportunities", [])

        except Exception as e:
            logger.error(f"[INTELLIGENCE] Odds processing failed: {e}")
            return []

    async def aggregate_team_profile(self, team_name: str) -> str:
        """Synthesize all recent insights into a team profile for match prediction."""
        insights = self.db.get_team_insights(team_name, limit=20)

        if not insights:
            return f"No intelligence data available for {team_name}."

        insights_text = ""
        for i in insights:
            insights_text += (
                f"\n[{i.get('category')}] {i.get('summary')}"
                f" (Impact: {i.get('impact_level', 'medium')}, "
                f"Created: {i.get('created_at', 'unknown')})"
            )
            if i.get("key_points"):
                for kp in i["key_points"]:
                    insights_text += f"\n  - {kp}"

        try:
            prompt = TEAM_PROFILE_SYNTHESIS_PROMPT.format(
                team_name=team_name,
                insights_data=insights_text
            )
            response = await self.client.generate_text(prompt=prompt, temperature=0.3)
            parsed = self._parse_json_response(response)

            # Save the profile as a meta-insight
            self.db.save_insight({
                "category": "team_profile",
                "entity_type": "team",
                "entity_name": team_name,
                "summary": json.dumps(parsed) if parsed else response[:1000],
                "model_used": self.config.llm.model,
                "expires_at": datetime.now() + timedelta(hours=12),
            })

            # Return formatted text for use in match prediction context
            if parsed:
                profile_text = f"=== AI INTELLIGENCE PROFILE: {team_name} ===\n"
                profile_text += f"Form: {parsed.get('current_form', 'Unknown')}\n"
                profile_text += f"Strengths: {', '.join(parsed.get('strengths', []))}\n"
                profile_text += f"Weaknesses: {', '.join(parsed.get('weaknesses', []))}\n"
                profile_text += f"Key Players: {', '.join(parsed.get('key_players', []))}\n"
                profile_text += f"Injury Impact: {parsed.get('injury_impact', 'Unknown')}\n"
                profile_text += f"Tactical Notes: {parsed.get('tactical_notes', 'N/A')}\n"
                profile_text += f"Betting Angles: {', '.join(parsed.get('betting_angles', []))}\n"
                profile_text += f"Risk Factors: {', '.join(parsed.get('risk_factors', []))}\n"
                profile_text += f"Rating: {parsed.get('overall_rating', 'N/A')}/100"
                return profile_text
            return response[:1000]

        except Exception as e:
            logger.error(f"[INTELLIGENCE] Profile synthesis failed for {team_name}: {e}")
            return f"Intelligence profile unavailable for {team_name}."

    async def generate_season_prediction(self) -> Dict:
        """Generate full season prediction using accumulated intelligence."""
        teams = self.db.get_teams()
        if not teams:
            return {"error": "No team data available"}

        league_text = "Current Premier League Standings:\n"
        for t in teams:
            league_text += (
                f"{t.get('position', '?')}. {t.get('name')} - "
                f"P{t.get('played', 0)} W{t.get('won', 0)} D{t.get('drawn', 0)} L{t.get('lost', 0)} "
                f"GF{t.get('goals_for', 0)} GA{t.get('goals_against', 0)} Pts{t.get('points', 0)}"
            )
            if t.get("team_xg"):
                league_text += f" xG{t['team_xg']:.1f} xGA{t.get('team_xga', 0):.1f}"
            league_text += "\n"

        try:
            prompt = SEASON_PREDICTION_PROMPT.format(league_data=league_text)
            response = await self.client.generate_text(prompt=prompt, temperature=0.4)
            parsed = self._parse_json_response(response)

            if parsed:
                self.db.save_insight({
                    "category": "season_prediction",
                    "entity_type": "league",
                    "entity_name": "Premier League",
                    "summary": json.dumps(parsed),
                    "model_used": self.config.llm.model,
                    "expires_at": datetime.now() + timedelta(hours=168),
                })

            logger.info("[INTELLIGENCE] Season prediction generated")
            return parsed or {"error": "Failed to parse season prediction"}

        except Exception as e:
            logger.error(f"[INTELLIGENCE] Season prediction failed: {e}")
            return {"error": str(e)}
