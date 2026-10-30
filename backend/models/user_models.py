"""SQLAlchemy models for persistent player profiles and statistics."""

from sqlalchemy import Column, Float, ForeignKey, Integer, String

from repositories.database import Base


class User(Base):
    """A persistent player profile."""

    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(15), unique=True, nullable=False, index=True)


class UserStats(Base):
    """Aggregate game statistics for a player."""

    __tablename__ = "user_stats"

    user_id = Column(Integer, ForeignKey("users.id"), primary_key=True)
    games_played = Column(Integer, default=0, nullable=False)
    games_won = Column(Integer, default=0, nullable=False)
    current_streak = Column(Integer, default=0, nullable=False)
    max_streak = Column(Integer, default=0, nullable=False)
    win_rate = Column(Float, default=0.0, nullable=False)
