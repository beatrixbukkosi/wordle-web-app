import streamlit as st
import state_manager
from views import game_view, profile_view, stats_view

# --- 1. CONFIGURATION & CSS INJECTION ---
st.set_page_config(page_title="Wordle", page_icon="🧩", layout="centered")

# Load CSS file
with open("style.css") as f:
    st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

# --- 2. STATE INITIALIZATION ---
state_manager.initialize_state()

# --- 3. NAVIGATION LOGIC ---
def toggle_view(view_name):
    if st.session_state.current_view == view_name:
        st.session_state.current_view = "game"
    else:
        st.session_state.current_view = view_name
        st.session_state.profile_mode = "view"

# --- 4. HEADER & TOP BAR ---
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

# --- 5. VIEW ROUTER ---
if st.session_state.current_view == "game":
    game_view.render()
elif st.session_state.current_view == "profile":
    profile_view.render()
elif st.session_state.current_view == "stats":
    stats_view.render()