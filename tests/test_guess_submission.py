"""Acceptance tests for AC1: valid guesses return colors and consume one attempt."""

from types import SimpleNamespace

import pytest

from frontend.views import game_view


class FakeSessionState:
    def __init__(self, **values: object) -> None:
        self.__dict__.update(values)

    def get(self, key: str, default: object = None) -> object:
        return getattr(self, key, default)


def test_keyboard_colors_keep_the_strongest_feedback() -> None:
    board = [
        list("ABCDE"),
        list("AFCDE"),
        list("CDEFG"),
    ]
    row_colors = [
        ["YELLOW", "GREEN", "GRAY", "GRAY", "YELLOW"],
        ["GREEN", "GRAY", "YELLOW", "GREEN", "GRAY"],
        ["GREEN", "GRAY", "GRAY", "GRAY", "GRAY"],
    ]

    assert game_view.get_keyboard_colors(board, row_colors) == {
        "A": "GREEN",
        "B": "GREEN",
        "C": "GREEN",
        "D": "GREEN",
        "E": "YELLOW",
        "F": "GRAY",
        "G": "GRAY",
    }


def test_keyboard_styles_target_each_colored_key() -> None:
    styles = game_view.get_keyboard_styles({"A": "GREEN", "Q": "YELLOW"})

    assert ".st-key-btn_A button" in styles
    assert "background-color: #6aaa64 !important" in styles
    assert ".st-key-btn_Q button" in styles
    assert "background-color: #c9b458 !important" in styles
    assert "[data-testid='stHorizontalBlock']:has(" in styles
    assert ":nth-child(9))" in styles


def test_submit_button_style_shows_valid_and_invalid_guesses() -> None:
    valid_style = game_view.get_submit_button_style(True)
    invalid_style = game_view.get_submit_button_style(False)

    assert "background-color: #6aaa64" in valid_style
    assert "background-color: #d9534f" in invalid_style
    assert "button[kind='primary']" in valid_style
    assert "button[kind='primary']:disabled" in invalid_style
    assert "cursor: not-allowed !important" in invalid_style
    assert game_view.get_submit_button_style(None) == ""


def test_winning_guess_sends_active_player_id_and_refreshes_streak(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    state = FakeSessionState(
        game_won=False,
        current_row=0,
        current_col=5,
        guess_is_valid=True,
        board=[list("APPLE") for _ in range(6)],
        row_colors=[[None] * 5 for _ in range(6)],
        session_id="session-1",
        player_id=21,
    )
    submitted_payload: dict[str, object] = {}

    def mock_post(url: str, **kwargs: object) -> SimpleNamespace:
        assert url.endswith("/api/v1/game/validate")
        submitted_payload.update(kwargs["json"])
        return SimpleNamespace(
            status_code=200,
            json=lambda: {
                "is_valid": True,
                "is_winning": True,
                "game_status": "WON",
                "colors": ["GREEN"] * 5,
            },
        )

    monkeypatch.setattr(game_view.st, "session_state", state)
    monkeypatch.setattr(game_view.requests, "post", mock_post)
    monkeypatch.setattr(
        game_view.state_manager,
        "load_player_stats",
        lambda: setattr(state, "current_streak", 1),
    )

    game_view.submit_guess()

    assert submitted_payload["session_id"] == "session-1"
    assert submitted_payload["user_id"] == 21
    assert state.game_won is True
    assert state.current_streak == 1


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
