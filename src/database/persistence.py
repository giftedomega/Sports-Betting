"""Database persistence layer for scraped data."""

from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from sqlalchemy import create_engine, func
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import (
    Base, Team, Player, Fixture, Formation, HeadToHead,
    NewsArticle, Prediction, ScrapingLog, DataInsight,
    PlayerMatchRating, TrackedBet, BankrollEntry, get_database_url
)
from src.utils.config import get_config
from src.utils.logger import get_logger

logger = get_logger(__name__)


class DatabasePersistence:
    """Handles persisting scraped data to SQLite database."""

    def __init__(self):
        """Initialize database connection."""
        config = get_config()
        db_path = Path(config.database.path)
        db_path.parent.mkdir(parents=True, exist_ok=True)

        self.engine = create_engine(get_database_url(str(db_path)))
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

        # Run migrations for new columns on existing tables
        from src.database.migrations import run_migrations
        run_migrations(str(db_path))

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()

    # ── Teams ──────────────────────────────────────────────

    def save_teams(self, teams_data: List[Dict]) -> int:
        """Save team data to database."""
        session = self.get_session()
        count = 0

        try:
            for team_data in teams_data:
                name = team_data.get("name")
                if not name:
                    continue

                team = session.query(Team).filter(Team.name == name).first()
                if team:
                    team.position = team_data.get("position", team.position)
                    team.played = team_data.get("played", team.played)
                    team.won = team_data.get("won", team.won)
                    team.drawn = team_data.get("drawn", team.drawn)
                    team.lost = team_data.get("lost", team.lost)
                    team.goals_for = team_data.get("goals_for", team.goals_for)
                    team.goals_against = team_data.get("goals_against", team.goals_against)
                    team.points = team_data.get("points", team.points)
                    team.form = team_data.get("form", team.form)
                    # Advanced stats
                    if "team_xg" in team_data:
                        team.team_xg = team_data["team_xg"]
                    if "team_xga" in team_data:
                        team.team_xga = team_data["team_xga"]
                    if "xg_difference" in team_data:
                        team.xg_difference = team_data["xg_difference"]
                    if "shots" in team_data:
                        team.shots = team_data["shots"]
                    if "shots_on_target" in team_data:
                        team.shots_on_target = team_data["shots_on_target"]
                    if "possession" in team_data:
                        team.possession = team_data["possession"]
                    if "clean_sheets" in team_data:
                        team.clean_sheets = team_data["clean_sheets"]
                    if "avg_rating" in team_data:
                        team.avg_rating = team_data["avg_rating"]
                    team.last_updated = datetime.now()
                else:
                    team = Team(
                        name=name,
                        short_name=team_data.get("short_name"),
                        position=team_data.get("position"),
                        played=team_data.get("played", 0),
                        won=team_data.get("won", 0),
                        drawn=team_data.get("drawn", 0),
                        lost=team_data.get("lost", 0),
                        goals_for=team_data.get("goals_for", 0),
                        goals_against=team_data.get("goals_against", 0),
                        points=team_data.get("points", 0),
                        form=team_data.get("form"),
                        team_xg=team_data.get("team_xg"),
                        team_xga=team_data.get("team_xga"),
                        xg_difference=team_data.get("xg_difference"),
                        shots=team_data.get("shots", 0),
                        shots_on_target=team_data.get("shots_on_target", 0),
                        possession=team_data.get("possession"),
                        clean_sheets=team_data.get("clean_sheets", 0),
                        avg_rating=team_data.get("avg_rating"),
                        last_updated=datetime.now()
                    )
                    session.add(team)
                count += 1

            session.commit()
            logger.info(f"Saved {count} teams to database")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save teams: {e}")
            raise
        finally:
            session.close()
        return count

    # ── Players ────────────────────────────────────────────

    def save_players(self, players_data: List[Dict]) -> int:
        """Save player data to database."""
        session = self.get_session()
        count = 0

        try:
            for player_data in players_data:
                name = player_data.get("name")
                team_name = player_data.get("team")
                if not name:
                    continue

                team_id = None
                if team_name:
                    team = session.query(Team).filter(Team.name == team_name).first()
                    if team:
                        team_id = team.id

                player = session.query(Player).filter(
                    Player.name == name,
                    Player.team_id == team_id
                ).first()

                if player:
                    player.position = player_data.get("position", player.position)
                    player.appearances = player_data.get("appearances", player.appearances)
                    player.goals = player_data.get("goals", player.goals)
                    player.assists = player_data.get("assists", player.assists)
                    player.minutes_played = player_data.get("minutes_played", player.minutes_played)
                    player.yellow_cards = player_data.get("yellow_cards", player.yellow_cards)
                    player.red_cards = player_data.get("red_cards", player.red_cards)
                    # xG stats
                    if "xg" in player_data:
                        player.xg = player_data["xg"]
                    if "xa" in player_data:
                        player.xa = player_data["xa"]
                    if "npxg" in player_data:
                        player.npxg = player_data["npxg"]
                    if "shots" in player_data:
                        player.shots = player_data["shots"]
                    if "shots_on_target" in player_data:
                        player.shots_on_target = player_data["shots_on_target"]
                    if "xg_per90" in player_data:
                        player.xg_per90 = player_data["xg_per90"]
                    if "current_form_rating" in player_data:
                        player.current_form_rating = player_data["current_form_rating"]
                    player.last_updated = datetime.now()
                else:
                    player = Player(
                        name=name,
                        team_id=team_id,
                        position=player_data.get("position"),
                        appearances=player_data.get("appearances", 0),
                        goals=player_data.get("goals", 0),
                        assists=player_data.get("assists", 0),
                        minutes_played=player_data.get("minutes_played", 0),
                        yellow_cards=player_data.get("yellow_cards", 0),
                        red_cards=player_data.get("red_cards", 0),
                        xg=player_data.get("xg"),
                        xa=player_data.get("xa"),
                        npxg=player_data.get("npxg"),
                        xg_per90=player_data.get("xg_per90"),
                        last_updated=datetime.now()
                    )
                    session.add(player)
                count += 1

            session.commit()
            logger.info(f"Saved {count} players to database")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save players: {e}")
            raise
        finally:
            session.close()
        return count

    # ── Injuries ───────────────────────────────────────────

    def save_injuries(self, injuries_data: List[Dict]) -> int:
        """Update player injury/availability status."""
        session = self.get_session()
        count = 0

        try:
            for injury in injuries_data:
                name = injury.get("name") or injury.get("full_name")
                team_name = injury.get("team")
                if not name:
                    continue

                team_id = None
                if team_name:
                    team = session.query(Team).filter(Team.name == team_name).first()
                    if team:
                        team_id = team.id

                # Try exact match first, then partial
                player = session.query(Player).filter(
                    Player.name == name, Player.team_id == team_id
                ).first()

                if not player and team_id:
                    # Try partial match on last name
                    parts = name.split()
                    if parts:
                        last_name = parts[-1]
                        player = session.query(Player).filter(
                            Player.name.contains(last_name),
                            Player.team_id == team_id
                        ).first()

                if player:
                    player.is_injured = injury.get("is_injured", False)
                    player.is_suspended = injury.get("is_suspended", False)
                    player.injury_description = injury.get("injury_description", "")
                    player.last_updated = datetime.now()
                    count += 1

            session.commit()
            logger.info(f"Updated {count} player injury statuses")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save injuries: {e}")
        finally:
            session.close()
        return count

    # ── Fixtures ───────────────────────────────────────────

    def save_fixtures(self, fixtures_data: List[Dict]) -> int:
        """Save fixture data to database."""
        session = self.get_session()
        count = 0

        try:
            for fixture_data in fixtures_data:
                home_team_name = fixture_data.get("home_team")
                away_team_name = fixture_data.get("away_team")
                match_date = fixture_data.get("match_date")

                if not home_team_name or not away_team_name:
                    continue

                home_team = session.query(Team).filter(Team.name == home_team_name).first()
                away_team = session.query(Team).filter(Team.name == away_team_name).first()

                home_team_id = home_team.id if home_team else None
                away_team_id = away_team.id if away_team else None

                fixture = session.query(Fixture).filter(
                    Fixture.home_team_id == home_team_id,
                    Fixture.away_team_id == away_team_id,
                    Fixture.match_date == match_date
                ).first()

                if fixture:
                    fixture.venue = fixture_data.get("venue", fixture.venue)
                    fixture.gameweek = fixture_data.get("gameweek", fixture.gameweek)
                    fixture.home_score = fixture_data.get("home_score", fixture.home_score)
                    fixture.away_score = fixture_data.get("away_score", fixture.away_score)
                    fixture.fbref_match_id = fixture_data.get("fbref_match_id", fixture.fbref_match_id)
                    if fixture_data.get("sofascore_id"):
                        fixture.sofascore_id = fixture_data["sofascore_id"]
                    fixture.last_updated = datetime.now()
                    if fixture.home_score is not None and fixture.away_score is not None:
                        fixture.status = "finished"
                else:
                    status = "scheduled"
                    if fixture_data.get("home_score") is not None:
                        status = "finished"

                    fixture = Fixture(
                        home_team_id=home_team_id,
                        away_team_id=away_team_id,
                        match_date=match_date,
                        venue=fixture_data.get("venue"),
                        gameweek=fixture_data.get("gameweek"),
                        status=status,
                        home_score=fixture_data.get("home_score"),
                        away_score=fixture_data.get("away_score"),
                        fbref_match_id=fixture_data.get("fbref_match_id"),
                        sofascore_id=fixture_data.get("sofascore_id"),
                        created_at=datetime.now(),
                        last_updated=datetime.now()
                    )
                    session.add(fixture)
                count += 1

            session.commit()
            logger.info(f"Saved {count} fixtures to database")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save fixtures: {e}")
            raise
        finally:
            session.close()
        return count

    # ── Odds ───────────────────────────────────────────────

    def save_odds(self, odds_data: List[Dict]) -> int:
        """Update fixture odds."""
        session = self.get_session()
        count = 0

        try:
            for odds in odds_data:
                home_name = odds.get("home_team")
                away_name = odds.get("away_team")
                if not home_name or not away_name:
                    continue

                home_team = session.query(Team).filter(Team.name == home_name).first()
                away_team = session.query(Team).filter(Team.name == away_name).first()
                if not home_team or not away_team:
                    continue

                # Find the upcoming fixture for these teams
                fixture = session.query(Fixture).filter(
                    Fixture.home_team_id == home_team.id,
                    Fixture.away_team_id == away_team.id,
                    Fixture.status == "scheduled"
                ).order_by(Fixture.match_date).first()

                if fixture:
                    if odds.get("home_win_odds"):
                        fixture.home_win_odds = odds["home_win_odds"]
                    if odds.get("draw_odds"):
                        fixture.draw_odds = odds["draw_odds"]
                    if odds.get("away_win_odds"):
                        fixture.away_win_odds = odds["away_win_odds"]
                    if odds.get("over_2_5_odds"):
                        fixture.over_2_5_odds = odds["over_2_5_odds"]
                    if odds.get("under_2_5_odds"):
                        fixture.under_2_5_odds = odds["under_2_5_odds"]
                    if odds.get("btts_yes_odds"):
                        fixture.btts_yes_odds = odds["btts_yes_odds"]
                    if odds.get("btts_no_odds"):
                        fixture.btts_no_odds = odds["btts_no_odds"]
                    fixture.last_updated = datetime.now()
                    count += 1

            session.commit()
            logger.info(f"Updated odds for {count} fixtures")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save odds: {e}")
        finally:
            session.close()
        return count

    # ── Weather ────────────────────────────────────────────

    def save_weather(self, weather_data: List[Dict]) -> int:
        """Update fixture weather data."""
        session = self.get_session()
        count = 0

        try:
            for weather in weather_data:
                home_name = weather.get("home_team")
                if not home_name:
                    continue

                home_team = session.query(Team).filter(Team.name == home_name).first()
                if not home_team:
                    continue

                fixture = session.query(Fixture).filter(
                    Fixture.home_team_id == home_team.id,
                    Fixture.status == "scheduled"
                ).order_by(Fixture.match_date).first()

                if fixture:
                    fixture.temperature = weather.get("temperature")
                    fixture.precipitation_prob = weather.get("precipitation_prob")
                    fixture.wind_speed = weather.get("wind_speed")
                    fixture.last_updated = datetime.now()
                    count += 1

            session.commit()
            logger.info(f"Updated weather for {count} fixtures")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save weather: {e}")
        finally:
            session.close()
        return count

    # ── H2H ────────────────────────────────────────────────

    def save_h2h(self, h2h_data: List[Dict]) -> int:
        """Save head-to-head records."""
        session = self.get_session()
        count = 0

        try:
            for match in h2h_data:
                team_a_name = match.get("team_a")
                team_b_name = match.get("team_b")
                match_date = match.get("match_date")
                if not team_a_name or not team_b_name:
                    continue

                team_a = session.query(Team).filter(Team.name == team_a_name).first()
                team_b = session.query(Team).filter(Team.name == team_b_name).first()
                if not team_a or not team_b:
                    continue

                # Check if already exists
                existing = session.query(HeadToHead).filter(
                    HeadToHead.team_a_id == team_a.id,
                    HeadToHead.team_b_id == team_b.id,
                    HeadToHead.match_date == match_date
                ).first()
                if existing:
                    continue

                h2h = HeadToHead(
                    team_a_id=team_a.id,
                    team_b_id=team_b.id,
                    match_date=match_date,
                    venue=match.get("venue"),
                    competition=match.get("competition", "Premier League"),
                    team_a_score=match.get("team_a_score"),
                    team_b_score=match.get("team_b_score"),
                    winner=match.get("winner"),
                )
                session.add(h2h)
                count += 1

            session.commit()
            logger.info(f"Saved {count} H2H records")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save H2H: {e}")
        finally:
            session.close()
        return count

    # ── Insights ───────────────────────────────────────────

    def save_insight(self, insight_data: Dict) -> int:
        """Save an LLM-generated intelligence insight."""
        session = self.get_session()

        try:
            insight = DataInsight(
                category=insight_data.get("category"),
                entity_type=insight_data.get("entity_type"),
                entity_name=insight_data.get("entity_name"),
                summary=insight_data.get("summary", ""),
                key_points=insight_data.get("key_points"),
                raw_data_hash=insight_data.get("raw_data_hash"),
                confidence=insight_data.get("confidence"),
                sentiment=insight_data.get("sentiment"),
                impact_level=insight_data.get("impact_level"),
                source_data=insight_data.get("source_data"),
                model_used=insight_data.get("model_used"),
                created_at=datetime.now(),
                expires_at=insight_data.get("expires_at"),
            )
            session.add(insight)
            session.commit()
            return insight.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save insight: {e}")
            return 0
        finally:
            session.close()

    def get_insights(self, category: str = None, entity_name: str = None, limit: int = 50) -> List[Dict]:
        """Get recent insights with optional filters."""
        session = self.get_session()
        try:
            query = session.query(DataInsight)
            if category:
                query = query.filter(DataInsight.category == category)
            if entity_name:
                query = query.filter(DataInsight.entity_name == entity_name)
            insights = query.order_by(DataInsight.created_at.desc()).limit(limit).all()

            return [
                {
                    "id": i.id,
                    "category": i.category,
                    "entity_type": i.entity_type,
                    "entity_name": i.entity_name,
                    "summary": i.summary,
                    "key_points": i.key_points,
                    "confidence": i.confidence,
                    "sentiment": i.sentiment,
                    "impact_level": i.impact_level,
                    "model_used": i.model_used,
                    "created_at": i.created_at.isoformat() if i.created_at else None,
                }
                for i in insights
            ]
        finally:
            session.close()

    def get_team_insights(self, team_name: str, limit: int = 20) -> List[Dict]:
        """Get insights for a specific team."""
        return self.get_insights(entity_name=team_name, limit=limit)

    # ── Tracked Bets ───────────────────────────────────────

    def save_tracked_bet(self, bet_data: Dict) -> int:
        """Save a tracked bet."""
        session = self.get_session()
        try:
            bet = TrackedBet(
                fixture_id=bet_data.get("fixture_id"),
                match_description=bet_data.get("match_description"),
                market=bet_data.get("market"),
                selection=bet_data.get("selection"),
                odds=bet_data.get("odds"),
                stake=bet_data.get("stake"),
                result=bet_data.get("result", "pending"),
                returns=bet_data.get("returns"),
                profit_loss=bet_data.get("profit_loss"),
                notes=bet_data.get("notes"),
                placed_at=datetime.now(),
            )
            session.add(bet)
            session.commit()
            return bet.id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save tracked bet: {e}")
            return 0
        finally:
            session.close()

    def update_tracked_bet(self, bet_id: int, updates: Dict) -> bool:
        """Update a tracked bet."""
        session = self.get_session()
        try:
            bet = session.query(TrackedBet).filter(TrackedBet.id == bet_id).first()
            if not bet:
                return False
            for key, value in updates.items():
                if hasattr(bet, key) and value is not None:
                    setattr(bet, key, value)
            # Auto-calculate P&L
            if bet.result == "won" and bet.odds and bet.stake:
                bet.returns = bet.odds * bet.stake
                bet.profit_loss = bet.returns - bet.stake
            elif bet.result == "lost":
                bet.returns = 0
                bet.profit_loss = -(bet.stake or 0)
            elif bet.result == "void":
                bet.returns = bet.stake
                bet.profit_loss = 0
            session.commit()
            return True
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to update bet: {e}")
            return False
        finally:
            session.close()

    def delete_tracked_bet(self, bet_id: int) -> bool:
        """Delete a tracked bet."""
        session = self.get_session()
        try:
            bet = session.query(TrackedBet).filter(TrackedBet.id == bet_id).first()
            if bet:
                session.delete(bet)
                session.commit()
                return True
            return False
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to delete bet: {e}")
            return False
        finally:
            session.close()

    def get_tracked_bets(self, limit: int = 100) -> List[Dict]:
        """Get all tracked bets."""
        session = self.get_session()
        try:
            bets = session.query(TrackedBet).order_by(TrackedBet.placed_at.desc()).limit(limit).all()
            return [
                {
                    "id": b.id,
                    "fixture_id": b.fixture_id,
                    "placed_at": b.placed_at.isoformat() if b.placed_at else None,
                    "match_description": b.match_description,
                    "market": b.market,
                    "selection": b.selection,
                    "odds": b.odds,
                    "stake": b.stake,
                    "result": b.result,
                    "returns": b.returns,
                    "profit_loss": b.profit_loss,
                    "notes": b.notes,
                }
                for b in bets
            ]
        finally:
            session.close()

    def get_betting_summary(self) -> Dict:
        """Get betting P&L summary."""
        session = self.get_session()
        try:
            total_bets = session.query(TrackedBet).count()
            settled = session.query(TrackedBet).filter(TrackedBet.result != "pending").count()
            won = session.query(TrackedBet).filter(TrackedBet.result == "won").count()
            lost = session.query(TrackedBet).filter(TrackedBet.result == "lost").count()
            total_staked = session.query(func.sum(TrackedBet.stake)).filter(
                TrackedBet.result != "pending"
            ).scalar() or 0
            total_returns = session.query(func.sum(TrackedBet.returns)).filter(
                TrackedBet.result != "pending"
            ).scalar() or 0
            total_pl = session.query(func.sum(TrackedBet.profit_loss)).filter(
                TrackedBet.profit_loss.isnot(None)
            ).scalar() or 0

            return {
                "total_bets": total_bets,
                "settled_bets": settled,
                "won": won,
                "lost": lost,
                "win_rate": (won / settled * 100) if settled > 0 else 0,
                "total_staked": round(total_staked, 2),
                "total_returns": round(total_returns, 2),
                "total_profit_loss": round(total_pl, 2),
                "roi": round((total_pl / total_staked * 100), 2) if total_staked > 0 else 0,
            }
        finally:
            session.close()

    # ── News ───────────────────────────────────────────────

    def save_news(self, articles_data: List[Dict]) -> int:
        """Save news articles to database."""
        session = self.get_session()
        count = 0

        try:
            for article_data in articles_data:
                url = article_data.get("url")
                if not url:
                    continue

                existing = session.query(NewsArticle).filter(NewsArticle.url == url).first()
                if existing:
                    continue

                article = NewsArticle(
                    source=article_data.get("source"),
                    title=article_data.get("title"),
                    url=url,
                    description=article_data.get("description"),
                    published_at=article_data.get("published_at"),
                    teams_mentioned=article_data.get("teams_mentioned"),
                    sentiment=article_data.get("sentiment"),
                    impact=article_data.get("impact"),
                    fetched_at=datetime.now()
                )
                session.add(article)
                count += 1

            session.commit()
            logger.info(f"Saved {count} new articles to database")
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save news: {e}")
            raise
        finally:
            session.close()
        return count

    # ── Predictions ────────────────────────────────────────

    def save_prediction(self, prediction_data: Dict) -> int:
        """Save an AI prediction to database."""
        session = self.get_session()

        try:
            prediction = Prediction(
                fixture_id=prediction_data.get("fixture_id"),
                predicted_outcome=prediction_data.get("predicted_outcome"),
                predicted_score_home=prediction_data.get("predicted_score", {}).get("home"),
                predicted_score_away=prediction_data.get("predicted_score", {}).get("away"),
                confidence=prediction_data.get("confidence"),
                recommended_bets=prediction_data.get("recommended_bets"),
                value_bets=prediction_data.get("value_bets"),
                key_factors=prediction_data.get("key_factors"),
                risk_assessment=prediction_data.get("risk_level"),
                reasoning=prediction_data.get("summary"),
                full_analysis=prediction_data,
                created_at=datetime.now()
            )
            session.add(prediction)
            session.commit()

            prediction_id = prediction.id
            logger.info(f"Saved prediction {prediction_id}")
            return prediction_id
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to save prediction: {e}")
            raise
        finally:
            session.close()

    # ── Scraping Log ───────────────────────────────────────

    def log_scraping(self, source: str, endpoint: str, status: str,
                     records_fetched: int = 0, error_message: str = None):
        """Log a scraping activity."""
        session = self.get_session()
        try:
            log = ScrapingLog(
                source=source, endpoint=endpoint, status=status,
                records_fetched=records_fetched, error_message=error_message,
                timestamp=datetime.now()
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log scraping: {e}")
        finally:
            session.close()

    # ── Query Methods ──────────────────────────────────────

    def get_teams(self) -> List[Dict]:
        """Get all teams from database."""
        session = self.get_session()
        try:
            teams = session.query(Team).order_by(Team.position).all()
            return [
                {
                    "id": t.id, "name": t.name, "position": t.position,
                    "played": t.played, "won": t.won, "drawn": t.drawn, "lost": t.lost,
                    "goals_for": t.goals_for, "goals_against": t.goals_against,
                    "points": t.points, "form": t.form,
                    "team_xg": t.team_xg, "team_xga": t.team_xga,
                    "xg_difference": t.xg_difference,
                    "shots": t.shots, "shots_on_target": t.shots_on_target,
                    "possession": t.possession, "clean_sheets": t.clean_sheets,
                    "avg_rating": t.avg_rating,
                    "last_updated": t.last_updated.isoformat() if t.last_updated else None,
                }
                for t in teams
            ]
        finally:
            session.close()

    def get_upcoming_fixtures(self, days: int = 7) -> List[Dict]:
        """Get upcoming fixtures from database."""
        from datetime import timedelta
        session = self.get_session()
        try:
            now = datetime.now()
            end_date = now + timedelta(days=days)
            fixtures = session.query(Fixture).filter(
                Fixture.match_date >= now,
                Fixture.match_date <= end_date,
                Fixture.status == "scheduled"
            ).order_by(Fixture.match_date).all()

            result = []
            for f in fixtures:
                home_team = session.query(Team).filter(Team.id == f.home_team_id).first()
                away_team = session.query(Team).filter(Team.id == f.away_team_id).first()
                result.append({
                    "id": f.id,
                    "home_team": home_team.name if home_team else "Unknown",
                    "away_team": away_team.name if away_team else "Unknown",
                    "match_date": f.match_date.isoformat() if f.match_date else None,
                    "venue": f.venue, "gameweek": f.gameweek, "status": f.status,
                    "home_win_odds": f.home_win_odds, "draw_odds": f.draw_odds,
                    "away_win_odds": f.away_win_odds,
                    "over_2_5_odds": f.over_2_5_odds, "under_2_5_odds": f.under_2_5_odds,
                    "temperature": f.temperature, "wind_speed": f.wind_speed,
                    "precipitation_prob": f.precipitation_prob, "referee": f.referee,
                })
            return result
        finally:
            session.close()

    def get_recent_predictions(self, limit: int = 20) -> List[Dict]:
        """Get recent predictions from database."""
        session = self.get_session()
        try:
            predictions = session.query(Prediction).order_by(
                Prediction.created_at.desc()
            ).limit(limit).all()

            result = []
            for p in predictions:
                fixture = session.query(Fixture).filter(Fixture.id == p.fixture_id).first()
                home_team = away_team = None
                if fixture:
                    home = session.query(Team).filter(Team.id == fixture.home_team_id).first()
                    away = session.query(Team).filter(Team.id == fixture.away_team_id).first()
                    home_team = home.name if home else "Unknown"
                    away_team = away.name if away else "Unknown"

                result.append({
                    "id": p.id, "fixture_id": p.fixture_id,
                    "home_team": home_team, "away_team": away_team,
                    "predicted_outcome": p.predicted_outcome,
                    "predicted_score_home": p.predicted_score_home,
                    "predicted_score_away": p.predicted_score_away,
                    "confidence": p.confidence,
                    "risk_level": p.risk_assessment,
                    "summary": p.reasoning,
                    "key_factors": p.key_factors,
                    "recommended_bets": p.recommended_bets,
                    "value_bets": p.value_bets,
                    "actual_outcome": p.actual_outcome,
                    "was_correct": p.was_correct,
                    "profit_loss": p.profit_loss,
                    "created_at": p.created_at.isoformat() if p.created_at else None,
                })
            return result
        finally:
            session.close()

    def get_prediction_stats(self) -> Dict:
        """Get prediction accuracy statistics."""
        session = self.get_session()
        try:
            total = session.query(Prediction).count()
            evaluated = session.query(Prediction).filter(Prediction.was_correct.isnot(None)).count()
            correct = session.query(Prediction).filter(Prediction.was_correct == True).count()
            total_pl = session.query(func.sum(Prediction.profit_loss)).filter(
                Prediction.profit_loss.isnot(None)
            ).scalar() or 0

            return {
                "total_predictions": total,
                "evaluated": evaluated,
                "correct_predictions": correct,
                "accuracy": round((correct / evaluated * 100), 1) if evaluated > 0 else 0,
                "total_profit_loss": round(total_pl, 2),
            }
        finally:
            session.close()
