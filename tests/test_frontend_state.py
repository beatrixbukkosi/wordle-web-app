"""Tests for Streamlit frontend session management and URL state restoration."""

from types import SimpleNamespace
from typing import Any
import pytest
import streamlit as st

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


def test_start_new_game_sets_session_id_in_url_and_state(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that starting a new game updates session_state and URL query parameters."""
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {}

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(
        state_manager.requests,
        "post",
        lambda url, **kwargs: SimpleNamespace(
            status_code=201,
            json=lambda: {
                "session_id": "new-session-789",
                "word_length": 5,
                "max_attempts": 6,
                "remaining_attempts": 6,
                "game_status": "IN_PROGRESS",
                "guesses": [],
            },
        ),
    )

    state_manager.start_new_game()

    assert fake_state.session_id == "new-session-789"
    assert fake_query_params["session_id"] == "new-session-789"
    assert fake_state.current_row == 0
    assert fake_state.current_col == 0
    assert fake_state.board == [["" for _ in range(5)] for _ in range(6)]
    assert fake_state.row_colors == [[None for _ in range(5)] for _ in range(6)]
    assert "secret_word" not in fake_state
    assert "target_word" not in fake_state


def test_start_new_game_associates_active_player(monkeypatch: pytest.MonkeyPatch) -> None:
    fake_state = FakeSessionState(player_id=42)
    fake_query_params: dict[str, str] = {}
    request_params: list[dict[str, int] | None] = []

    def mock_post(url: str, **kwargs: Any) -> SimpleNamespace:
        request_params.append(kwargs.get("params"))
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"session_id": "player-game-session"},
        )

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "post", mock_post)

    state_manager.start_new_game()

    assert request_params == [{"user_id": 42}]


def test_initialize_without_profile_does_not_create_guest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {}
    requested_urls: list[str] = []

    def mock_post(url: str, **kwargs: Any) -> SimpleNamespace:
        requested_urls.append(url)
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"session_id": "anonymous-session"},
        )

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "post", mock_post)

    state_manager.initialize_state()

    assert fake_state.player_name == ""
    assert fake_state.saved_profiles == []
    assert "player_id" not in fake_state
    assert requested_urls == [f"{state_manager.BACKEND_URL}/api/v1/game/start"]
    assert "player" not in fake_query_params


def test_rename_active_profile_uses_update_and_keeps_profile_id(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_state = FakeSessionState(
        player_id=42,
        player_name="OldName",
        profile_original_name="OldName",
        saved_profiles=["OldName", "Other"],
        profile_mode="edit",
        name_input="NewName",
    )
    fake_query_params: dict[str, str] = {}
    request_data: dict[str, Any] = {}

    def mock_put(url: str, **kwargs: Any) -> SimpleNamespace:
        request_data.update({"url": url, **kwargs})
        return SimpleNamespace(
            status_code=200,
            json=lambda: {"id": 42, "username": "NewName"},
        )

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "put", mock_put)
    monkeypatch.setattr(
        state_manager.requests,
        "post",
        lambda *args, **kwargs: pytest.fail("Renaming must not create a profile"),
    )

    profile_view.save_profile()

    assert request_data["url"].endswith("/api/v1/users/42")
    assert request_data["json"] == {"username": "NewName"}
    assert fake_state.player_id == 42
    assert fake_state.player_name == "NewName"
    assert fake_state.saved_profiles == ["Other", "NewName"]
    assert fake_query_params["player"] == "NewName"
    assert fake_state.profile_mode == "view"


def test_switching_profile_starts_a_new_game(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_state = FakeSessionState(
        player_id=12,
        profile_selectbox="AnotherPlayer",
        profile_mode="switch",
    )
    selected_profiles: list[str] = []
    started_games: list[bool] = []

    def select_profile(username: str) -> None:
        selected_profiles.append(username)
        fake_state.player_id = 24

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(state_manager, "select_profile", select_profile)
    monkeypatch.setattr(
        state_manager,
        "start_new_game",
        lambda: started_games.append(True),
    )

    profile_view.apply_switch_profile()

    assert selected_profiles == ["AnotherPlayer"]
    assert started_games == [True]
    assert fake_state.profile_mode == "view"


def test_delete_last_profile_leaves_no_guest_profile(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    fake_state = FakeSessionState(
        player_id=42,
        player_name="RemoveMe",
        saved_profiles=["RemoveMe"],
    )
    fake_query_params: dict[str, str] = {}
    deleted_urls: list[str] = []
    post_urls: list[str] = []

    def mock_delete(url: str, **kwargs: Any) -> SimpleNamespace:
        deleted_urls.append(url)
        return SimpleNamespace(status_code=204)

    def mock_post(url: str, **kwargs: Any) -> SimpleNamespace:
        post_urls.append(url)
        return SimpleNamespace(
            status_code=201,
            json=lambda: {"session_id": "anonymous-game"},
        )

    monkeypatch.setattr(
        state_manager.requests,
        "get",
        lambda *args, **kwargs: SimpleNamespace(status_code=200, json=lambda: []),
    )
    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager.requests, "delete", mock_delete)
    monkeypatch.setattr(state_manager.requests, "post", mock_post)

    assert state_manager.delete_active_profile() is True

    assert deleted_urls == [f"{state_manager.BACKEND_URL}/api/v1/users/42"]
    assert post_urls == [f"{state_manager.BACKEND_URL}/api/v1/game/start"]
    assert fake_state.player_name == ""
    assert "player_id" not in fake_state
    assert "RemoveMe" not in fake_state.saved_profiles
    assert "player" not in fake_query_params
    assert fake_state.session_id == "anonymous-game"


def test_invalid_url_session_id_triggers_new_game(monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that when URL contains an invalid or expired session_id, a fresh game is created."""
    fake_state = FakeSessionState()
    fake_query_params: dict[str, str] = {"session_id": "expired-session-id"}

    monkeypatch.setattr(st, "session_state", fake_state)
    monkeypatch.setattr(st, "query_params", fake_query_params)
    monkeypatch.setattr(state_manager, "fetch_game_state", lambda session_id: None)
    monkeypatch.setattr(
        state_manager.requests,
        "post",
        lambda url, **kwargs: SimpleNamespace(
            status_code=201,
            json=lambda: {
                "session_id": "fallback-fresh-session",
                "word_length": 5,
                "max_attempts": 6,
                "remaining_attempts": 6,
                "game_status": "IN_PROGRESS",
                "guesses": [],
            },
        ),
    )

    state_manager.initialize_state()

    assert fake_state.session_id == "fallback-fresh-session"
    assert fake_query_params["session_id"] == "fallback-fresh-session"
    assert fake_state.current_row == 0
