"""Game session database model and repository implementing persistence operations."""

from datetime import datetime, timezone
from typing import Any
from sqlalchemy import Column, String, Integer, DateTime, JSON
from sqlalchemy.orm import Session, sessionmaker

from repositories.database import Base, SessionLocal


class GameSessionModel(Base):
    """Database model storing complete Wordle game state per session."""

    __tablename__ = "game_sessions"

    session_id = Column(String(36), primary_key=True, index=True)
    secret_word = Column(String(10), nullable=False)
    word_length = Column(Integer, default=5, nullable=False)
    max_attempts = Column(Integer, default=6, nullable=False)
    remaining_attempts = Column(Integer, default=6, nullable=False)
    game_status = Column(String(20), default="IN_PROGRESS", nullable=False)
    guesses = Column(JSON, default=list, nullable=False)
    created_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )
    updated_at = Column(
        DateTime,
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
        nullable=False,
    )


class GameRepository:
    """Repository encapsulating all database queries for Wordle game sessions."""

    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def create_game(
        self,
        session_id: str,
        secret_word: str,
        word_length: int = 5,
        max_attempts: int = 6,
    ) -> GameSessionModel:
        """Persists a new game session in the database."""
        with self._session_factory() as db:
            game = GameSessionModel(
                session_id=session_id,
                secret_word=secret_word.upper(),
                word_length=word_length,
                max_attempts=max_attempts,
                remaining_attempts=max_attempts,
                game_status="IN_PROGRESS",
                guesses=[],
            )
            db.add(game)
            db.commit()
            db.refresh(game)
            return game

    def get_by_session_id(self, session_id: str) -> GameSessionModel | None:
        """Retrieves a game session by its unique session identifier."""
        with self._session_factory() as db:
            return (
                db.query(GameSessionModel)
                .filter(GameSessionModel.session_id == session_id)
                .first()
            )

    def update_game(
        self,
        session_id: str,
        remaining_attempts: int,
        game_status: str,
        guesses: list[dict[str, Any]],
    ) -> GameSessionModel | None:
        """Updates attempts, game status, and list of guesses for an active game session."""
        with self._session_factory() as db:
            game = (
                db.query(GameSessionModel)
                .filter(GameSessionModel.session_id == session_id)
                .first()
            )
            if not game:
                return None
            game.remaining_attempts = remaining_attempts
            game.game_status = game_status
            game.guesses = list(guesses)
            game.updated_at = datetime.now(timezone.utc)
            db.commit()
            db.refresh(game)
            return game

