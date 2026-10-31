# Test suite for AC7: Invalid Operation (Finished Game)

from types import SimpleNamespace

import pytest
from fastapi import HTTPException

import main as game_api
from frontend.views import game_view
from models.game_schemas import GuessRequest
from services.game_service import GameService


@pytest.mark.parametrize("terminal_state", ["WON", "LOST"])
def test_backend_rejects_guesses_after_game_ends(
    test_setup: GameService, terminal_state: str
) -> None:
    """Verifies AC7: the backend blocks guesses after either terminal state."""
    game = game_api.start_game()
    session = game_api.game_service.repository.get_by_session_id(game.session_id)
    assert session is not None

    if terminal_state == "WON":
        terminal_guess = session.secret_word
    else:
        terminal_guess = "CRANE" if session.secret_word != "CRANE" else "SLATE"
        for _ in range(5):
            game_api.validate_guess(
                GuessRequest(session_id=game.session_id, guess=terminal_guess)
            )
    game_api.validate_guess(
        GuessRequest(session_id=game.session_id, guess=terminal_guess)
    )
    finished_state = game_api.get_game_state(game.session_id)

    with pytest.raises(HTTPException) as error:
        game_api.validate_guess(
            GuessRequest(session_id=game.session_id, guess="CRANE")
        )

    assert error.value.status_code == 400
    unchanged_state = game_api.get_game_state(game.session_id)
    assert unchanged_state.game_status == terminal_state
    assert unchanged_state.remaining_attempts == finished_state.remaining_attempts
    assert unchanged_state.guesses == finished_state.guesses


class FakeSessionState:
    def __init__(self) -> None:
        self.game_won = False
        self.game_lost = True
        self.current_row = 0
        self.current_col = 0
        self.board = [[""] * 5 for _ in range(6)]
        self.row_colors = [[None] * 5 for _ in range(6)]

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


def test_frontend_ignores_input_after_game_ends(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies AC7: finished-game input handlers cannot change the board."""
    state = FakeSessionState()
    monkeypatch.setattr(game_view.st, "session_state", state)
    monkeypatch.setattr(
        game_view.requests,
        "post",
        lambda *args, **kwargs: pytest.fail("A finished game must not submit guesses"),
    )

    game_view.handle_key_press("A")
    game_view.submit_guess()

    assert state.current_row == 0
    assert state.current_col == 0
    assert state.board[0] == [""] * 5
