"""Game view rendering the Wordle board, letter tiles, and virtual keyboard."""

import os
import requests
import streamlit as st

import state_manager

BACKEND_URL: str = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")

TILE_COLORS: dict[str, str] = {
    "GREEN": "#6aaa64",
    "YELLOW": "#c9b458",
    "GRAY": "#787c7e",
}

KEYBOARD_ROWS: list[list[str]] = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
    ["Z", "X", "C", "V", "B", "N", "M", "⌫"],
]


def submit_guess() -> None:
    """Submits the current row guess to the backend and handles evaluation results."""
    if st.session_state.get("game_won", False) or st.session_state.get("game_lost", False):
        return

    row = st.session_state.current_row
    if st.session_state.current_col != 5:
        return

    guess_word = "".join(st.session_state.board[row]).upper()
    session_id = st.session_state.get("session_id")

    payload: dict[str, str | None] = {"guess": guess_word}
    if session_id:
        payload["session_id"] = session_id
    if getattr(st.session_state, "target_word", None):
        payload["target_word"] = st.session_state.target_word

    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/game/validate",
            json=payload,
            timeout=5,
        )
        if response.status_code == 200:
            data = response.json()
            if not data.get("is_valid", False):
                st.toast(f"'{guess_word}' is not a valid word!", icon="⚠️")
                return

            colors = data.get("colors") or [None] * len(guess_word)
            st.session_state.row_colors[row] = colors

            is_winning = data.get("is_winning", False) or data.get("game_status") == "WON"
            if is_winning:
                st.session_state.game_won = True
                st.session_state.game_status = "WON"
                st.toast("Congratulations! That's the winning word! 🎉", icon="🏆")
            else:
                remaining = data.get("remaining_attempts")
                status = data.get("game_status")
                is_lost = status == "LOST" or remaining == 0 or (row >= 5 and remaining is None)
                if is_lost:
                    st.session_state.game_lost = True
                    st.session_state.game_status = "LOST"
                    st.toast("Game over! You've used all attempts.", icon="😢")
                else:
                    st.toast(f"'{guess_word}' is a valid guess!", icon="✅")
                    if st.session_state.current_row < 5:
                        st.session_state.current_row += 1
                        st.session_state.current_col = 0
        else:
            st.toast("Error validating guess with server.", icon="🚨")
    except requests.exceptions.RequestException:
        st.toast("Backend is unreachable!", icon="🚨")


def handle_key_press(key: str) -> None:
    """Handles virtual keyboard clicks for letters, backspace, and submit."""
    if st.session_state.get("game_won", False) or st.session_state.get("game_lost", False):
        return

    row = st.session_state.current_row
    col = st.session_state.current_col

    if key == "⌫":
        if col > 0:
            st.session_state.current_col -= 1
            st.session_state.board[row][st.session_state.current_col] = ""
    elif key == "SUBMIT":
        submit_guess()
    else:
        if col < 5 and row < 6:
            st.session_state.board[row][col] = key
            st.session_state.current_col += 1


def render() -> None:
    """Renders the game board, game completion status banner, keyboard, and actions."""
    game_won = st.session_state.get("game_won", False)
    game_lost = st.session_state.get("game_lost", False)
    game_over = game_won or game_lost

    if game_won:
        st.success("🎉 Congratulations! You guessed the word correctly!")
    elif game_lost:
        st.error("Game Over! All attempts used.")

    # Render board grid
    grid_html = "<div class='wordle-grid'>"
    for row in range(6):
        grid_html += "<div class='wordle-row'>"
        for col in range(5):
            letter = st.session_state.board[row][col]
            color = st.session_state.row_colors[row][col]
            if color:
                tile_color = TILE_COLORS.get(color, "#787c7e")
                style = f"background-color: {tile_color}; border-color: {tile_color}; color: white;"
            else:
                border_color = "#878a8c" if letter else "#d3d6da"
                style = f"border-color: {border_color};"
            grid_html += f"<div class='wordle-box' style='{style}'>{letter}</div>"
        grid_html += "</div>"
    grid_html += "</div>"

    st.markdown(grid_html, unsafe_allow_html=True)

    # Render virtual keyboard
    for row_keys in KEYBOARD_ROWS:
        cols = st.columns(len(row_keys))
        for index, key in enumerate(row_keys):
            cols[index].button(
                key,
                key=f"btn_{key}",
                use_container_width=True,
                disabled=game_over,
                on_click=handle_key_press,
                args=(key,),
            )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Render submit button centered, with start new game below it at a small distance
    can_submit = st.session_state.current_col == 5 and not game_over
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:
        st.button(
            "SUBMIT GUESS",
            key="btn_submit_guess",
            use_container_width=True,
            disabled=not can_submit,
            on_click=submit_guess,
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.button(
            "🔄 Start New Game",
            key="btn_start_new_game",
            use_container_width=True,
            on_click=state_manager.start_new_game,
        )
