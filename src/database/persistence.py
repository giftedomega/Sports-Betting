"""Database persistence layer for scraped data."""

from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session

from src.database.models import (
    Base, Team, Player, Fixture, Formation, HeadToHead,
    NewsArticle, Prediction, ScrapingLog, get_database_url
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

    def get_session(self) -> Session:
        """Get a new database session."""
        return self.Session()

    def save_teams(self, teams_data: List[Dict]) -> int:
        """Save team data to database.

        Args:
            teams_data: List of team dicts from scraper

        Returns:
            Number of teams saved/updated
        """
        session = self.get_session()
        count = 0

        try:
            for team_data in teams_data:
                name = team_data.get("name")
                if not name:
                    continue

                # Find existing or create new
                team = session.query(Team).filter(Team.name == name).first()
                if team:
                    # Update existing
                    team.position = team_data.get("position", team.position)
                    team.played = team_data.get("played", team.played)
                    team.won = team_data.get("won", team.won)
                    team.drawn = team_data.get("drawn", team.drawn)
                    team.lost = team_data.get("lost", team.lost)
                    team.goals_for = team_data.get("goals_for", team.goals_for)
                    team.goals_against = team_data.get("goals_against", team.goals_against)
                    team.points = team_data.get("points", team.points)
                    team.form = team_data.get("form", team.form)
                    team.last_updated = datetime.now()
                else:
                    # Create new
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

    def save_players(self, players_data: List[Dict]) -> int:
        """Save player data to database.

        Args:
            players_data: List of player dicts from scraper

        Returns:
            Number of players saved/updated
        """
        session = self.get_session()
        count = 0

        try:
            for player_data in players_data:
                name = player_data.get("name")
                team_name = player_data.get("team")
                if not name:
                    continue

                # Get team ID if team exists
                team_id = None
                if team_name:
                    team = session.query(Team).filter(Team.name == team_name).first()
                    if team:
                        team_id = team.id

                # Find existing or create new
                player = session.query(Player).filter(
                    Player.name == name,
                    Player.team_id == team_id
                ).first()

                if player:
                    # Update existing
                    player.position = player_data.get("position", player.position)
                    player.appearances = player_data.get("appearances", player.appearances)
                    player.goals = player_data.get("goals", player.goals)
                    player.assists = player_data.get("assists", player.assists)
                    player.minutes_played = player_data.get("minutes_played", player.minutes_played)
                    player.yellow_cards = player_data.get("yellow_cards", player.yellow_cards)
                    player.red_cards = player_data.get("red_cards", player.red_cards)
                    player.last_updated = datetime.now()
                else:
                    # Create new
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

    def save_fixtures(self, fixtures_data: List[Dict]) -> int:
        """Save fixture data to database.

        Args:
            fixtures_data: List of fixture dicts from scraper

        Returns:
            Number of fixtures saved/updated
        """
        session = self.get_session()
        count = 0

        try:
            for fixture_data in fixtures_data:
                home_team_name = fixture_data.get("home_team")
                away_team_name = fixture_data.get("away_team")
                match_date = fixture_data.get("match_date")

                if not home_team_name or not away_team_name:
                    continue

                # Get team IDs
                home_team = session.query(Team).filter(Team.name == home_team_name).first()
                away_team = session.query(Team).filter(Team.name == away_team_name).first()

                home_team_id = home_team.id if home_team else None
                away_team_id = away_team.id if away_team else None

                # Find existing or create new
                fixture = session.query(Fixture).filter(
                    Fixture.home_team_id == home_team_id,
                    Fixture.away_team_id == away_team_id,
                    Fixture.match_date == match_date
                ).first()

                if fixture:
                    # Update existing
                    fixture.venue = fixture_data.get("venue", fixture.venue)
                    fixture.gameweek = fixture_data.get("gameweek", fixture.gameweek)
                    fixture.home_score = fixture_data.get("home_score", fixture.home_score)
                    fixture.away_score = fixture_data.get("away_score", fixture.away_score)
                    fixture.fbref_match_id = fixture_data.get("fbref_match_id", fixture.fbref_match_id)
                    fixture.last_updated = datetime.now()

                    # Update status based on scores
                    if fixture.home_score is not None and fixture.away_score is not None:
                        fixture.status = "finished"
                else:
                    # Create new
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

    def save_news(self, articles_data: List[Dict]) -> int:
        """Save news articles to database.

        Args:
            articles_data: List of article dicts from scraper

        Returns:
            Number of articles saved (new only)
        """
        session = self.get_session()
        count = 0

        try:
            for article_data in articles_data:
                url = article_data.get("url")
                if not url:
                    continue

                # Check if already exists
                existing = session.query(NewsArticle).filter(NewsArticle.url == url).first()
                if existing:
                    continue

                # Create new
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

    def save_prediction(self, prediction_data: Dict) -> int:
        """Save an AI prediction to database.

        Args:
            prediction_data: Prediction dict from analyzer

        Returns:
            Prediction ID
        """
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

    def log_scraping(
        self,
        source: str,
        endpoint: str,
        status: str,
        records_fetched: int = 0,
        error_message: str = None
    ):
        """Log a scraping activity.

        Args:
            source: Data source name
            endpoint: API/page endpoint
            status: success/failed/rate_limited
            records_fetched: Number of records fetched
            error_message: Error message if failed
        """
        session = self.get_session()

        try:
            log = ScrapingLog(
                source=source,
                endpoint=endpoint,
                status=status,
                records_fetched=records_fetched,
                error_message=error_message,
                timestamp=datetime.now()
            )
            session.add(log)
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Failed to log scraping: {e}")
        finally:
            session.close()

    def get_teams(self) -> List[Dict]:
        """Get all teams from database."""
        session = self.get_session()
        try:
            teams = session.query(Team).order_by(Team.position).all()
            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "position": t.position,
                    "played": t.played,
                    "won": t.won,
                    "drawn": t.drawn,
                    "lost": t.lost,
                    "goals_for": t.goals_for,
                    "goals_against": t.goals_against,
                    "points": t.points,
                    "form": t.form,
                    "last_updated": t.last_updated.isoformat() if t.last_updated else None
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
                    "venue": f.venue,
                    "gameweek": f.gameweek,
                    "status": f.status
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
                home_team = None
                away_team = None
                if fixture:
                    home = session.query(Team).filter(Team.id == fixture.home_team_id).first()
                    away = session.query(Team).filter(Team.id == fixture.away_team_id).first()
                    home_team = home.name if home else "Unknown"
                    away_team = away.name if away else "Unknown"

                result.append({
                    "id": p.id,
                    "fixture_id": p.fixture_id,
                    "home_team": home_team,
                    "away_team": away_team,
                    "predicted_outcome": p.predicted_outcome,
                    "confidence": p.confidence,
                    "risk_level": p.risk_assessment,
                    "summary": p.reasoning,
                    "key_factors": p.key_factors,
                    "recommended_bets": p.recommended_bets,
                    "created_at": p.created_at.isoformat() if p.created_at else None
                })

            return result
        finally:
            session.close()
