import streamlit as st

def set_profile_mode(mode):
    st.session_state.profile_mode = mode

def save_profile():
    new_name = st.session_state.name_input.strip()
    if new_name:
        st.session_state.player_name = new_name
        if new_name not in st.session_state.saved_profiles:
            st.session_state.saved_profiles.append(new_name)
    st.session_state.profile_mode = "view"

def apply_switch_profile():
    st.session_state.player_name = st.session_state.profile_selectbox
    st.session_state.profile_mode = "view"

def render():
    st.markdown("<h3 class='center-text'>👤 Player Profile</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.profile_mode == "view":
        st.markdown(f"<h3 class='center-text'><span class='gray-label'>Name:</span> <span class='profile-name-highlight'>{st.session_state.player_name}</span></h3>", unsafe_allow_html=True)
        st.markdown("<br>", unsafe_allow_html=True)
        
        btn_col1, btn_col2, btn_col3 = st.columns(3)
        btn_col1.button("✏️ Edit", use_container_width=True, on_click=set_profile_mode, args=("edit",))
        btn_col2.button("🔄 Switch", use_container_width=True, on_click=set_profile_mode, args=("switch",))
        btn_col3.button("➕ New", use_container_width=True, on_click=set_profile_mode, args=("new",))
        
    elif st.session_state.profile_mode in ["edit", "new"]:
        prompt = "Edit your name:" if st.session_state.profile_mode == "edit" else "Enter new profile name:"
        default_val = st.session_state.player_name if st.session_state.profile_mode == "edit" else ""
        
        st.text_input(prompt, value=default_val, key="name_input", max_chars=15)
        
        col1, col2 = st.columns(2)
        col1.button("💾 Save", use_container_width=True, on_click=save_profile)
        col2.button("❌ Cancel", use_container_width=True, on_click=set_profile_mode, args=("view",))
        
    elif st.session_state.profile_mode == "switch":
        st.selectbox("Select a profile:", st.session_state.saved_profiles, key="profile_selectbox")
        
        col1, col2 = st.columns(2)
        col1.button("✅ Select", use_container_width=True, on_click=apply_switch_profile)
        col2.button("❌ Cancel", use_container_width=True, on_click=set_profile_mode, args=("view",))