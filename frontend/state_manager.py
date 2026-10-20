# state_manager.py
import streamlit as st
import requests

def initialize_state():
    if "board" not in st.session_state:
        st.session_state.board = [["" for _ in range(5)] for _ in range(6)]
        st.session_state.current_row = 0
        st.session_state.current_col = 0
        
        try:
            response = requests.get("http://127.0.0.1:8000/api/v1/game/start")
            if response.status_code == 200:
                st.session_state.target_word = response.json().get("target_word")
            else:
                st.session_state.target_word = "ERROR"
        except requests.exceptions.ConnectionError:
            st.session_state.target_word = "BACKEND_OFFLINE"
            
        st.session_state.player_name = "Guest"
        st.session_state.streak = 3
        st.session_state.longest_streak = 8
        st.session_state.games_played = 10
        st.session_state.wins = 7
        
        st.session_state.saved_profiles = ["Guest", "Alice", "Bob"]
        st.session_state.profile_mode = "view" 
        
        st.session_state.global_leaderboard = [
            {"Rank": "🥇 1", "Player": "Alice", "Played": 42, "Wins": 38, "Win %": "90%", "Longest Streak": 12},
            {"Rank": "🥈 2", "Player": "Bob", "Played": 35, "Wins": 30, "Win %": "85%", "Longest Streak": 5},
        ]
        st.session_state.current_view = "game"