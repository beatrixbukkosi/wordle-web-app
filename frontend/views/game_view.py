import streamlit as st

def handle_key_press(key):
    row = st.session_state.current_row
    col = st.session_state.current_col

    if key == "⌫":
        if col > 0:
            st.session_state.current_col -= 1
            st.session_state.board[row][st.session_state.current_col] = ""
            
    elif key == "SUBMIT":
        if col == 5:
            st.toast("Submitting guess to backend...", icon="🚀")
            if st.session_state.current_row < 5:
                st.session_state.current_row += 1
                st.session_state.current_col = 0
                
    else:
        if col < 5 and row < 6:
            st.session_state.board[row][col] = key
            st.session_state.current_col += 1

def render():
    # Render Game Board using CSS classes
    grid_html = "<div class='wordle-grid'>"
    for row in range(6):
        grid_html += "<div class='wordle-row'>"
        for col in range(5):
            letter = st.session_state.board[row][col]
            # Dynamic border color depending on content
            border_color = "#878a8c" if letter else "#d3d6da"
            grid_html += f"<div class='wordle-box' style='border-color: {border_color};'>{letter}</div>"
        grid_html += "</div>"
    grid_html += "</div>"

    st.markdown(grid_html, unsafe_allow_html=True)

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
                on_click=handle_key_press, 
                args=(key,)
            )

    st.markdown("<div style='margin-top: 15px;'></div>", unsafe_allow_html=True)

    # Render Submit Button
    can_submit = (st.session_state.current_col == 5)
    _, center_col, _ = st.columns([1, 2, 1])
    center_col.button(
        "SUBMIT GUESS", 
        use_container_width=True, 
        disabled=not can_submit, 
        on_click=handle_key_press, 
        args=("SUBMIT",)
    )