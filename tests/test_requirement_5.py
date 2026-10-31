# Test suite for AC5: Invalid Input (Format Validation)

import pytest

from frontend.views import game_view
import main as game_api
from models.game_schemas import GuessRequest
from services.game_service import GameService


def test_submit_button_style_marks_invalid_guesses_as_disabled() -> None:
    """Verifies AC5: the submit button has an invalid and disabled visual state."""
    valid_style = game_view.get_submit_button_style(True)
    invalid_style = game_view.get_submit_button_style(False)

    assert "background-color: #6aaa64" in valid_style
    assert "background-color: #d9534f" in invalid_style
    assert "button[kind='primary']:disabled" in invalid_style
    assert "cursor: not-allowed !important" in invalid_style
    assert game_view.get_submit_button_style(None) == ""


@pytest.mark.parametrize("guess", ["PAPE", "PAPER1", "PA1ER"])
def test_malformed_guess_is_rejected_without_using_an_attempt(
    test_setup: GameService, guess: str
) -> None:
    """Verifies AC5: malformed guesses do not consume an attempt."""
    game = game_api.start_game()

    response = game_api.validate_guess(
        GuessRequest(session_id=game.session_id, guess=guess)
    )

    assert response.is_valid is False
    assert response.remaining_attempts == 6
    state = game_api.get_game_state(game.session_id)
    assert state.remaining_attempts == 6
    assert state.guesses == []
