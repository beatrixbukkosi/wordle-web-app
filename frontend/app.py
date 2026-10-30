"""Main entry point for Streamlit Wordle Single-Page Application."""

from pathlib import Path
import streamlit as st

import state_manager
from views import game_view, profile_view, stats_view

# --- 1. CONFIGURATION & CSS INJECTION ---
st.set_page_config(page_title="Wordle", page_icon="🧩", layout="centered")

css_path = Path(__file__).parent / "style.css"
if css_path.exists():
    with open(css_path, encoding="utf-8") as style_file:
        st.markdown(f"<style>{style_file.read()}</style>", unsafe_allow_html=True)

# --- 2. STATE INITIALIZATION ---
state_manager.initialize_state()

# --- 3. DEBUG SIDEBAR (DEVELOPER TOOLS - READ-ONLY DEBUG INFO) ---
with st.sidebar:
    st.title("🛠️ Debug Menu")
    st.markdown("---")

    active_session = st.session_state.get("session_id", "NOT SET")
    st.markdown(
        f"**Session ID:**<br><span style='font-family: monospace; font-size: 0.85em; word-break: break-all;'>{active_session}</span>",
        unsafe_allow_html=True,
    )

    current_status = st.session_state.get("game_status", "IN_PROGRESS")
    st.markdown(f"**Game Status:** `{current_status}`")
    st.caption("ℹ️ Secret word is securely logged to the backend console.")

    if st.session_state.get("backend_error"):
        st.error(st.session_state.backend_error)


# --- 4. NAVIGATION HANDLER ---
def toggle_view(view_name: str) -> None:
    """Toggles view navigation between game, profile, and stats."""
    if st.session_state.current_view == view_name:
        st.session_state.current_view = "game"
    else:
        st.session_state.current_view = view_name
        st.session_state.profile_mode = "view"


# --- 5. HEADER & TOP BAR ---
nav1, nav2, nav3, nav4 = st.columns([1, 1, 4, 2])

with nav1:
    st.button("👤", help="Profile", use_container_width=True, on_click=toggle_view, args=("profile",))
with nav2:
    st.button("📊", help="Statistics", use_container_width=True, on_click=toggle_view, args=("stats",))
with nav3:
    st.markdown(
        "<h2 style='text-align: center; margin-top: -15px; padding-bottom: 5px;'>Wordle</h2>",
        unsafe_allow_html=True,
    )
with nav4:
    current_streak = st.session_state.get("current_streak", 0)
    st.markdown(
        f"<div style='text-align: right; margin-top: 5px; font-size: 18px; font-weight: bold;'>🔥 Streak: {current_streak}</div>",
        unsafe_allow_html=True,
    )

st.markdown("<hr style='margin-top: 0px; margin-bottom: 15px;'>", unsafe_allow_html=True)

# --- 6. VIEW ROUTER ---
if st.session_state.current_view == "game":
    game_view.render()
elif st.session_state.current_view == "profile":
    profile_view.render()
elif st.session_state.current_view == "stats":
    stats_view.render()
