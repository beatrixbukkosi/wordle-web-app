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

KEY_COLOR_PRIORITY: dict[str, int] = {
    "GRAY": 1,
    "YELLOW": 2,
    "GREEN": 3,
}

KEYBOARD_ROWS: list[list[str]] = [
    ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
    ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
    ["Z", "X", "C", "V", "B", "N", "M", "⌫"],
]


def get_keyboard_colors(
    board: list[list[str]], row_colors: list[list[str | None]]
) -> dict[str, str]:
    """Returns the strongest evaluated color for each guessed letter."""
    keyboard_colors: dict[str, str] = {}
    for letters, colors in zip(board, row_colors):
        for letter, color in zip(letters, colors):
            if not letter or color not in KEY_COLOR_PRIORITY:
                continue

            current_color = keyboard_colors.get(letter)
            if (
                current_color is None
                or KEY_COLOR_PRIORITY[color] > KEY_COLOR_PRIORITY[current_color]
            ):
                keyboard_colors[letter] = color

    return keyboard_colors


def get_keyboard_styles(keyboard_colors: dict[str, str]) -> str:
    """Builds CSS targeting evaluated keys in old and new Streamlit layouts."""
    styles: list[str] = []
    for key, color in keyboard_colors.items():
        tile_color = TILE_COLORS[color]
        styles.append(
            f".st-key-btn_{key} button {{ "
            f"background-color: {tile_color} !important; "
            f"border-color: {tile_color} !important; "
            "color: white !important; }"
        )

    for row_keys in KEYBOARD_ROWS:
        column_count = len(row_keys)
        for key_index, key in enumerate(row_keys):
            color = keyboard_colors.get(key)
            if color is None:
                continue

            tile_color = TILE_COLORS[color]
            row_selector = (
                "[data-testid='stHorizontalBlock']:has("
                f"> [data-testid='column']:nth-child({column_count})"
                f"):not(:has(> [data-testid='column']:nth-child({column_count + 1})))"
            )
            styles.append(
                f"{row_selector} > [data-testid='column']:nth-child({key_index + 1}) "
                f"[data-testid='stButton'] button {{ "
                f"background-color: {tile_color} !important; "
                f"border-color: {tile_color} !important; "
                "color: white !important; }"
            )
    return "".join(styles)


def get_submit_button_style(guess_is_valid: bool | None) -> str:
    """Returns the submit button color for the current full guess."""
    if guess_is_valid is None:
        return ""

    color = "#6aaa64" if guess_is_valid else "#d9534f"
    declarations = (
        f"background-color: {color} !important; "
        f"border-color: {color} !important; "
        "color: white !important;"
    )
    return (
        f"button[kind='primary'] {{ {declarations} }}"
        "button[kind='primary']:disabled { cursor: not-allowed !important; }"
    )


def validate_current_guess() -> None:
    """Checks the current five-letter guess without consuming a game attempt."""
    row = st.session_state.current_row
    guess = "".join(st.session_state.board[row]).upper()
    try:
        response = requests.post(
            f"{BACKEND_URL}/api/v1/game/word-validation",
            json={"guess": guess},
            timeout=5,
        )
        if response.status_code == 200:
            st.session_state.guess_is_valid = response.json().get("is_valid", False)
            st.session_state.backend_error = None
        else:
            st.session_state.guess_is_valid = None
            st.session_state.backend_error = (
                f"Error validating guess with server (HTTP {response.status_code})."
            )
    except requests.exceptions.RequestException:
        st.session_state.guess_is_valid = None
        st.session_state.backend_error = "Backend is unreachable!"


def submit_guess() -> None:
    """Submits the current row guess to the backend and handles evaluation results."""
    if st.session_state.get("game_won", False) or st.session_state.get("game_lost", False):
        return

    row = st.session_state.current_row
    if (
        st.session_state.current_col != 5
        or not st.session_state.get("guess_is_valid", False)
    ):
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
                st.session_state.guess_is_valid = False
                return

            colors = data.get("colors") or [None] * len(guess_word)
            st.session_state.row_colors[row] = colors
            st.session_state.backend_error = None

            is_winning = data.get("is_winning", False) or data.get("game_status") == "WON"
            if is_winning:
                st.session_state.game_won = True
                st.session_state.game_status = "WON"
            else:
                remaining = data.get("remaining_attempts")
                status = data.get("game_status")
                is_lost = status == "LOST" or remaining == 0 or (row >= 5 and remaining is None)
                if is_lost:
                    st.session_state.game_lost = True
                    st.session_state.game_status = "LOST"
                else:
                    if st.session_state.current_row < 5:
                        st.session_state.current_row += 1
                        st.session_state.current_col = 0
                        st.session_state.guess_is_valid = None
        else:
            st.session_state.backend_error = (
                f"Error validating guess with server (HTTP {response.status_code})."
            )
    except requests.exceptions.RequestException:
        st.session_state.backend_error = "Backend is unreachable!"


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
            st.session_state.guess_is_valid = None
    elif key == "SUBMIT":
        submit_guess()
    else:
        if col < 5 and row < 6:
            st.session_state.board[row][col] = key
            st.session_state.current_col += 1
            if st.session_state.current_col == 5:
                validate_current_guess()
            else:
                st.session_state.guess_is_valid = None


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
    keyboard_colors = get_keyboard_colors(
        st.session_state.board, st.session_state.row_colors
    )
    keyboard_styles = get_keyboard_styles(keyboard_colors)
    if keyboard_styles:
        st.markdown(f"<style>{keyboard_styles}</style>", unsafe_allow_html=True)

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
    guess_is_valid = st.session_state.get("guess_is_valid")
    invalid_guess = can_submit and guess_is_valid is False
    submit_button_style = get_submit_button_style(
        guess_is_valid if can_submit else None
    )
    if submit_button_style:
        st.markdown(f"<style>{submit_button_style}</style>", unsafe_allow_html=True)
    _, center_col, _ = st.columns([1, 2, 1])

    with center_col:
        st.button(
            "SUBMIT GUESS",
            key="btn_submit_guess",
            type="primary",
            use_container_width=True,
            disabled=not can_submit or invalid_guess,
            on_click=submit_guess,
            help="Invalid word" if invalid_guess else None,
        )
        st.markdown("<div style='margin-top: 10px;'></div>", unsafe_allow_html=True)
        st.button(
            "🔄 Start New Game",
            key="btn_start_new_game",
            use_container_width=True,
            on_click=state_manager.start_new_game,
        )
