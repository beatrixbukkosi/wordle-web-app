"""Centralized global state initialization and URL session management for Wordle frontend."""

import os
from typing import Any
import requests
import streamlit as st

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")
BOARD_ROWS: int = 6
WORD_LENGTH: int = 5


def _init_user_profile_state() -> None:
    """Initializes player profile and leaderboard state variables if not present."""
    if "player_name" not in st.session_state:
        st.session_state.player_name = "Guest"
    if "streak" not in st.session_state:
        st.session_state.streak = 3
    if "longest_streak" not in st.session_state:
        st.session_state.longest_streak = 8
    if "games_played" not in st.session_state:
        st.session_state.games_played = 10
    if "wins" not in st.session_state:
        st.session_state.wins = 7
    if "saved_profiles" not in st.session_state:
        st.session_state.saved_profiles = ["Guest", "Alice", "Bob"]
    if "profile_mode" not in st.session_state:
        st.session_state.profile_mode = "view"
    if "global_leaderboard" not in st.session_state:
        st.session_state.global_leaderboard = [
            {"Rank": "🥇 1", "Player": "Alice", "Played": 42, "Wins": 38, "Win %": "90%", "Longest Streak": 12},
            {"Rank": "🥈 2", "Player": "Bob", "Played": 35, "Wins": 30, "Win %": "85%", "Longest Streak": 5},
        ]
    if "current_view" not in st.session_state:
        st.session_state.current_view = "game"


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
        response = requests.post(f"{BACKEND_URL}/api/v1/game/start", timeout=5)
        if response.status_code in (200, 201):
            data = response.json()
            session_id = data.get("session_id")
            st.session_state.session_id = session_id
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

    url_session_id = st.query_params.get("session_id")
    has_active_board = "board" in st.session_state and "row_colors" in st.session_state
    current_session = st.session_state.get("session_id")

    if has_active_board and current_session and current_session == url_session_id:
        return

    if url_session_id:
        game_data = fetch_game_state(url_session_id)
        if game_data:
            _restore_game_from_state(game_data)
            return

    start_new_game()
