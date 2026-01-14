import random
from datetime import datetime

import pytz
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from data.activities import TASKS, default_task_index
from data.firebase_db import get_event_state, get_my_status, get_table_activity, set_table_activity

tz = pytz.timezone("Pacific/Auckland")



st.markdown(
    """
    <style>
    .activity-wrap {
        max-width: 780px;
        margin: 0 auto;
    }
    .activity-card {
        background: #f8faff;
        border: 1px solid #dbe7ff;
        border-radius: 16px;
        padding: 20px 22px;
        box-shadow: 0 10px 24px rgba(16,24,40,0.12);
        margin-bottom: 16px;
        color: #111827;
    }
    .activity-title {
        font-size: 22px;
        font-weight: 700;
        margin-bottom: 6px;
        color: #111827;
    }
    .activity-sub {
        color: #4b5563;
        font-size: 14px;
        margin-bottom: 10px;
    }
    .badge {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        background: #ffe7f3;
        color: #9d174d;
        margin-right: 6px;
    }
    .activity-body {
        font-size: 16px;
        line-height: 1.7;
        color: #111827;
    }
    .activity-body li {
        margin-bottom: 6px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="activity-wrap">
        <div class="activity-card">
            <div class="activity-title">活動 / Activities</div>
            <div class="activity-sub">同じテーブルの人は同じお題が表示されます。 / Same table sees the same task.</div>
        </div>
    </div>
    """,
    unsafe_allow_html=True,
)

current_id = st.session_state.u_id
if not current_id:
    st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
    if st.button("ログインへ / Go to Login"):
        st.session_state.role = "Select your role"
        st.rerun()
else:
    try:
        current_participant = get_my_status(current_id)
        if current_participant.status != "Checked In":
            st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
            if st.button("ログインへ / Go to Login"):
                st.session_state.role = "Select your role"
                st.rerun()
        else:
            table_number = current_participant.table_number
            if not table_number:
                st.info("イベントはまだ開始していません。 / The event has not started yet.")
            else:
                state = get_event_state()
                round_no = int(state.get("current_round") or 0)
                date_str = str(datetime.now(tz=tz).date())

                activity = get_table_activity(round_no, str(table_number))
                if activity and activity.get("task_index") is not None:
                    task_idx = int(activity["task_index"])
                else:
                    task_idx = default_task_index(date_str, round_no, str(table_number))
                task = TASKS[task_idx]

                steps_html = "".join([f"<li>{line}</li>" for line in task["steps"]])
                st.markdown(
                    f"""
                    <div class="activity-wrap">
                        <div class="activity-card">
                            <span class="badge">Table {table_number}</span>
                            <span class="badge">Round {round_no}</span>
                            <div class="activity-title">{task['title']}</div>
                            <div class="activity-body">
                                <ul>
                                    {steps_html}
                                </ul>
                            </div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

                if st.button("お題を切り替える / Switch task"):
                    if len(TASKS) > 1:
                        next_idx = task_idx
                        while next_idx == task_idx:
                            next_idx = random.randrange(len(TASKS))
                    else:
                        next_idx = task_idx
                    set_table_activity(round_no, str(table_number), next_idx, current_participant.id)
                    st.rerun()

                st.caption("このお題は同じテーブルの全員に共有されます。 / This task is shared by your table.")
                st.caption("次のラウンドでお題が変わります。 / The task updates next round.")

        # Refresh periodically to pick up round/table changes
        st_autorefresh(interval=30_000, key="activity_refresh")
    except ValueError:
        st.session_state.role = "Select your role"
        st.rerun()
