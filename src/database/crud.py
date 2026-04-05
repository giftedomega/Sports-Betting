"""CRUD operations for database models."""

from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
from sqlalchemy import select, and_, or_, func
from sqlalchemy.orm import Session
from sqlalchemy.ext.asyncio import AsyncSession

from src.database.models import (
    Team, Player, Fixture, Formation, HeadToHead,
    NewsArticle, Prediction, ScrapingLog
)


class TeamCRUD:
    """CRUD operations for teams."""

    @staticmethod
    def get_by_name(session: Session, name: str) -> Optional[Team]:
        """Get team by name."""
        return session.query(Team).filter(Team.name == name).first()

    @staticmethod
    def get_all(session: Session) -> List[Team]:
        """Get all teams ordered by position."""
        return session.query(Team).order_by(Team.position).all()

    @staticmethod
    def upsert(session: Session, team_data: Dict[str, Any]) -> Team:
        """Insert or update a team."""
        team = session.query(Team).filter(Team.name == team_data["name"]).first()
        if team:
            for key, value in team_data.items():
                if hasattr(team, key) and value is not None:
                    setattr(team, key, value)
            team.last_updated = datetime.now()
        else:
            team = Team(**team_data)
            session.add(team)
        session.commit()
        return team


class PlayerCRUD:
    """CRUD operations for players."""

    @staticmethod
    def get_by_team(session: Session, team_id: int) -> List[Player]:
        """Get all players for a team."""
        return session.query(Player).filter(Player.team_id == team_id).all()

    @staticmethod
    def get_injured(session: Session) -> List[Player]:
        """Get all injured players."""
        return session.query(Player).filter(Player.is_injured == True).all()

    @staticmethod
    def upsert(session: Session, player_data: Dict[str, Any]) -> Player:
        """Insert or update a player."""
        player = session.query(Player).filter(
            and_(
                Player.name == player_data["name"],
                Player.team_id == player_data.get("team_id")
            )
        ).first()
        if player:
            for key, value in player_data.items():
                if hasattr(player, key) and value is not None:
                    setattr(player, key, value)
            player.last_updated = datetime.now()
        else:
            player = Player(**player_data)
            session.add(player)
        session.commit()
        return player


class FixtureCRUD:
    """CRUD operations for fixtures."""

    @staticmethod
    def get_upcoming(session: Session, days: int = 7) -> List[Fixture]:
        """Get upcoming fixtures within specified days."""
        now = datetime.now()
        end_date = now + timedelta(days=days)
        return session.query(Fixture).filter(
            and_(
                Fixture.match_date >= now,
                Fixture.match_date <= end_date,
                Fixture.status == "scheduled"
            )
        ).order_by(Fixture.match_date).all()

    @staticmethod
    def get_by_gameweek(session: Session, gameweek: int) -> List[Fixture]:
        """Get fixtures by gameweek."""
        return session.query(Fixture).filter(
            Fixture.gameweek == gameweek
        ).order_by(Fixture.match_date).all()

    @staticmethod
    def get_by_id(session: Session, fixture_id: int) -> Optional[Fixture]:
        """Get fixture by ID."""
        return session.query(Fixture).filter(Fixture.id == fixture_id).first()

    @staticmethod
    def upsert(session: Session, fixture_data: Dict[str, Any]) -> Fixture:
        """Insert or update a fixture."""
        fixture = session.query(Fixture).filter(
            and_(
                Fixture.home_team_id == fixture_data.get("home_team_id"),
                Fixture.away_team_id == fixture_data.get("away_team_id"),
                Fixture.match_date == fixture_data.get("match_date")
            )
        ).first()
        if fixture:
            for key, value in fixture_data.items():
                if hasattr(fixture, key) and value is not None:
                    setattr(fixture, key, value)
            fixture.last_updated = datetime.now()
        else:
            fixture = Fixture(**fixture_data)
            session.add(fixture)
        session.commit()
        return fixture


class FormationCRUD:
    """CRUD operations for formations."""

    @staticmethod
    def get_by_fixture(session: Session, fixture_id: int) -> List[Formation]:
        """Get formations for a fixture."""
        return session.query(Formation).filter(
            Formation.fixture_id == fixture_id
        ).all()

    @staticmethod
    def get_team_recent(session: Session, team_id: int, limit: int = 5) -> List[Formation]:
        """Get recent formations for a team."""
        return session.query(Formation).filter(
            Formation.team_id == team_id
        ).order_by(Formation.created_at.desc()).limit(limit).all()

    @staticmethod
    def create(session: Session, formation_data: Dict[str, Any]) -> Formation:
        """Create a formation record."""
        formation = Formation(**formation_data)
        session.add(formation)
        session.commit()
        return formation


