# Test suite for AC3: Edge Case (Defeat on 6th Attempt)


import logging
from typing import Generator
from fastapi import HTTPException
import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import main as game_api
from models.game_schemas import GuessRequest
from repositories.database import Base
from repositories.game_repository import GameRepository
from services.game_service import GameService

from models.game_schemas import UserCreateRequest
from repositories.user_repository import UserRepository


@pytest.fixture
def player_service() -> Generator[GameService, None, None]:
    """Configures the API with an isolated in-memory database."""
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
    repository = GameRepository(session_factory=test_session_factory)
    user_repository = UserRepository(session_factory=test_session_factory)
    service = GameService(repository=repository, user_repository=user_repository)
    service.load_dictionaries()

    original_service = game_api.game_service
    game_api.game_service = service
    yield service
    game_api.game_service = original_service
    test_engine.dispose()


def _create_user(username: str) -> int:
    return game_api.create_user(UserCreateRequest(username=username)).id


def _complete_win(session_id: str, secret_word: str) -> None:
    game_api.validate_guess(
        GuessRequest(session_id=session_id, guess=secret_word)
    )


def _complete_loss(service: GameService, session_id: str, secret_word: str) -> None:
    wrong_guess = next(
        word for word in service.valid_guesses if word != secret_word
    )
    for _ in range(6):
        game_api.validate_guess(
            GuessRequest(session_id=session_id, guess=wrong_guess)
        )


def test_exhausting_attempts_updates_game_status_to_lost(test_setup: GameService) -> None:
    """Verifies that after 6 non-winning attempts the game status transitions to LOST."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    session_model = game_api.game_service.repository.get_by_session_id(session_id)
    assert session_model is not None
    # Pick a valid guess that is different from the secret word
    wrong_guess = "CRANE" if session_model.secret_word != "CRANE" else "SLATE"

    for attempt in range(1, 7):
        resp = game_api.validate_guess(
            GuessRequest(session_id=session_id, guess=wrong_guess)
        )
        data = resp.model_dump()
        assert data["remaining_attempts"] == 6 - attempt
        if attempt == 6:
            assert data["game_status"] == "LOST"
        else:
            assert data["game_status"] == "IN_PROGRESS"


def test_lost_game_resets_player_streak(player_service: GameService) -> None:
    """Verifies AC3: losing a game resets the player's current streak."""
    user_id = _create_user("StreakPlayer")
    winning_game = game_api.start_game(user_id=user_id)
    winning_session = player_service.get_game_state(winning_game.session_id)
    assert winning_session is not None
    _complete_win(winning_game.session_id, winning_session.secret_word)
    lost_game = game_api.start_game(user_id=user_id)
    lost_session = player_service.get_game_state(lost_game.session_id)
    assert lost_session is not None
    _complete_loss(player_service, lost_game.session_id, lost_session.secret_word)
    stats = game_api.get_user_stats(user_id)
    assert stats.games_played == 2
    assert stats.games_won == 1
    assert stats.current_streak == 0
