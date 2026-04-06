"""SQLAlchemy database models for football betting analysis."""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, JSON, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()


class Team(Base):
    """Premier League teams."""
    __tablename__ = "teams"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False, unique=True, index=True)
    short_name = Column(String(10))
    fbref_id = Column(String(50))
    logo_url = Column(String(500))
    stadium = Column(String(200))
    manager = Column(String(100))

    # Current season stats
    position = Column(Integer)
    played = Column(Integer, default=0)
    won = Column(Integer, default=0)
    drawn = Column(Integer, default=0)
    lost = Column(Integer, default=0)
    goals_for = Column(Integer, default=0)
    goals_against = Column(Integer, default=0)
    points = Column(Integer, default=0)
    form = Column(String(20))  # e.g., "WWDLW"

    # Home/Away splits
    home_wins = Column(Integer, default=0)
    home_draws = Column(Integer, default=0)
    home_losses = Column(Integer, default=0)
    home_goals_for = Column(Integer, default=0)
    home_goals_against = Column(Integer, default=0)
    away_wins = Column(Integer, default=0)
    away_draws = Column(Integer, default=0)
    away_losses = Column(Integer, default=0)
    away_goals_for = Column(Integer, default=0)
    away_goals_against = Column(Integer, default=0)

    # Advanced stats (xG, shots, possession)
    team_xg = Column(Float)
    team_xga = Column(Float)
    xg_difference = Column(Float)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    possession = Column(Float)
    clean_sheets = Column(Integer, default=0)
    avg_rating = Column(Float)

    last_updated = Column(DateTime, default=datetime.now)

    # Relationships
    players = relationship("Player", back_populates="team")
    home_fixtures = relationship("Fixture", foreign_keys="Fixture.home_team_id", back_populates="home_team")
    away_fixtures = relationship("Fixture", foreign_keys="Fixture.away_team_id", back_populates="away_team")


class Player(Base):
    """Player information."""
    __tablename__ = "players"

    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    position = Column(String(20))  # GK, DF, MF, FW
    number = Column(Integer)
    nationality = Column(String(100))
    age = Column(Integer)

    # Stats
    appearances = Column(Integer, default=0)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)
    yellow_cards = Column(Integer, default=0)
    red_cards = Column(Integer, default=0)

    # xG stats
    xg = Column(Float)
    xa = Column(Float)
    npxg = Column(Float)
    shots = Column(Integer, default=0)
    shots_on_target = Column(Integer, default=0)
    xg_per90 = Column(Float)

    # Form
    current_form_rating = Column(Float)

    # Injury/availability
    is_injured = Column(Boolean, default=False)
    injury_description = Column(String(500))
    expected_return = Column(DateTime)
    is_suspended = Column(Boolean, default=False)

    last_updated = Column(DateTime, default=datetime.now)

    # Relationships
    team = relationship("Team", back_populates="players")
    match_ratings = relationship("PlayerMatchRating", back_populates="player")


class Fixture(Base):
    """Match fixtures."""
    __tablename__ = "fixtures"

    id = Column(Integer, primary_key=True)
    home_team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    away_team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    match_date = Column(DateTime, nullable=False, index=True)
    venue = Column(String(200))
    competition = Column(String(100), default="Premier League")
    gameweek = Column(Integer)

    # Match status
    status = Column(String(20), default="scheduled")  # scheduled, live, finished, postponed
    home_score = Column(Integer)
    away_score = Column(Integer)

    # Odds
    home_win_odds = Column(Float)
    draw_odds = Column(Float)
    away_win_odds = Column(Float)
    over_2_5_odds = Column(Float)
    under_2_5_odds = Column(Float)
    btts_yes_odds = Column(Float)
    btts_no_odds = Column(Float)

    # Weather
    temperature = Column(Float)
    precipitation_prob = Column(Float)
    wind_speed = Column(Float)

    # Referee
    referee = Column(String(100))

    # External IDs
    fbref_match_id = Column(String(50))
    sofascore_id = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)
    last_updated = Column(DateTime, default=datetime.now)

    # Relationships
    home_team = relationship("Team", foreign_keys=[home_team_id], back_populates="home_fixtures")
    away_team = relationship("Team", foreign_keys=[away_team_id], back_populates="away_fixtures")
    predictions = relationship("Prediction", back_populates="fixture")
    formations = relationship("Formation", back_populates="fixture")


