import streamlit as st

def initialize_state():
    if "board" not in st.session_state:
        # Game state
        st.session_state.board = [["" for _ in range(5)] for _ in range(6)]
        st.session_state.current_row = 0
        st.session_state.current_col = 0
        
        # Personal stats
        st.session_state.player_name = "Guest"
        st.session_state.streak = 3
        st.session_state.longest_streak = 8
        st.session_state.games_played = 10
        st.session_state.wins = 7
        
        # Profile settings
        st.session_state.saved_profiles = ["Guest", "Alice", "Bob"]
        st.session_state.profile_mode = "view" 
        
        # Global Leaderboard (Mock data)
        st.session_state.global_leaderboard = [
            {"Rank": "🥇 1", "Player": "Alice", "Played": 42, "Wins": 38, "Win %": "90%", "Longest Streak": 12},
            {"Rank": "🥈 2", "Player": "Bob", "Played": 35, "Wins": 30, "Win %": "85%", "Longest Streak": 5},
            {"Rank": "🥉 3", "Player": "Charlie", "Played": 20, "Wins": 15, "Win %": "75%", "Longest Streak": 2},
        ]
        
        # View routing
        st.session_state.current_view = "game"