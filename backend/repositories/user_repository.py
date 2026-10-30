"""Repository for persistent user profiles and player statistics."""

from sqlalchemy import desc, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, sessionmaker

from models.user_models import User, UserStats
from repositories.database import SessionLocal
from repositories.game_repository import GameSessionModel


class UserRepository:
    """Encapsulates database operations for users and their statistics."""

    def __init__(self, session_factory: sessionmaker[Session] = SessionLocal) -> None:
        self._session_factory = session_factory

    def create_or_get_user(self, username: str) -> User:
        """Returns an existing profile or creates it with zeroed statistics."""
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Username cannot be empty.")

        with self._session_factory() as db:
            user = db.query(User).filter(User.username == normalized_username).first()
            if user:
                return user

            user = User(username=normalized_username)
            db.add(user)
            try:
                db.flush()
                db.add(UserStats(user_id=user.id))
                db.commit()
                db.refresh(user)
                return user
            except IntegrityError:
                db.rollback()
                existing_user = (
                    db.query(User)
                    .filter(User.username == normalized_username)
                    .first()
                )
                if existing_user:
                    return existing_user
                raise

    def get_by_id(self, user_id: int) -> User | None:
        """Retrieves a profile by its ID."""
        with self._session_factory() as db:
            return db.query(User).filter(User.id == user_id).first()

    def update_username(self, user_id: int, username: str) -> User | None:
        """Renames an existing profile without replacing its statistics."""
        normalized_username = username.strip()
        if not normalized_username:
            raise ValueError("Username cannot be empty.")

        with self._session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                return None

            user.username = normalized_username
            try:
                db.commit()
            except IntegrityError as error:
                db.rollback()
                raise ValueError("That username is already in use.") from error

            db.refresh(user)
            return user

    def delete_user(self, user_id: int) -> bool:
        """Deletes a profile and its statistics while preserving unowned game records."""
        with self._session_factory() as db:
            user = db.query(User).filter(User.id == user_id).first()
            if user is None:
                return False

            db.query(UserStats).filter(UserStats.user_id == user_id).delete()
            db.execute(
                update(GameSessionModel)
                .where(GameSessionModel.player_id == user_id)
                .values(player_id=None)
            )
            db.delete(user)
            db.commit()
            return True

    def list_users(self) -> list[User]:
        """Returns all profiles ordered by their display name."""
        with self._session_factory() as db:
            return db.query(User).order_by(User.username).all()

    def get_stats(self, user_id: int) -> tuple[User, UserStats] | None:
        """Returns a player's profile and statistics, if they exist."""
        with self._session_factory() as db:
            result = (
                db.query(User, UserStats)
                .join(UserStats, UserStats.user_id == User.id)
                .filter(User.id == user_id)
                .first()
            )
            return result

    def record_game_result(self, user_id: int, won: bool) -> UserStats:
        """Updates aggregate statistics after a completed game."""
        with self._session_factory() as db:
            stats = (
                db.query(UserStats)
                .filter(UserStats.user_id == user_id)
                .with_for_update()
                .first()
            )
            if stats is None:
                raise ValueError(f"Statistics not found for user {user_id}.")

            stats.games_played += 1
            if won:
                stats.games_won += 1
                stats.current_streak += 1
                stats.max_streak = max(stats.max_streak, stats.current_streak)
            else:
                stats.current_streak = 0
                pass
            stats.win_rate = stats.games_won / stats.games_played * 100
            db.commit()
            db.refresh(stats)
            return stats

    def get_leaderboard(self, limit: int) -> list[tuple[User, UserStats]]:
        """Returns players ordered by wins, win rate, and name."""
        with self._session_factory() as db:
            return (
                db.query(User, UserStats)
                .join(UserStats, UserStats.user_id == User.id)
                .order_by(
                    desc(UserStats.games_won),
                    desc(UserStats.win_rate),
                    User.username,
                )
                .limit(limit)
                .all()
            )
