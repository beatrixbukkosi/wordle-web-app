import os
import requests
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


def render():
    player_id = st.session_state.get("player_id")
    if player_id is None:
        st.error("Player statistics are unavailable until the backend profile is connected.")
        return

    try:
        stats_response = requests.get(
            f"{BACKEND_URL}/api/v1/users/{player_id}/stats",
            timeout=5,
        )
        leaderboard_response = requests.get(
            f"{BACKEND_URL}/api/v1/leaderboard",
            timeout=5,
        )
        if stats_response.status_code != 200:
            st.error(
                f"Unable to load player statistics (HTTP {stats_response.status_code})."
            )
            return
        if leaderboard_response.status_code != 200:
            st.error(
                f"Unable to load the leaderboard "
                f"(HTTP {leaderboard_response.status_code})."
            )
            return
    except requests.exceptions.RequestException:
        st.error("Unable to reach the backend for player statistics.")
        return

    stats = stats_response.json()
    leaderboard = leaderboard_response.json()
    win_rate = f"{stats['win_rate']:.0f}%"
    st.subheader(f"📊 {stats['username']}'s Statistics")

    stats_html = f"""
    <div class='stats-container'>
        <div class='stat-box'>
            <div class='stat-label'>Played</div>
            <div class='stat-value'>{stats['games_played']}</div>
        </div>
        <div class='stat-box'>
            <div class='stat-label'>Wins</div>
            <div class='stat-value'>{stats['games_won']}</div>
        </div>
        <div class='stat-box'>
            <div class='stat-label'>Win %</div>
            <div class='stat-value'>{win_rate}</div>
        </div>
        <div class='stat-box'>
            <div class='stat-label'>Longest Streak</div>
            <div class='stat-value'>{stats['max_streak']}</div>
        </div>
    </div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)

    st.divider()

    st.subheader("🌍 Global Leaderboard")
    display_data = [
        {
            "Rank": entry["rank"],
            "Player": entry["username"],
            "Played": entry["games_played"],
            "Wins": entry["games_won"],
            "Win %": f"{entry['win_rate']:.0f}%",
            "Longest Streak": entry["max_streak"],
        }
        for entry in leaderboard
    ]
    st.dataframe(display_data, use_container_width=True, hide_index=True)