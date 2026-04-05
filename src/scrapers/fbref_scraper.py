"""FBref scraper using soccerdata library."""

import asyncio
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from src.scrapers.base_scraper import BaseScraper, CacheConfig
from src.utils.logger import get_logger
from src.utils.config import get_config

logger = get_logger(__name__)


class FBrefScraper(BaseScraper):
    """Scraper for FBref data via soccerdata library."""

    def __init__(self):
        """Initialize FBref scraper."""
        config = get_config()
        rate_limit = config.scraping.rate_limits.get("fbref", 3)
        super().__init__(rate_limit_seconds=rate_limit)

        self.season = config.scraping.season
        self._fbref = None
        self._loop = None

    def _get_current_season(self) -> str:
        """Get current season string (e.g., '2425' for 2024-25)."""
        now = datetime.now()
        if now.month >= 8:
            return f"{now.year % 100}{(now.year + 1) % 100}"
        else:
            return f"{(now.year - 1) % 100}{now.year % 100}"

    @property
    def fbref(self):
        """Lazy-load FBref scraper."""
        if self._fbref is None:
            try:
                import soccerdata as sd
                self._fbref = sd.FBref(
                    leagues="ENG-Premier League",
                    seasons=self.season or self._get_current_season()
                )
                logger.info(f"Initialized FBref scraper for season {self.season}")
            except ImportError:
                logger.error("soccerdata not installed. Run: pip install soccerdata")
                raise
            except Exception as e:
                logger.error(f"Failed to initialize FBref: {e}")
                raise
        return self._fbref

    async def fetch_fixtures(self) -> List[Dict]:
        """Fetch upcoming fixtures from FBref."""
        cache_key = "fixtures"
        cached = self._get_cached(cache_key, CacheConfig.FIXTURES)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            loop = asyncio.get_event_loop()
            schedule = await loop.run_in_executor(None, self.fbref.read_schedule)

            fixtures = []
            for idx, row in schedule.iterrows():
                match_date = row.get("date")
                if hasattr(match_date, "to_pydatetime"):
                    match_date = match_date.to_pydatetime()

                fixture = {
                    "home_team": str(row.get("home_team", "")),
                    "away_team": str(row.get("away_team", "")),
                    "match_date": match_date,
                    "venue": str(row.get("venue", "")),
                    "gameweek": row.get("round"),
                    "fbref_match_id": str(idx) if idx else None,
                    "home_score": row.get("home_score"),
                    "away_score": row.get("away_score"),
                }
                fixtures.append(fixture)

            logger.info(f"Fetched {len(fixtures)} fixtures from FBref")
            self._set_cache(cache_key, fixtures)
            return fixtures

        except Exception as e:
            logger.error(f"Failed to fetch fixtures: {e}")
            return []

    async def fetch_team_stats(self) -> List[Dict]:
        """Fetch team season statistics by calculating from match results."""
        cache_key = "team_stats"
        cached = self._get_cached(cache_key, CacheConfig.LEAGUE_TABLE)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            loop = asyncio.get_event_loop()

            # Get schedule with match results to calculate standings
            schedule = await loop.run_in_executor(
                None,
                lambda: self.fbref.read_schedule()
            )

            logger.info(f"[FBREF] Schedule has {len(schedule)} matches")

            # Calculate standings from completed matches
            team_stats = {}

            import pandas as pd
            for idx, row in schedule.iterrows():
                score = row.get("score")
                # Handle NA values properly - pandas NA can't be used in boolean context
                if pd.isna(score) or score is None or str(score).lower() in ("nan", "none", ""):
                    continue  # Skip unplayed matches

                home_team = str(row.get("home_team", ""))
                away_team = str(row.get("away_team", ""))

                if not home_team or not away_team:
                    continue

                # Parse score (format: "4–2" or "4-2")
                try:
                    score_str = str(score).replace("–", "-").replace("—", "-")
                    parts = score_str.split("-")
                    if len(parts) != 2:
                        continue
                    home_score = int(parts[0].strip())
                    away_score = int(parts[1].strip())
                except (ValueError, AttributeError):
                    continue

                # Initialize teams if not seen
                for team in [home_team, away_team]:
                    if team not in team_stats:
                        team_stats[team] = {
                            "name": team,
                            "played": 0,
                            "won": 0,
                            "drawn": 0,
                            "lost": 0,
                            "goals_for": 0,
                            "goals_against": 0,
                            "points": 0,
                        }

                # Update home team stats
                team_stats[home_team]["played"] += 1
                team_stats[home_team]["goals_for"] += home_score
                team_stats[home_team]["goals_against"] += away_score
                if home_score > away_score:
                    team_stats[home_team]["won"] += 1
                    team_stats[home_team]["points"] += 3
                elif home_score == away_score:
                    team_stats[home_team]["drawn"] += 1
                    team_stats[home_team]["points"] += 1
                else:
                    team_stats[home_team]["lost"] += 1

                # Update away team stats
                team_stats[away_team]["played"] += 1
                team_stats[away_team]["goals_for"] += away_score
                team_stats[away_team]["goals_against"] += home_score
                if away_score > home_score:
                    team_stats[away_team]["won"] += 1
                    team_stats[away_team]["points"] += 3
                elif home_score == away_score:
                    team_stats[away_team]["drawn"] += 1
                    team_stats[away_team]["points"] += 1
                else:
                    team_stats[away_team]["lost"] += 1

            teams = list(team_stats.values())

            # Sort by points (desc), then goal difference (desc), then goals for (desc)
            teams.sort(key=lambda x: (
                -x["points"],
                -(x["goals_for"] - x["goals_against"]),
                -x["goals_for"]
            ))

            # Assign positions
            for i, team in enumerate(teams, 1):
                team["position"] = i

            logger.info(f"[FBREF] Calculated standings for {len(teams)} teams from match results")
            if teams:
                logger.info(f"[FBREF] Top team: {teams[0]}")
            self._set_cache(cache_key, teams)
            return teams

        except Exception as e:
            logger.error(f"Failed to fetch team stats: {e}", exc_info=True)
            return []

    async def fetch_player_stats(self, team_name: Optional[str] = None) -> List[Dict]:
        """Fetch player statistics."""
        cache_key = f"player_stats_{team_name or 'all'}"
        cached = self._get_cached(cache_key, CacheConfig.PLAYER_INFO)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            loop = asyncio.get_event_loop()
            stats = await loop.run_in_executor(
                None,
                lambda: self.fbref.read_player_season_stats(stat_type="standard")
            )

            players = []
            for idx, row in stats.iterrows():
                player_team = idx[0] if isinstance(idx, tuple) else None
                player_name = idx[1] if isinstance(idx, tuple) and len(idx) > 1 else str(idx)

                if team_name and player_team != team_name:
                    continue

                player = {
                    "name": player_name,
                    "team": player_team,
                    "position": str(row.get("Pos", "")),
                    "appearances": int(row.get("MP", 0) or 0),
                    "goals": int(row.get("Gls", 0) or 0),
                    "assists": int(row.get("Ast", 0) or 0),
                    "minutes_played": int(row.get("Min", 0) or 0),
                    "yellow_cards": int(row.get("CrdY", 0) or 0),
                    "red_cards": int(row.get("CrdR", 0) or 0),
                }
                players.append(player)

            logger.info(f"Fetched {len(players)} player records")
            self._set_cache(cache_key, players)
            return players

        except Exception as e:
            logger.error(f"Failed to fetch player stats: {e}")
            return []

    async def fetch_league_table(self) -> List[Dict]:
        """Fetch current league table."""
        return await self.fetch_team_stats()

    async def fetch_match_lineups(self, match_id: str) -> Dict:
        """Fetch lineups for a specific match."""
        cache_key = f"lineup_{match_id}"
        cached = self._get_cached(cache_key, CacheConfig.LINEUPS)
        if cached:
            return cached

        await self._rate_limit_wait()

        try:
            loop = asyncio.get_event_loop()
            lineups = await loop.run_in_executor(
                None,
                lambda: self.fbref.read_lineup(match_id=match_id)
            )

            result = {
                "match_id": match_id,
                "home_lineup": [],
                "away_lineup": [],
            }

            if lineups is not None and not lineups.empty:
                for idx, row in lineups.iterrows():
                    player_data = {
                        "name": str(row.get("player", "")),
                        "position": str(row.get("position", "")),
                        "number": row.get("shirt_number"),
                    }
                    if row.get("team") == "home":
                        result["home_lineup"].append(player_data)
                    else:
                        result["away_lineup"].append(player_data)

            self._set_cache(cache_key, result)
            return result

        except Exception as e:
            logger.error(f"Failed to fetch lineups for {match_id}: {e}")
            return {"match_id": match_id, "home_lineup": [], "away_lineup": []}