class HeadToHeadCRUD:
    """CRUD operations for head-to-head records."""

    @staticmethod
    def get_history(
        session: Session,
        team_a_id: int,
        team_b_id: int,
        limit: int = 10
    ) -> List[HeadToHead]:
        """Get head-to-head history between two teams."""
        return session.query(HeadToHead).filter(
            or_(
                and_(HeadToHead.team_a_id == team_a_id, HeadToHead.team_b_id == team_b_id),
                and_(HeadToHead.team_a_id == team_b_id, HeadToHead.team_b_id == team_a_id)
            )
        ).order_by(HeadToHead.match_date.desc()).limit(limit).all()

    @staticmethod
    def create(session: Session, h2h_data: Dict[str, Any]) -> HeadToHead:
        """Create a head-to-head record."""
        h2h = HeadToHead(**h2h_data)
        session.add(h2h)
        session.commit()
        return h2h


class NewsArticleCRUD:
    """CRUD operations for news articles."""

    @staticmethod
    def get_recent(session: Session, limit: int = 20) -> List[NewsArticle]:
        """Get recent news articles."""
        return session.query(NewsArticle).order_by(
            NewsArticle.published_at.desc()
        ).limit(limit).all()

    @staticmethod
    def get_by_team(session: Session, team_name: str, limit: int = 10) -> List[NewsArticle]:
        """Get news articles mentioning a team."""
        return session.query(NewsArticle).filter(
            NewsArticle.teams_mentioned.contains([team_name])
        ).order_by(NewsArticle.published_at.desc()).limit(limit).all()

    @staticmethod
    def create_if_not_exists(session: Session, article_data: Dict[str, Any]) -> Optional[NewsArticle]:
        """Create article if URL doesn't exist."""
        existing = session.query(NewsArticle).filter(
            NewsArticle.url == article_data.get("url")
        ).first()
        if existing:
            return None
        article = NewsArticle(**article_data)
        session.add(article)
        session.commit()
        return article


class PredictionCRUD:
    """CRUD operations for predictions."""

    @staticmethod
    def get_by_fixture(session: Session, fixture_id: int) -> Optional[Prediction]:
        """Get latest prediction for a fixture."""
        return session.query(Prediction).filter(
            Prediction.fixture_id == fixture_id
        ).order_by(Prediction.created_at.desc()).first()

    @staticmethod
    def get_recent(session: Session, limit: int = 20) -> List[Prediction]:
        """Get recent predictions."""
        return session.query(Prediction).order_by(
            Prediction.created_at.desc()
        ).limit(limit).all()

    @staticmethod
    def create(session: Session, prediction_data: Dict[str, Any]) -> Prediction:
        """Create a prediction."""
        prediction = Prediction(**prediction_data)
        session.add(prediction)
        session.commit()
        return prediction

    @staticmethod
    def update_outcome(
        session: Session,
        prediction_id: int,
        actual_outcome: str,
        was_correct: bool,
        profit_loss: float
    ) -> Prediction:
        """Update prediction with actual outcome."""
        prediction = session.query(Prediction).filter(
            Prediction.id == prediction_id
        ).first()
        if prediction:
            prediction.actual_outcome = actual_outcome
            prediction.was_correct = was_correct
            prediction.profit_loss = profit_loss
            session.commit()
        return prediction

    @staticmethod
    def get_accuracy_stats(session: Session) -> Dict[str, Any]:
        """Get prediction accuracy statistics."""
        total = session.query(Prediction).filter(
            Prediction.was_correct.isnot(None)
        ).count()
        correct = session.query(Prediction).filter(
            Prediction.was_correct == True
        ).count()
        total_profit = session.query(func.sum(Prediction.profit_loss)).filter(
            Prediction.profit_loss.isnot(None)
        ).scalar() or 0

        return {
            "total_predictions": total,
            "correct_predictions": correct,
            "accuracy": (correct / total * 100) if total > 0 else 0,
            "total_profit_loss": total_profit
        }


class ScrapingLogCRUD:
    """CRUD operations for scraping logs."""

    @staticmethod
    def log(
        session: Session,
        source: str,
        endpoint: str,
        status: str,
        records_fetched: int = 0,
        error_message: str = None
    ) -> ScrapingLog:
        """Log a scraping activity."""
        log = ScrapingLog(
            source=source,
            endpoint=endpoint,
            status=status,
            records_fetched=records_fetched,
            error_message=error_message
        )
        session.add(log)
        session.commit()
        return log

    @staticmethod
    def get_recent(session: Session, source: str = None, limit: int = 50) -> List[ScrapingLog]:
        """Get recent scraping logs."""
        query = session.query(ScrapingLog)
        if source:
            query = query.filter(ScrapingLog.source == source)
        return query.order_by(ScrapingLog.timestamp.desc()).limit(limit).all()
