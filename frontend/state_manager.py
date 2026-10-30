"""Centralized global state initialization and URL session management for Wordle frontend."""

import os
from typing import Any
import requests
import streamlit as st

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
BOARD_ROWS: int = 6
WORD_LENGTH: int = 5


def _init_user_profile_state() -> None:
    """Initializes active player profile state if not present."""
    if "player_name" not in st.session_state:
        st.session_state.player_name = ""
    if "saved_profiles" not in st.session_state:
        st.session_state.saved_profiles = []
    if "profile_mode" not in st.session_state:
        st.session_state.profile_mode = "view"
    if "current_view" not in st.session_state:
        st.session_state.current_view = "game"


def select_profile(username: str) -> None:
    """Selects or creates a persistent profile and updates the active player."""
    normalized_username = username.strip()
    if not normalized_username:
        st.session_state.backend_error = "Player name cannot be empty."
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/users",
            json={"username": normalized_username},
            timeout=5,
        )
        if response.status_code in (200, 201):
            user_data = response.json()
            if not isinstance(user_data.get("id"), int) or not isinstance(
                user_data.get("username"), str
            ):
                st.session_state.backend_error = "Backend returned an invalid player profile."
                st.session_state.pop("player_id", None)
                st.session_state.player_name = normalized_username
                return
            st.session_state.player_id = user_data["id"]
            st.session_state.player_name = user_data["username"]
            profiles = st.session_state.saved_profiles
            if user_data["username"] not in profiles:
                profiles.append(user_data["username"])
            st.query_params["player"] = user_data["username"]
            st.session_state.backend_error = None
            return
        st.session_state.backend_error = (
            f"Failed to load player profile (HTTP {response.status_code})."
        )
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"

    st.session_state.player_name = normalized_username
    st.session_state.pop("player_id", None)


def rename_active_profile(username: str) -> bool:
    """Renames the active persistent profile while retaining its player ID."""
    player_id = st.session_state.get("player_id")
    normalized_username = username.strip()
    if player_id is None:
        st.session_state.backend_error = "The active profile is not connected to the backend."
        return False
    if not normalized_username:
        st.session_state.backend_error = "Player name cannot be empty."
        return False

    try:
        response = requests.put(
            f"{BACKEND_URL}/api/v1/users/{player_id}",
            json={"username": normalized_username},
            timeout=5,
        )
        if response.status_code == 200:
            user_data = response.json()
            st.session_state.player_name = user_data["username"]
            profiles = st.session_state.saved_profiles
            old_name = st.session_state.get("profile_original_name")
            if old_name is not None and old_name in profiles:
                profiles.remove(old_name)
            if user_data["username"] not in profiles:
                profiles.append(user_data["username"])
            st.query_params["player"] = user_data["username"]
            st.session_state.backend_error = None
            return True
        if response.status_code == 409:
            st.session_state.backend_error = "That username is already in use."
        else:
            st.session_state.backend_error = (
                f"Failed to rename profile (HTTP {response.status_code})."
            )
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"
    return False


def delete_active_profile() -> bool:
    """Deletes the active profile and selects a fresh default profile."""
    player_id = st.session_state.get("player_id")
    if player_id is None:
        st.session_state.backend_error = "The active profile is not connected to the backend."
        return False

    try:
        response = requests.delete(
            f"{BACKEND_URL}/api/v1/users/{player_id}",
            timeout=5,
        )
        if response.status_code != 204:
            st.session_state.backend_error = (
                f"Failed to delete profile (HTTP {response.status_code})."
            )
            return False
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"
        return False

    active_player_name = st.session_state.player_name
    st.session_state.saved_profiles = [
        profile
        for profile in st.session_state.saved_profiles
        if profile != active_player_name
    ]
    st.session_state.pop("player_id", None)
    st.session_state.player_name = ""
    st.query_params.pop("player", None)
    load_saved_profiles()
    if st.session_state.saved_profiles:
        select_profile(st.session_state.saved_profiles[0])
    else:
        st.session_state.pop("player_id", None)
        st.session_state.player_name = ""
    start_new_game()
    return True


def load_saved_profiles() -> None:
    """Refreshes the profile selector with names persisted by the backend."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/users", timeout=5)
        if response.status_code == 200:
            st.session_state.saved_profiles = [
                user["username"] for user in response.json()
            ]
            if (
                st.session_state.player_name
                and st.session_state.player_name
                not in st.session_state.saved_profiles
            ):
                st.session_state.saved_profiles.append(st.session_state.player_name)
            st.session_state.backend_error = None
        else:
            st.session_state.backend_error = (
                f"Failed to load player profiles (HTTP {response.status_code})."
            )
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"


def load_player_stats() -> None:
    """Refreshes the active player's current streak for the application header."""
    player_id = st.session_state.get("player_id")
    if player_id is None:
        st.session_state.current_streak = 0
        st.session_state.stats_user_id = None
        return

    try:
        response = requests.get(
            f"{BACKEND_URL}/api/v1/users/{player_id}/stats",
            timeout=5,
        )
        if response.status_code == 200:
            st.session_state.current_streak = response.json()["current_streak"]
            st.session_state.stats_user_id = player_id
        else:
            st.session_state.backend_error = (
                f"Failed to load player statistics (HTTP {response.status_code})."
            )
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"


