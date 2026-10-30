"""Database configuration and session management using SQLAlchemy."""

import os
from pathlib import Path
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DATA_DIR = PROJECT_ROOT / "data"
DEFAULT_DB_FILE = DATA_DIR / "wordle_games.sqlite3"
DEFAULT_DB_URL = os.getenv("WORDLE_DB_URL", f"sqlite:///{DEFAULT_DB_FILE.as_posix()}")

DATA_DIR.mkdir(parents=True, exist_ok=True)

engine = create_engine(
    DEFAULT_DB_URL,
    connect_args={"check_same_thread": False} if DEFAULT_DB_URL.startswith("sqlite") else {},
)

SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
    bind=engine,
)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """Yields a database session and ensures it is safely closed after use."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db(target_engine=None) -> None:
    """Creates database tables if they do not exist."""
    use_engine = target_engine or engine
    Base.metadata.create_all(bind=use_engine)

