import streamlit as st

import state_manager


def set_profile_mode(mode):
    st.session_state.profile_mode = mode


def begin_edit_profile():
    st.session_state.profile_original_name = st.session_state.player_name
    st.session_state.profile_mode = "edit"


def save_profile():
    new_name = st.session_state.name_input.strip()
    if st.session_state.profile_mode == "edit":
        saved = state_manager.rename_active_profile(new_name)
    else:
        state_manager.select_profile(new_name)
        saved = st.session_state.get("player_id") is not None
    if saved:
        st.session_state.profile_mode = "view"


def confirm_delete_profile():
    if state_manager.delete_active_profile():
        st.session_state.profile_mode = "view"


def apply_switch_profile():
    state_manager.select_profile(st.session_state.profile_selectbox)
    if st.session_state.get("player_id") is not None:
        state_manager.start_new_game()
    st.session_state.profile_mode = "view"


def render():
    state_manager.load_saved_profiles()
    if st.session_state.get("backend_error"):
        st.error(st.session_state.backend_error)
    st.markdown("<h3 class='center-text'>👤 Player Profile</h3>", unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)
    
    if st.session_state.profile_mode == "view":
        if st.session_state.player_name:
            st.markdown(f"<h3 class='center-text'><span class='gray-label'>Name:</span> <span class='profile-name-highlight'>{st.session_state.player_name}</span></h3>", unsafe_allow_html=True)
            st.markdown("<br>", unsafe_allow_html=True)
            actions = st.columns(4 if st.session_state.saved_profiles else 3)
            actions[0].button("✏️ Edit", use_container_width=True, on_click=begin_edit_profile)
            if st.session_state.saved_profiles:
                actions[1].button("🔄 Switch", use_container_width=True, on_click=set_profile_mode, args=("switch",))
            actions[2 if st.session_state.saved_profiles else 1].button(
                "➕ New",
                use_container_width=True,
                on_click=set_profile_mode,
                args=("new",),
            )
            actions[3 if st.session_state.saved_profiles else 2].button(
                "🗑️ Delete",
                use_container_width=True,
                on_click=set_profile_mode,
                args=("delete_confirm",),
            )
        else:
            st.info("No active profile. Create one to save your statistics.")
            st.button(
                "➕ Új profil",
                use_container_width=True,
                on_click=set_profile_mode,
                args=("new",),
            )
        
    elif st.session_state.profile_mode in ["edit", "new"]:
        prompt = "Edit your name:" if st.session_state.profile_mode == "edit" else "Enter new profile name:"
        default_val = st.session_state.player_name if st.session_state.profile_mode == "edit" else ""
        
        st.text_input(prompt, value=default_val, key="name_input", max_chars=15)
        
        col1, col2 = st.columns(2)
        col1.button("💾 Save", use_container_width=True, on_click=save_profile)
        col2.button("❌ Cancel", use_container_width=True, on_click=set_profile_mode, args=("view",))

    elif st.session_state.profile_mode == "delete_confirm":
        st.warning(
            f"Delete the profile '{st.session_state.player_name}'? "
            "Its statistics will be permanently deleted. Existing games will be kept "
            "without a player association."
        )
        col1, col2 = st.columns(2)
        col1.button(
            "🗑️ Delete profile",
            use_container_width=True,
            on_click=confirm_delete_profile,
        )
        col2.button("❌ Cancel", use_container_width=True, on_click=set_profile_mode, args=("view",))

    elif st.session_state.profile_mode == "switch":
        st.selectbox("Select a profile:", st.session_state.saved_profiles, key="profile_selectbox")
        
        col1, col2 = st.columns(2)
        col1.button("✅ Select", use_container_width=True, on_click=apply_switch_profile)
        col2.button("❌ Cancel", use_container_width=True, on_click=set_profile_mode, args=("view",))