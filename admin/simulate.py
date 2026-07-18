import time

import pandas as pd
import streamlit as st

from data.firebase_db import (
    clear_test_participants,
    create_test_participants,
    get_active_participants,
    get_event_state,
    get_test_participants,
)

st.title("🧪 Simulator / テスト")
st.caption(
    "Seed fake participants so you can test rounds and activities alone. "
    "/ 一人でラウンドや活動を試すための仮想参加者を作成します。"
)
st.warning(
    "This writes to today's live event data. Clear test users before a real event. "
    "/ 本日の本番データに書き込みます。実際のイベント前に必ずテストユーザーを削除してください。",
    icon="⚠️",
)

state = get_event_state()
active_participants = get_active_participants()
test_users = get_test_participants()
active_test_users = [u for u in test_users if u.get("status") == "Checked In"]

col1, col2, col3 = st.columns(3)
with col1:
    st.metric("Active participants", len(active_participants))
with col2:
    st.metric("Test users", len(test_users))
with col3:
    st.metric("Current round", int(state.get("current_round") or 0))

st.divider()

st.subheader("1. Seed test users / 仮想参加者を作成")
st.caption("Created as checked-in, so rounds can include them right away. / 作成後すぐチェックイン済みになります。")

with st.form("seed_test_users_form"):
    c1, c2 = st.columns(2)
    with c1:
        n_en = st.number_input("🇬🇧 English", min_value=0, max_value=100, value=5, step=1)
    with c2:
        n_jp = st.number_input("🇯🇵 Japanese", min_value=0, max_value=100, value=5, step=1)
    seed_submitted = st.form_submit_button("Seed / 作成", type="primary", width="stretch")

if seed_submitted:
    if int(n_en) + int(n_jp) == 0:
        st.error("Enter at least one user. / 1人以上を指定してください。")
    else:
        created = create_test_participants(int(n_en), int(n_jp))
        st.toast(f"Created {len(created)} test users.", icon="✅")
        time.sleep(0.6)
        st.rerun()

st.subheader("2. Run the event / ラウンド操作")
st.caption(
    "Start a round and timer from Event Operations as usual; the dashboard shows the result. "
    "/ 通常どおり Event Operations でラウンドとタイマーを開始してください。"
)
link_col1, link_col2 = st.columns(2)
with link_col1:
    st.page_link("admin/admin_1.py", label="Event Operations", icon=":material/tune:")
with link_col2:
    st.page_link("admin/admin_2.py", label="Live Dashboard", icon=":material/monitoring:")

st.subheader("3. View as a test participant / 参加者ビュー")
if not active_test_users:
    st.info("Seed test users first. / まずテストユーザーを作成してください。")
else:
    view_user = st.selectbox(
        "Test user / テストユーザー",
        options=active_test_users,
        format_func=lambda u: f"{u.get('name')}  (Table: {u.get('table_number') or '-'})",
    )
    if st.button("View as this participant / この参加者として見る", width="stretch"):
        st.session_state.u_id = view_user.get("id")
        st.session_state.name = view_user.get("name")
        st.session_state.role = "Participant"
        st.rerun()
    st.caption(
        "To return: sidebar → ログアウト / Log out, then log in again from the Staff tab. "
        "/ 戻るにはサイドバーからログアウトし、Staffタブで再ログインしてください。"
    )

st.divider()

st.subheader("🧹 Clean up / テストユーザー削除")
if test_users:
    with st.expander(f"Current test users ({len(test_users)})", expanded=False):
        df = pd.DataFrame(
            [
                {
                    "Name": u.get("name"),
                    "Language": u.get("language"),
                    "Table": u.get("table_number") or "-",
                    "Status": u.get("status"),
                }
                for u in test_users
            ]
        )
        st.dataframe(df, width="stretch", hide_index=True)

    if st.button(f"Clear {len(test_users)} test users / 全テストユーザーを削除", width="stretch"):
        deleted = clear_test_participants()
        st.toast(f"Deleted {deleted} test users.", icon="🗑️")
        time.sleep(0.6)
        st.rerun()
else:
    st.caption("No test users today. / 本日のテストユーザーはいません。")