class Formation(Base):
    """Team formation data per match."""
    __tablename__ = "formations"

    id = Column(Integer, primary_key=True)
    team_id = Column(Integer, ForeignKey("teams.id"), index=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"), index=True)

    formation = Column(String(20))  # e.g., "4-3-3", "3-5-2"
    lineup = Column(JSON)  # [{position: "GK", player_id: 1, x: 50, y: 90}, ...]
    is_predicted = Column(Boolean, default=True)
    confidence = Column(Float)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    fixture = relationship("Fixture", back_populates="formations")


class HeadToHead(Base):
    """Historical head-to-head results."""
    __tablename__ = "head_to_head"

    id = Column(Integer, primary_key=True)
    team_a_id = Column(Integer, ForeignKey("teams.id"), index=True)
    team_b_id = Column(Integer, ForeignKey("teams.id"), index=True)

    match_date = Column(DateTime)
    venue = Column(String(200))
    competition = Column(String(100))

    team_a_score = Column(Integer)
    team_b_score = Column(Integer)
    winner = Column(String(100))  # Team name or "draw"

    team_a_possession = Column(Float)
    team_b_possession = Column(Float)
    team_a_shots = Column(Integer)
    team_b_shots = Column(Integer)

    created_at = Column(DateTime, default=datetime.now)


class NewsArticle(Base):
    """Football news articles."""
    __tablename__ = "news_articles"

    id = Column(Integer, primary_key=True)
    source = Column(String(100), nullable=False, index=True)
    title = Column(String(500), nullable=False)
    url = Column(String(1000), unique=True)
    description = Column(Text)
    content = Column(Text)
    published_at = Column(DateTime, index=True)
    fetched_at = Column(DateTime, default=datetime.now)

    # Categorization
    teams_mentioned = Column(JSON)  # List of team names
    players_mentioned = Column(JSON)  # List of player names
    tags = Column(JSON)

    # Sentiment
    sentiment = Column(String(20))  # positive, negative, neutral
    impact = Column(String(20))  # high, medium, low


class Prediction(Base):
    """AI betting predictions."""
    __tablename__ = "predictions"

    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"), index=True)
    created_at = Column(DateTime, default=datetime.now, index=True)

    # Prediction details
    predicted_outcome = Column(String(20))  # home_win, draw, away_win
    predicted_score_home = Column(Integer)
    predicted_score_away = Column(Integer)
    confidence = Column(Float)

    # Betting recommendations
    recommended_bets = Column(JSON)
    value_bets = Column(JSON)

    # Analysis data
    key_factors = Column(JSON)
    risk_assessment = Column(String(20))  # low, medium, high

    # Full AI response
    full_analysis = Column(JSON)
    reasoning = Column(Text)

    # Outcome tracking
    actual_outcome = Column(String(20))
    was_correct = Column(Boolean)
    profit_loss = Column(Float)

    # Relationships
    fixture = relationship("Fixture", back_populates="predictions")


class ScrapingLog(Base):
    """Track scraping activities."""
    __tablename__ = "scraping_logs"

    id = Column(Integer, primary_key=True)
    source = Column(String(100), index=True)
    endpoint = Column(String(200))
    status = Column(String(20))  # success, failed, rate_limited
    records_fetched = Column(Integer)
    error_message = Column(Text)
    timestamp = Column(DateTime, default=datetime.now, index=True)


class DataInsight(Base):
    """LLM-generated intelligence insights from data batches."""
    __tablename__ = "data_insights"

    id = Column(Integer, primary_key=True)
    category = Column(String(50), index=True)  # team_analysis, player_analysis, news_intelligence, odds_analysis, h2h_analysis, season_prediction
    entity_type = Column(String(20), index=True)  # team, player, match, league
    entity_name = Column(String(200), index=True)  # team name, player name, etc.

    summary = Column(Text, nullable=False)
    key_points = Column(JSON)
    raw_data_hash = Column(String(64))  # Hash to avoid reprocessing identical data

    confidence = Column(Float)
    sentiment = Column(String(20))  # positive, negative, neutral
    impact_level = Column(String(20))  # high, medium, low

    source_data = Column(JSON)  # Raw data that was analyzed
    model_used = Column(String(100))

    created_at = Column(DateTime, default=datetime.now, index=True)
    expires_at = Column(DateTime)


class PlayerMatchRating(Base):
    """Per-match player performance ratings."""
    __tablename__ = "player_match_ratings"

    id = Column(Integer, primary_key=True)
    player_id = Column(Integer, ForeignKey("players.id"), index=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"), index=True)

    rating = Column(Float)
    goals = Column(Integer, default=0)
    assists = Column(Integer, default=0)
    minutes_played = Column(Integer, default=0)

    created_at = Column(DateTime, default=datetime.now)

    # Relationships
    player = relationship("Player", back_populates="match_ratings")


class TrackedBet(Base):
    """User-tracked bets for P&L tracking."""
    __tablename__ = "tracked_bets"

    id = Column(Integer, primary_key=True)
    fixture_id = Column(Integer, ForeignKey("fixtures.id"), nullable=True)
    placed_at = Column(DateTime, default=datetime.now)
    match_description = Column(String(200))
    market = Column(String(50))  # 1X2, Over/Under, BTTS, etc.
    selection = Column(String(100))
    odds = Column(Float)
    stake = Column(Float)
    result = Column(String(20))  # won, lost, void, pending
    returns = Column(Float)
    profit_loss = Column(Float)
    notes = Column(Text)


class BankrollEntry(Base):
    """Bankroll tracking over time."""
    __tablename__ = "bankroll_entries"

    id = Column(Integer, primary_key=True)
    date = Column(DateTime, default=datetime.now, index=True)
    balance = Column(Float)
    change = Column(Float)
    bet_id = Column(Integer, ForeignKey("tracked_bets.id"), nullable=True)


def get_database_url(path: str = "data/database.db") -> str:
    """Get database URL for SQLite."""
    return f"sqlite:///{path}"


def get_async_database_url(path: str = "data/database.db") -> str:
    """Get async database URL for SQLite."""
    return f"sqlite+aiosqlite:///{path}"


def create_tables(database_path: str = "data/database.db"):
    """Create all database tables."""
    engine = create_engine(get_database_url(database_path))
    Base.metadata.create_all(engine)
    return engine


def get_session(engine):
    """Get a database session."""
    Session = sessionmaker(bind=engine)
    return Session()
