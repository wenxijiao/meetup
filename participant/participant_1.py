import streamlit as st
from streamlit_autorefresh import st_autorefresh
from data.firebase_db import get_my_status, logout_user

current_id = st.session_state.u_id
if not current_id:
    st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
    if st.button("ログインへ / Go to Login"):
        st.session_state.role = "Select your role"
        st.rerun()
else:
    try:
        current_participant = get_my_status(current_id)

        if current_participant.status == "Not Checked In":
            st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
            if st.button("ログインへ / Go to Login"):
                st.session_state.role = "Select your role"
                st.rerun()
        else:
            st.header("参加者ページ / Participant")

            name = current_participant.name

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"👤 **{name}**")
            with col2:
                if st.button("ログアウト / Logout", type="secondary", width="stretch"):
                    logout_user(current_id)
                    # Keep cookie for this event; session role is reset.
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
                    <p style="color: #155724; margin: 0;">あなたのテーブル / Your Table</p>
                    <h1 style="color: #155724; font-size: 80px; margin: 0;">{table_number}</h1>
                </div>
                """, unsafe_allow_html=True)
            else:
                st.caption("イベントはまだ開始していません。主催者が開始するまでお待ちください。")
                st.caption("The event has not started yet. Please wait for the organizer to begin...")

        # 桌号每 30 分钟才会变化一次，轮询不需要太频繁；降低读取频率也能省 Firestore 成本。
        st_autorefresh(interval=30_000, key="auto_refresh")

    except ValueError:
        st.session_state.role = "Select your role"
        st.rerun()
        