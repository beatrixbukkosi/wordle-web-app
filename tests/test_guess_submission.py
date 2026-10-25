"""Acceptance tests for AC1: valid guesses return colors and consume one attempt."""

from types import SimpleNamespace

import pytest

from frontend.views import game_view


class FakeSessionState:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


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
    assert state.row_colors[current_row] == [
        "YELLOW",
        "YELLOW",
        "GREEN",
        "YELLOW",
        "GRAY",
    ]
