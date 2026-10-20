import streamlit as st
import state_manager
from views import game_view, profile_view, stats_view
import requests

# --- 1. CONFIGURATION & CSS INJECTION ---
st.set_page_config(page_title="Wordle", page_icon="🧩", layout="centered")

with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- 2. STATE INITIALIZATION ---
state_manager.initialize_state()

# --- 3. DEBUG SIDEBAR (DEVELOPER TOOLS) ---
with st.sidebar:
    st.title("🛠️ Debug Menu")
    st.markdown("---")

    target = st.session_state.get('target_word', 'NOT SET')
    st.markdown(f"**Target Word:** <span style='color: #4CAF50; font-family: monospace; font-size: 1.2em;'>{target}</span>", unsafe_allow_html=True)
    
    st.markdown("---")
    
    if st.button("🔄 Generate new word (API)"):
        try:
            res = requests.get("http://127.0.0.1:8000/api/v1/game/start")
            if res.status_code == 200:
                st.session_state.target_word = res.json().get("target_word")
                st.session_state.board = [["" for _ in range(5)] for _ in range(6)]
                st.session_state.current_row = 0
                st.session_state.current_col = 0
                st.session_state.game_won = False
                st.rerun() 
        except requests.exceptions.ConnectionError:
            st.error("Backend is unreachable!")

# --- 4. NAVIGATION LOGIC ---
def toggle_view(view_name):
    if st.session_state.current_view == view_name:
        st.session_state.current_view = "game"
    else:
        st.session_state.current_view = view_name
        st.session_state.profile_mode = "view"

# --- 5. HEADER & TOP BAR ---
nav1, nav2, nav3, nav4 = st.columns([1, 1, 4, 2])

with nav1:
    st.button("👤", use_container_width=True, on_click=toggle_view, args=("profile",))
with nav2:
    st.button("📊", use_container_width=True, on_click=toggle_view, args=("stats",))
with nav3:
    st.markdown("<h2 style='text-align: center; margin-top: -15px; padding-bottom: 5px;'>Wordle</h2>", unsafe_allow_html=True)
with nav4:
    st.markdown(f"<div style='text-align: right; margin-top: 5px; font-size: 18px; font-weight: bold;'>🔥 Streak: {st.session_state.streak}</div>", unsafe_allow_html=True)

st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# --- 6. VIEW ROUTER ---
if st.session_state.current_view == "game":
    game_view.render()
elif st.session_state.current_view == "profile":
    profile_view.render()
elif st.session_state.current_view == "stats":
    stats_view.render()