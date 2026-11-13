# Test suite for AC8: State Management and Persistence


from types import SimpleNamespace
from typing import Any
import pytest
import streamlit as st
import main as game_api
from services.game_service import GameService
import state_manager
from views import profile_view


class FakeSessionState(dict):
    """Dict-like mock of Streamlit session_state supporting attribute access."""

    def __getattr__(self, name: str) -> Any:
        try:
            return self[name]
        except KeyError:
            raise AttributeError(name)

    def __setattr__(self, name: str, value: Any) -> None:
        self[name] = value

    def __delattr__(self, name: str) -> None:
        try:
            del self[name]
        except KeyError:
            raise AttributeError(name)


def test_restore_active_state_from_url_on_refresh(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that on page refresh (F5), existing session state is reconstructed from backend."""
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {"session_id": "persisted-session-456"}

    # Mock server response for the session in URL
    mock_game_data = {
        "session_id": "persisted-session-456",
        "word_length": 5,
        "max_attempts": 6,
        "remaining_attempts": 4,
        "game_status": "IN_PROGRESS",
        "guesses": [
            {"guess": "SLATE", "colors": ["GRAY", "YELLOW", "GRAY", "GRAY", "GREEN"]},
            {"guess": "CRANE", "colors": ["GRAY", "GRAY", "GREEN", "GRAY", "GREEN"]},
        ],
    }

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager, "load_saved_profiles", lambda: None)
    monkeypatch.setattr(
        state_manager,
        "fetch_game_state",
        lambda session_id: mock_game_data if session_id == "persisted-session-456" else None,
    )

    # Trigger initialization (simulates F5)
    state_manager.initialize_state()

    # Assert session restored correctly
    assert fake_state.session_id == "persisted-session-456"
    assert fake_state.current_row == 2
    assert fake_state.current_col == 0
    assert fake_state.game_won is False
    assert fake_state.game_lost is False
    assert fake_state.game_status == "IN_PROGRESS"

    # Board tile checks
    assert fake_state.board[0] == ["S", "L", "A", "T", "E"]
    assert fake_state.board[1] == ["C", "R", "A", "N", "E"]
    assert fake_state.board[2] == ["", "", "", "", ""]

    # Color checks
    assert fake_state.row_colors[0] == ["GRAY", "YELLOW", "GRAY", "GRAY", "GREEN"]
    assert fake_state.row_colors[1] == ["GRAY", "GRAY", "GREEN", "GRAY", "GREEN"]
    assert fake_state.row_colors[2] == [None] * 5

    # Security check: secret_word or target_word MUST NOT exist in state
    assert "secret_word" not in fake_state
    assert "target_word" not in fake_state


def test_query_game_state_by_session_id(test_setup: GameService) -> None:
    """Verifies AC8: backend state includes guesses needed to restore a session."""
    start_resp = game_api.start_game()
    session_id = start_resp.session_id

    state_resp = game_api.get_game_state(session_id)
    data = state_resp.model_dump()

    assert data["session_id"] == session_id
    assert data["remaining_attempts"] == 6
    assert data["game_status"] == "IN_PROGRESS"
    assert data["guesses"] == []
    assert "secret_word" not in data
    assert "target_word" not in data
