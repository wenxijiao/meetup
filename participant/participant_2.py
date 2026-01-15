import random
from datetime import datetime

import pytz
import streamlit as st
from streamlit_autorefresh import st_autorefresh

from activities.registry import get_activity_meta
from activities.ui import render_activity_participant
from data.firebase_db import (
    get_event_state,
    get_my_status,
    ensure_table_activity,
    switch_table_activity,
)

tz = pytz.timezone("Pacific/Auckland")



st.markdown(
    """
    <style>
    /* Keep the page centered and consistent with Streamlit theme */
    section.main > div.block-container {
        max-width: 860px;
        padding-top: 1.4rem;
    }

    /* Button polish */
    div.stButton > button {
        border-radius: 12px;
        padding: 0.65rem 0.9rem;
        font-weight: 650;
    }

    /* Small pills for meta info */
    .pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        border: 1px solid rgba(128,128,128,0.25);
        background: rgba(255, 99, 132, 0.10);
        color: inherit;
        margin-right: 8px;
    }

    /* Word display card (theme-friendly) */
    .word-card {
        border-radius: 18px;
        padding: 22px 22px;
        border: 1px solid rgba(128,128,128,0.25);
        background: var(--secondary-background-color, rgba(255,255,255,0.06));
        color: var(--text-color, inherit);
        margin-top: 0.5rem;
    }
    .word-title {
        font-size: 16px;
        font-weight: 750;
        margin-bottom: 6px;
    }
    .word-text {
        text-align: center;
        font-size: clamp(40px, 7vw, 64px);
        font-weight: 900;
        letter-spacing: 0.6px;
        margin: 10px 0 4px;
        line-height: 1.05;
    }
    .hint {
        opacity: 0.82;
        font-size: 13px;
        line-height: 1.45;
        margin-top: 10px;
    }

    /* Generic info card (for prompts + status) */
    .info-card {
        border-radius: 18px;
        padding: 18px 18px;
        border: 1px solid rgba(128,128,128,0.25);
        background: var(--secondary-background-color, rgba(255,255,255,0.06));
        color: var(--text-color, inherit);
        margin: 0.6rem 0 0.2rem;
    }
    .info-title {
        font-size: 14px;
        font-weight: 800;
        letter-spacing: 0.2px;
        margin-bottom: 8px;
        opacity: 0.95;
    }
    .prompt-jp {
        font-size: 20px;
        font-weight: 850;
        line-height: 1.25;
        margin: 2px 0 6px;
    }
    .prompt-en {
        font-size: 13px;
        opacity: 0.82;
        margin-bottom: 12px;
        line-height: 1.35;
    }
    .stats-grid {
        display: grid;
        grid-template-columns: repeat(3, minmax(0, 1fr));
        gap: 10px;
        margin-top: 8px;
    }
    .stat {
        border-radius: 14px;
        padding: 10px 12px;
        border: 1px solid rgba(128,128,128,0.18);
        background: rgba(255,255,255,0.04);
    }
    .stat-label {
        font-size: 12px;
        opacity: 0.78;
        margin-bottom: 4px;
        font-weight: 650;
    }
    .stat-value {
        font-size: 18px;
        font-weight: 900;
        line-height: 1.1;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

current_id = st.session_state.u_id
if not current_id:
    st.title("活動 / Activities")
    st.caption("同じテーブルの人は同じ活動が表示されます。 / Same table sees the same activity.")
    st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
    if st.button("ログインへ / Go to Login"):
        st.session_state.role = "Select your role"
        st.rerun()
else:
    try:
        current_participant = get_my_status(current_id)
        if current_participant.status != "Checked In":
            st.title("活動 / Activities")
            st.caption("同じテーブルの人は同じ活動が表示されます。 / Same table sees the same activity.")
            st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
            if st.button("ログインへ / Go to Login"):
                st.session_state.role = "Select your role"
                st.rerun()
        else:
            table_number = current_participant.table_number
            if not table_number:
                st.title("活動 / Activities")
                st.caption("同じテーブルの人は同じ活動が表示されます。 / Same table sees the same activity.")
                st.info("イベントはまだ開始していません。 / The event has not started yet.")
            else:
                event_state = get_event_state()
                round_no = int(event_state.get("current_round") or 0)
                if round_no <= 0:
                    st.title("活動 / Activities")
                    st.caption("同じテーブルの人は同じ活動が表示されます。 / Same table sees the same activity.")
                    st.info("ラウンドがまだ開始されていません。 / Round has not started yet.")
                else:
                    doc = ensure_table_activity(round_no, str(table_number), current_participant.id)
                    activity_id = doc.get("activity_id")
                    meta = get_activity_meta(activity_id) or {"title": activity_id, "description": ""}
                    state = doc.get("state") or {}
                    desc_text = (meta.get("description", "") or "").strip()

                    # Top row: big page title + global switch button (table-level)
                    top_l, top_r = st.columns([0.72, 0.28], vertical_alignment="center")
                    with top_l:
                        st.title("活動 / Activities")
                        st.caption("同じテーブルの人は同じ活動が表示されます。 / Same table sees the same activity.")
                        # st.caption("Same table sees the same activity.")
                    with top_r:
                        if st.button("ゲーム変更 / Switch game", width="stretch", type="primary"):
                            switch_table_activity(round_no, str(table_number), current_participant.id)
                            st.rerun()

                    st.divider()

                    st.markdown(
                        f"<span class='pill'>Table {table_number}</span><span class='pill'>Round {round_no}</span>",
                        unsafe_allow_html=True,
                    )
                    st.subheader(meta.get("title", ""))
                    if desc_text:
                        st.caption(desc_text)

                    rendered = render_activity_participant(
                        activity_id,
                        state=state,
                        participant_id=current_participant.id,
                        round_no=round_no,
                        table_number=str(table_number),
                        updated_by=current_participant.id,
                    )
                    if not rendered:
                        st.info("This activity type is not implemented yet.")

        # Refresh periodically to pick up round/table changes
        st_autorefresh(interval=10_000, key="activity_refresh")
    except ValueError:
        st.session_state.role = "Select your role"
        st.rerun()
