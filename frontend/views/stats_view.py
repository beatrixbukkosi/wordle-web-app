import streamlit as st

def render():
    st.markdown(f"<h3 class='center-text'>📊 {st.session_state.player_name}'s Statistics</h3>", unsafe_allow_html=True)
    
    win_rate = f"{(st.session_state.wins / st.session_state.games_played * 100):.0f}%" if st.session_state.games_played > 0 else "0%"
    
    stats_html = f"""
    <div class='stats-container'>
        <div class='stat-box'>
            <div class='stat-label'>Played</div>
            <div class='stat-value'>{st.session_state.games_played}</div>
        </div>
        <div class='stat-box'>
            <div class='stat-label'>Wins</div>
            <div class='stat-value'>{st.session_state.wins}</div>
        </div>
        <div class='stat-box'>
            <div class='stat-label'>Win %</div>
            <div class='stat-value'>{win_rate}</div>
        </div>
        <div class='stat-box'>
            <div class='stat-label'>Longest Streak</div>
            <div class='stat-value'>{st.session_state.longest_streak}</div>
        </div>
    </div>
    """
    st.markdown(stats_html, unsafe_allow_html=True)
    
    st.divider()
    
    st.markdown("<h3 class='center-text'>🌍 Global Leaderboard</h3>", unsafe_allow_html=True)
    
    current_player_data = {
        "Rank": "-", 
        "Player": st.session_state.player_name, 
        "Played": st.session_state.games_played, 
        "Wins": st.session_state.wins, 
        "Win %": win_rate,
        "Longest Streak": st.session_state.longest_streak
    }
    
    display_data = st.session_state.global_leaderboard + [current_player_data]
    st.dataframe(display_data, use_container_width=True, hide_index=True)