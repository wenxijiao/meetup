import streamlit as st
from datetime import datetime, timedelta
import pytz
from streamlit_autorefresh import st_autorefresh
from data.firebase_db import get_my_status, logout_user, get_event_state

st.markdown(
    """
    <style>
    .hero-card {
        background: #fff7fb;
        border: 1px solid #f0d7e6;
        border-radius: 16px;
        padding: 18px 20px;
        margin-bottom: 16px;
        color: #111827;
        box-shadow: 0 10px 24px rgba(16,24,40,0.12);
    }
    .pill {
        display: inline-block;
        padding: 4px 10px;
        border-radius: 999px;
        font-size: 12px;
        background: #eef2ff;
        color: #1e3a8a;
        margin-right: 8px;
    }
    .table-card {
        text-align: center;
        padding: 28px;
        background: #f3f7ff;
        border-radius: 16px;
        border: 1px solid #dbe7ff;
        margin-bottom: 10px;
        box-shadow: 0 10px 24px rgba(16,24,40,0.12);
    }
    .table-label {
        color: #374151;
        margin: 0;
        font-size: 14px;
    }
    .table-number {
        color: #111827;
        font-size: 84px;
        font-weight: 700;
        margin: 0;
        line-height: 1.1;
    }
    .ring {
        width: 320px;
        height: 320px;
        border-radius: 50%;
        background:
          conic-gradient(#93c5fd var(--deg), #e5e7eb 0deg);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 8px auto 16px;
        box-shadow: 0 10px 24px rgba(16,24,40,0.12);
    }
    .ring-inner {
        width: 240px;
        height: 240px;
        border-radius: 50%;
        background: #ffffff;
        border: 1px solid #e5e7eb;
        display: flex;
        align-items: center;
        justify-content: center;
        flex-direction: column;
        color: #111827;
    }
    .ring-time {
        font-size: 112px;
        font-weight: 700;
        line-height: 1.1;
    }
    .ring-label {
        font-size: 12px;
        color: #6b7280;
    }
    </style>
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

        if current_participant.status == "Not Checked In":
            st.error("チェックインしていません。もう一度ログインしてください。 / You are not checked in. Please log in again.")
            if st.button("ログインへ / Go to Login"):
                st.session_state.role = "Select your role"
                st.rerun()
        else:
            st.markdown(
                """
                <div class="hero-card">
                    <span class="pill">参加者 / Participant</span>
                    <span class="pill">Meetup</span>
                </div>
                """,
                unsafe_allow_html=True,
            )

            name = current_participant.name

            col1, col2 = st.columns([3, 1])
            with col1:
                st.write(f"👤 **{name}**")
            with col2:
                if st.button("ログアウト / Logout", type="secondary", width="stretch"):
                    logout_user(current_id)
                    # Keep cookie for this event; skip auto-restore for this session.
                    st.session_state.skip_auto_restore = True
                    st.session_state.role = "Select your role"
                    st.rerun()

            table_number = current_participant.table_number

            st.divider()

            if table_number:
                state = get_event_state()
                started_at = state.get("round_started_at")
                duration_min = state.get("round_duration_min") or 30
                remaining_seconds = None
                deg = 0
                round_no = int(state.get("current_round") or 0)
                status_text = "Round {r}: Go to your new table / 新しいテーブルへ移動".format(r=round_no)
                if started_at:
                    try:
                        started_dt = datetime.fromisoformat(started_at)
                        if started_dt.tzinfo is None:
                            started_dt = started_dt.replace(tzinfo=pytz.timezone("Pacific/Auckland"))
                        now_dt = datetime.now(tz=started_dt.tzinfo)
                        elapsed = (now_dt - started_dt).total_seconds()
                        total = max(1, int(duration_min) * 60)
                        remaining_seconds = max(0, int(total - elapsed))
                        pct = remaining_seconds / total
                        deg = int(pct * 360)
                        status_text = "Round {r}: In progress / 進行中".format(r=round_no)
                    except Exception:
                        remaining_seconds = None

                label = "Table / テーブル" if started_at else "Waiting / 待機"
                st.markdown(
                    f"""
                    <div class="ring" style="--deg: {deg}deg;">
                        <div class="ring-inner">
                            <div class="ring-time">{table_number}</div>
                            <div class="ring-label">{label}</div>
                        </div>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.info(status_text)
            else:
                st.info("イベントはまだ開始していません。主催者が開始するまでお待ちください。")
                st.caption("The event has not started yet. Please wait for the organizer to begin...")

        # If timer is active, refresh more frequently for smoother countdown.
        refresh_ms = 5_000 if table_number and started_at else 30_000
        st_autorefresh(interval=refresh_ms, key="auto_refresh")

    except ValueError:
        st.session_state.role = "Select your role"
        st.rerun()
