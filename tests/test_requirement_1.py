# Test suite for AC1: Normal Operation (Guess Evaluation)


import pytest
import main as game_api
from services.game_service import GameService

from types import SimpleNamespace
import pytest
from frontend.views import game_view

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


class FakeSessionState:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


@pytest.mark.parametrize(
    ("guess", "target_word", "expected_colors"),
    [
        ("PAPER", "APPLE", ["YELLOW", "YELLOW", "GREEN", "YELLOW", "GRAY"]),
        ("CRANE", "SLATE", ["GRAY", "GRAY", "GREEN", "GRAY", "GREEN"]),
        ("SLATE", "SLATE", ["GREEN"] * 5),
        ("XXXXX", "APPLE", ["GRAY"] * 5),
    ],
)
def test_evaluate_guess_returns_a_color_for_each_letter(
    guess: str, target_word: str, expected_colors: list[str]
) -> None:
    """Verifies AC1: valid five-letter guesses receive Wordle colors per letter."""
    # Arrange
    game_service = GameService()

    # Act
    colors = game_service.evaluate_guess(guess, target_word)

    # Assert
    assert colors == expected_colors
    assert len(colors) == len(guess)


def test_validate_guess_returns_colors_for_a_valid_five_letter_guess(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verifies AC1: the validation endpoint returns per-letter statuses."""
    # Arrange
    monkeypatch.setattr(game_api.game_service, "valid_guesses", {"PAPER"})
    request = game_api.GuessRequest(guess="PAPER", target_word="APPLE")

    # Act
    response = game_api.validate_guess(request)

    # Assert
    assert response["is_valid"] is True
    assert response["colors"] == ["YELLOW", "YELLOW", "GREEN", "YELLOW", "GRAY"]


@pytest.mark.parametrize("current_row", [0, 2, 4])
def test_valid_nonwinning_guess_uses_one_attempt(
    monkeypatch: pytest.MonkeyPatch, current_row: int
) -> None:
    """Verifies AC1: a valid non-winning guess advances by one attempt."""
    # Arrange
    state = FakeSessionState(
        game_won=False,
        current_row=current_row,
        current_col=5,
        guess_is_valid=True,
        board=[["P", "A", "P", "E", "R"] for _ in range(6)],
        target_word="APPLE",
        row_colors=[[None] * 5 for _ in range(6)],
    )
    monkeypatch.setattr(game_view.st, "session_state", state)
    monkeypatch.setattr(game_view.st, "toast", lambda *args, **kwargs: None)
    monkeypatch.setattr(
        game_view.requests,
        "post",
        lambda *args, **kwargs: SimpleNamespace(
            status_code=200,
            json=lambda: {
                "is_valid": True,
                "is_winning": False,
                "colors": ["YELLOW", "YELLOW", "GREEN", "YELLOW", "GRAY"],
            },
        ),
    )

    # Act
    game_view.submit_guess()

    # Assert
    assert state.current_row == current_row + 1
    assert state.current_col == 0
    assert state.guess_is_valid is None
    assert state.row_colors[current_row] == [
        "YELLOW",
        "YELLOW",
        "GREEN",
        "YELLOW",
        "GRAY",
    ]


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
