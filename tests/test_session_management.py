"""Tests for backend server-side session management, persistence, security, and logging."""

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


@pytest.fixture
def test_setup() -> Generator[GameService, None, None]:
    """Configures an in-memory database and fresh GameService for test isolation."""
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
    test_repo = GameRepository(session_factory=test_session_factory)
    test_service = GameService(repository=test_repo)
    test_service.load_dictionaries()

    # Inject into main controller
    original_service = game_api.game_service
    game_api.game_service = test_service

    yield test_service

    game_api.game_service = original_service


def test_start_game_generates_session_id_and_hides_secret_word(test_setup: GameService) -> None:
    """Verifies that starting a game generates a unique session_id and never exposes secret_word."""
    response = game_api.start_game()
    data = response.model_dump()

    assert "session_id" in data
    assert isinstance(data["session_id"], str)
    assert len(data["session_id"]) > 0

    assert data["word_length"] == 5
    assert data["max_attempts"] == 6
    assert data["remaining_attempts"] == 6
    assert data["game_status"] == "IN_PROGRESS"
    assert data["guesses"] == []

    # Security check: secret_word and target_word must NEVER be in client response
    assert "secret_word" not in data
    assert "target_word" not in data
    assert not hasattr(response, "secret_word")
    assert not hasattr(response, "target_word")


def test_start_game_logs_secret_word_and_session_id(
    test_setup: GameService,
    caplog: pytest.LogCaptureFixture,
) -> None:
    """Verifies that backend logs the secret word and session_id upon game creation for dev testing."""
    with caplog.at_level(logging.INFO):
        response = game_api.start_game()
        session_id = response.session_id

        matching_logs = [
            record.message
            for record in caplog.records
            if session_id in record.message and "Secret Word:" in record.message
        ]
        assert len(matching_logs) == 1
        assert "New game started" in matching_logs[0]


def test_query_game_state_by_session_id(test_setup: GameService) -> None:
    """Verifies that active game state can be retrieved by session_id without secret_word."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    state_resp = game_api.get_game_state(session_id)
    data = state_resp.model_dump()

    assert data["session_id"] == session_id
    assert data["remaining_attempts"] == 6
    assert data["game_status"] == "IN_PROGRESS"
    assert data["guesses"] == []

    # Security check: secret_word and target_word must NEVER be in client response
    assert "secret_word" not in data
    assert "target_word" not in data
    assert not hasattr(state_resp, "secret_word")
    assert not hasattr(state_resp, "target_word")


def test_query_nonexistent_session_raises_404(test_setup: GameService) -> None:
    """Verifies that querying an unknown session_id raises HTTPException 404."""
    with pytest.raises(HTTPException) as exc_info:
        game_api.get_game_state("non-existent-session-id")
    assert exc_info.value.status_code == 404


def test_submit_valid_guess_persists_state_and_decrements_attempts(test_setup: GameService) -> None:
    """Verifies that submitting a valid guess updates server state and persists previous guesses."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    guess_resp = game_api.validate_guess(
        GuessRequest(session_id=session_id, guess="CRANE")
    )
    guess_data = guess_resp.model_dump()
    assert guess_data["is_valid"] is True
    assert guess_data["remaining_attempts"] == 5
    assert len(guess_data["colors"]) == 5
    assert "secret_word" not in guess_data
    assert "target_word" not in guess_data

    # Query state from server to confirm persistence
    state_resp = game_api.get_game_state(session_id)
    state_data = state_resp.model_dump()
    assert state_data["remaining_attempts"] == 5
    assert len(state_data["guesses"]) == 1
    assert state_data["guesses"][0]["guess"] == "CRANE"
    assert state_data["guesses"][0]["colors"] == guess_data["colors"]


def test_submit_invalid_word_does_not_consume_attempt(test_setup: GameService) -> None:
    """Verifies that an invalid word does not consume an attempt or alter stored guesses."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    guess_resp = game_api.validate_guess(
        GuessRequest(session_id=session_id, guess="ZZZZZ")
    )
    guess_data = guess_resp.model_dump()
    assert guess_data["is_valid"] is False
    assert guess_data["remaining_attempts"] == 6

    # Verify server state is unchanged
    state_resp = game_api.get_game_state(session_id)
    state_data = state_resp.model_dump()
    assert state_data["remaining_attempts"] == 6
    assert len(state_data["guesses"]) == 0


def test_winning_guess_updates_game_status_to_won(test_setup: GameService) -> None:
    """Verifies that submitting the correct word sets status to WON and prevents further guesses."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    # Retrieve internal secret word from repository for test verification
    session_model = game_api.game_service.repository.get_by_session_id(session_id)
    assert session_model is not None
    secret = session_model.secret_word

    win_resp = game_api.validate_guess(
        GuessRequest(session_id=session_id, guess=secret)
    )
    win_data = win_resp.model_dump()
    assert win_data["is_winning"] is True
    assert win_data["game_status"] == "WON"
    assert win_data["colors"] == ["GREEN"] * 5

    # Submitting another guess after win must raise 400
    with pytest.raises(HTTPException) as exc_info:
        game_api.validate_guess(
            GuessRequest(session_id=session_id, guess="CRANE")
        )
    assert exc_info.value.status_code == 400


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

    # Further guesses must be rejected with 400
    with pytest.raises(HTTPException) as blocked_exc:
        game_api.validate_guess(
            GuessRequest(session_id=session_id, guess=wrong_guess)
        )
    assert blocked_exc.value.status_code == 400
