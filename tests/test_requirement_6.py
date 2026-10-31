# Test suite for AC6: Invalid Input (Dictionary Validation)


import pytest
import main as game_api
from services.game_service import GameService

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


@pytest.mark.parametrize(
    ("guess", "valid_guesses", "expected"),
    [("PAPER", {"PAPER"}, True), ("XXXXX", {"PAPER"}, False)],
)
def test_validate_word_checks_dictionary_without_submitting_guess(
    monkeypatch: pytest.MonkeyPatch,
    guess: str,
    valid_guesses: set[str],
    expected: bool,
) -> None:
    """Verifies requirement 6 behavior."""
    monkeypatch.setattr(game_api.game_service, "valid_guesses", valid_guesses)

    response = game_api.validate_word(game_api.WordValidationRequest(guess=guess))

    assert response.is_valid is expected


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
