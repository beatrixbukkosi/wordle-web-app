import streamlit as st
import requests

TILE_COLORS = {
    "GREEN": "#6aaa64",
    "YELLOW": "#c9b458",
    "GRAY": "#787c7e",
}


def submit_guess():
    if st.session_state.get("game_won", False):
        return

    row = st.session_state.current_row
    if st.session_state.current_col != 5:
        return

    guess_word = "".join(st.session_state.board[row]).upper()
    target_word = st.session_state.get("target_word", "").upper()

    try:
        response = requests.post(
            "http://127.0.0.1:8000/api/v1/game/validate",
            json={"guess": guess_word, "target_word": target_word},
            timeout=5
        )
        if response.status_code == 200:
            data = response.json()
            if not data.get("is_valid", False):
                st.toast(f"'{guess_word}' is not a valid word!", icon="⚠️")
                return

            if data.get("is_winning", False):
                st.session_state.game_won = True
                st.toast("Congratulations! That's the winning word! 🎉", icon="🏆")
            else:
                st.toast(f"'{guess_word}' is a valid guess!", icon="✅")

            st.session_state.row_colors[row] = data.get("colors") or [None] * len(guess_word)

            if not st.session_state.game_won and st.session_state.current_row < 5:
                st.session_state.current_row += 1
                st.session_state.current_col = 0
        else:
            st.toast("Error validating guess with server.", icon="🚨")
    except requests.exceptions.RequestException:
        st.toast("Backend is unreachable!", icon="🚨")

def handle_key_press(key):
    if st.session_state.get("game_won", False):
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

def render():
    grid_html = "<div class='wordle-grid'>"
    for row in range(6):
        grid_html += "<div class='wordle-row'>"
        for col in range(5):
            letter = st.session_state.board[row][col]
            color = st.session_state.row_colors[row][col]
            if color:
                tile_color = TILE_COLORS[color]
                style = f"background-color: {tile_color}; border-color: {tile_color}; color: white;"
            else:
                border_color = "#878a8c" if letter else "#d3d6da"
                style = f"border-color: {border_color};"
            grid_html += f"<div class='wordle-box' style='{style}'>{letter}</div>"
        grid_html += "</div>"
    grid_html += "</div>"

    st.markdown(grid_html, unsafe_allow_html=True)

    game_won = st.session_state.get("game_won", False)

    # Render Keyboard
    keyboard_rows = [
        ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
        ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
        ["Z", "X", "C", "V", "B", "N", "M", "⌫"]
    ]

    for row in keyboard_rows:
        cols = st.columns(len(row))
        for i, key in enumerate(row):
            cols[i].button(
                key, 
                key=f"btn_{key}", 
                use_container_width=True, 
                disabled=game_won,
                on_click=handle_key_press, 
                args=(key,)
            )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Render Submit Button
    can_submit = (st.session_state.current_col == 5 and not game_won)
    _, center_col, _ = st.columns([1, 2, 1])
    center_col.button(
        "SUBMIT GUESS", 
        use_container_width=True, 
        disabled=not can_submit, 
        on_click=submit_guess
    )