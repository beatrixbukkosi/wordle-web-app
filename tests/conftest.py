"""Pytest configuration ensuring backend and frontend directories are on sys.path."""

import sys
from pathlib import Path
from typing import Generator

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

PROJECT_ROOT = Path(__file__).resolve().parents[1]
BACKEND_PATH = PROJECT_ROOT / "backend"
FRONTEND_PATH = PROJECT_ROOT / "frontend"

sys.path.insert(0, str(BACKEND_PATH))
sys.path.insert(0, str(FRONTEND_PATH))

from repositories.database import Base
from repositories.game_repository import GameRepository
from services.game_service import GameService
import main as game_api


@pytest.fixture
def test_setup() -> Generator[GameService, None, None]:
    """Provides an isolated in-memory backend database for game API tests."""
    test_engine = create_engine(
        "sqlite:///:memory:",
        connect_args={"check_same_thread": False},
    )
    Base.metadata.create_all(bind=test_engine)
    test_session_factory = sessionmaker(
        autocommit=False,
        autoflush=False,
        expire_on_commit=False,
        bind=test_engine,
    )
    service = GameService(repository=GameRepository(session_factory=test_session_factory))
    service.load_dictionaries()

    original_service = game_api.game_service
    game_api.game_service = service
    try:
        yield service
    finally:
        game_api.game_service = original_service
        test_engine.dispose()
