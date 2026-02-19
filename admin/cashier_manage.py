import importlib

import streamlit as st

# Reload firebase_db to avoid Streamlit module caching issues during development
import data.firebase_db as firebase_db
from admin.participant_list_component import render_participant_list_table

firebase_db = importlib.reload(firebase_db)


def _lang_label(lang: str) -> str:
    s = str(lang)
    if "English" in s and "Japanese" in s:
        return "EN+JP"
    if "English" in s:
        return "EN"
    if "Japanese" in s:
        return "JP"
    return s


st.title("受付ツール / Front Desk Tools")
st.caption("Manual check-in + Participant list (with table number). / 手動チェックイン + 参加者一覧（テーブル番号付き）")

state = firebase_db.get_event_state()
round_no = int(state.get("current_round") or 0)
started = bool(state.get("started"))
st.caption(f"Round={round_no} | Started={started}")

st.divider()

st.subheader("Manual check-in (no phone) / 手動チェックイン（スマホなし）")
with st.form("cashier_manual_checkin_form"):
    manual_name = st.text_input("Name / 名前")
    manual_language = st.selectbox("Language / 言語", ["English", "Japanese"])
    submitted = st.form_submit_button("Add / 追加", type="primary")
    if submitted:
        if not manual_name.strip():
            st.error("Please enter a name. / 名前を入力してください。")
        else:
            user = firebase_db.admin_add_participant(manual_name, manual_language, created_by_role="cashier")
            table_info = user.table_number or "-"
            st.success(f"Added / 追加しました: {user.name} | Table: {table_info}")

st.divider()

participants = firebase_db.get_all_participants()
active_participants = firebase_db.get_active_participants()
render_participant_list_table(participants, active_participants, default_only_checked_in=True)

