import streamlit as st
import pandas as pd
import time
from data.firebase_db import get_all_participants, logout_user, get_active_participants
from admin.participant_list_component import render_participant_list_table

st.title("📊 Live Data Dashboard / ダッシュボード")
st.caption("Real-time monitoring of participants and stats. / 参加者と統計をリアルタイム表示。")

if st.button("🔄 Refresh Data"):
    st.rerun()

participants = get_all_participants()
active_participants = get_active_participants()
total_count = len(active_participants)

en_count = sum(1 for p in active_participants if "English" in str(p.language))
jp_count = sum(1 for p in active_participants if "Japanese" in str(p.language))

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Total Participants", total_count)
with col2:
    st.metric("🇬🇧 English Speakers", en_count)
with col3:
    st.metric("🇯🇵 Japanese Speakers", jp_count)

st.divider()

render_participant_list_table(participants, active_participants, default_only_checked_in=False)

if total_count > 0:
    st.divider()
    st.subheader("🚫 Manage Users (Logout)")
    
    active_users = active_participants
    
    if active_users:
        col_kick_sel, col_kick_btn = st.columns([3, 1])
        
        with col_kick_sel:
            user_to_kick = st.selectbox(
                "Select a user to force logout:",
                options=active_users,
                format_func=lambda p: f"{p.name} (Table: {p.table_number or '-'})"
            )
            
        with col_kick_btn:
            st.write("")
            st.write("") 
            if st.button("Kick User 👢", type="primary"):
                if user_to_kick:
                    try:
                        logout_user(user_to_kick.id)
                        st.toast(f"User {user_to_kick.name} has been logged out!", icon="✅")
                        time.sleep(1)
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error: {e}")
    else:
        st.info("Everyone is currently logged out.")

if total_count > 0:
    st.divider()
    st.subheader("📈 Language Distribution")
    chart_data = pd.DataFrame({
        "Language": ["English", "Japanese"],
        "Count": [en_count, jp_count]
    })
    st.bar_chart(chart_data, x="Language", y="Count", color="#FF4B4B")