def associate_game_with_active_player(session_id: str) -> None:
    """Links an unowned restored game to the active profile once."""
    player_id = st.session_state.get("player_id")
    if player_id is None or st.session_state.get("associated_session_id") == session_id:
        return

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/game/{session_id}/associate",
            json={"user_id": player_id},
            timeout=5,
        )
        if response.status_code == 200:
            st.session_state.associated_session_id = session_id
            st.session_state.backend_error = None
            load_player_stats()
        else:
            st.session_state.backend_error = (
                f"Failed to associate game with player (HTTP {response.status_code})."
            )
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"


def _reset_board_state() -> None:
    """Resets the game board and attempt counters to an empty initial state."""
    st.session_state.board = [["" for _ in range(WORD_LENGTH)] for _ in range(BOARD_ROWS)]
    st.session_state.row_colors = [[None for _ in range(WORD_LENGTH)] for _ in range(BOARD_ROWS)]
    st.session_state.current_row = 0
    st.session_state.current_col = 0
    st.session_state.game_won = False
    st.session_state.game_lost = False
    st.session_state.game_status = "IN_PROGRESS"
    st.session_state.guess_is_valid = None


def _restore_game_from_state(game_data: dict[str, Any]) -> None:
    """Reconstructs board tiles, colors, and game status from server session data."""
    st.session_state.session_id = game_data.get("session_id")
    status = game_data.get("game_status", "IN_PROGRESS")
    st.session_state.game_status = status
    st.session_state.game_won = (status == "WON")
    st.session_state.game_lost = (status == "LOST")

    board = [["" for _ in range(WORD_LENGTH)] for _ in range(BOARD_ROWS)]
    row_colors = [[None for _ in range(WORD_LENGTH)] for _ in range(BOARD_ROWS)]
    guesses = game_data.get("guesses", [])

    for row_idx, guess_item in enumerate(guesses[:BOARD_ROWS]):
        guess_str = guess_item.get("guess", "")
        board[row_idx] = list(guess_str.upper())[:WORD_LENGTH]
        row_colors[row_idx] = guess_item.get("colors", [None] * WORD_LENGTH)

    st.session_state.board = board
    st.session_state.row_colors = row_colors
    st.session_state.current_row = min(len(guesses), BOARD_ROWS - 1 if (st.session_state.game_won or st.session_state.game_lost) else len(guesses))
    st.session_state.current_col = 0
    st.session_state.guess_is_valid = None


def fetch_game_state(session_id: str) -> dict[str, Any] | None:
    """Fetches full game state from the backend for the given session identifier."""
    try:
        response = requests.get(f"{BACKEND_URL}/api/v1/game/{session_id}", timeout=5)
        if response.status_code == 200:
            return response.json()
        return None
    except requests.exceptions.RequestException:
        return None


def start_new_game() -> None:
    """Requests a new game session from the backend and resets board and URL state."""
    try:
        player_id = st.session_state.get("player_id")
        response = requests.post(
            f"{BACKEND_URL}/api/v1/game/start",
            params={"user_id": player_id} if player_id is not None else None,
            timeout=5,
        )
        if response.status_code in (200, 201):
            data = response.json()
            session_id = data.get("session_id")
            st.session_state.session_id = session_id
            st.session_state.associated_session_id = (
                session_id if player_id is not None else None
            )
            st.query_params["session_id"] = session_id
            st.session_state.backend_error = None
            _reset_board_state()
            return
        st.session_state.backend_error = f"Failed to start game (HTTP {response.status_code})"
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"

    st.session_state.session_id = "OFFLINE"
    _reset_board_state()


def initialize_state() -> None:
    """Central entry point initializing global state and restoring active session from URL if present."""
    _init_user_profile_state()

    requested_player = st.query_params.get("player")
    if requested_player == "Guest" or st.session_state.player_name == "Guest":
        st.query_params.pop("player", None)
        requested_player = None
        st.session_state.pop("player_id", None)
        st.session_state.player_name = ""
        st.session_state.saved_profiles = [
            profile
            for profile in st.session_state.saved_profiles
            if profile != "Guest"
        ]
    if requested_player and requested_player != st.session_state.player_name:
        select_profile(requested_player)
    elif "player_id" not in st.session_state and st.session_state.player_name:
        select_profile(st.session_state.player_name)
    if st.session_state.get("stats_user_id") != st.session_state.get("player_id"):
        load_player_stats()

    url_session_id = st.query_params.get("session_id")
    has_active_board = "board" in st.session_state and "row_colors" in st.session_state
    current_session = st.session_state.get("session_id")

    if has_active_board and current_session and current_session == url_session_id:
        associate_game_with_active_player(current_session)
        return

    if url_session_id:
        game_data = fetch_game_state(url_session_id)
        if game_data:
            associate_game_with_active_player(url_session_id)
            _restore_game_from_state(game_data)
            return

    start_new_game()
