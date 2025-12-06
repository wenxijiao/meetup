import streamlit as st
from streamlit_autorefresh import st_autorefresh
import time
from data.firebase_db import get_my_status, logout_user

current_id = st.session_state.u_id
if not current_id:
    # 确实没有任何 ID，才显示未登录
    st.error("You are not Checked In. Please log in again.")
    if st.button("Go to Login Page"):
        st.session_state.role = "Select your role"
        st.rerun()
else:
    try:
        current_participant = get_my_status(current_id)

        if current_participant.status == "Not Checked In":
            st.error("You are not Checked In. Please log in again.")
            if st.button("Go to Login Page"):
                st.session_state.role = "Select your role"
                st.rerun()
        else:
            st.header("Participant Page")

            name = current_participant.name

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"👤 **{name}**")
            with col2:
                if st.button("ログアウト / Logout", type="secondary", use_container_width=True):
                    logout_user(current_id)
                    st.session_state.role = "Select your role"
                    st.rerun()

            table_number = current_participant.table_number

            st.divider()

            if table_number:
                st.markdown(f"""
                <div style="
                    text-align: center; 
                    padding: 30px; 
                    background-color: #d4edda; 
                    border-radius: 15px;
                    margin-bottom: 20px;
                    border: 2px solid #c3e6cb;">
                    <p style="color: #155724; margin: 0;">Your Table</p>
                    <h1 style="color: #155724; font-size: 80px; margin: 0;">{table_number}</h1>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("The event has not started yet. Please wait for the organizer to begin...")
                st.caption("イベントはまだ開始していません、主催者が開始するまでお待ちください...")

        st_autorefresh(interval=10_000, key="auto_refresh")

    except ValueError:
        st.session_state.role = "Select your role"
        st.rerun()
        