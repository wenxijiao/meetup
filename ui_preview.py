from __future__ import annotations

from datetime import datetime, timedelta

import pytz
import streamlit as st
try:
    from streamlit_autorefresh import st_autorefresh  # type: ignore
except Exception:  # pragma: no cover
    def st_autorefresh(*args, **kwargs):
        # Optional dependency: UI still works without auto-refresh.
        return None


st.set_page_config(page_title="UI Preview", page_icon="✨", layout="wide")

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
    .ring {
        width: 320px;
        height: 320px;
        border-radius: 50%;
        background:
          conic-gradient(#93c5fd var(--deg), #e5e7eb 0deg);
        display: flex;
        align-items: center;
        justify-content: center;
        margin: 8px auto 10px;
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
        padding: 14px 12px;
        text-align: center;
    }
    .ring-main {
        font-size: 96px;
        font-weight: 800;
        margin: 0;
        line-height: 1.0;
    }
    .ring-label {
        font-size: 12px;
        color: #6b7280;
        margin-top: 4px;
    }
    .ring-sub {
        font-size: 14px;
        font-weight: 750;
        margin-top: 10px;
        color: #111827;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

tz = pytz.timezone("Pacific/Auckland")

if "demo_round_started_at" not in st.session_state:
    st.session_state.demo_round_started_at = None  # datetime | None
if "demo_round_no" not in st.session_state:
    st.session_state.demo_round_no = 1
if "demo_round_duration_min" not in st.session_state:
    st.session_state.demo_round_duration_min = 30

st.title("✨ UI Preview (Public Demo)")
st.caption("This page previews the Participant UI (table card + status + countdown) without login or database.")

st.divider()

left, right = st.columns([0.55, 0.45], vertical_alignment="top")

with left:
    st.subheader("Controls")

    name = st.text_input("Name", value="Vincent")
    language = st.selectbox("Language", ["English", "Japanese"], index=0)
    table_number = st.number_input("Table number", min_value=1, max_value=99, value=7, step=1)

    c1, c2 = st.columns(2)
    with c1:
        st.session_state.demo_round_no = st.number_input(
            "Round number", min_value=0, max_value=20, value=int(st.session_state.demo_round_no), step=1
        )
    with c2:
        st.session_state.demo_round_duration_min = st.number_input(
            "Round duration (min)",
            min_value=1,
            max_value=120,
            value=int(st.session_state.demo_round_duration_min),
            step=1,
        )

    b1, b2, b3 = st.columns(3)
    with b1:
        if st.button("Start round (now)", type="primary", width="stretch"):
            st.session_state.demo_round_started_at = datetime.now(tz=tz)
            st.rerun()
    with b2:
        if st.button("Waiting / Not started", width="stretch"):
            st.session_state.demo_round_started_at = None
            st.rerun()
    with b3:
        if st.button("Simulate +5 min", width="stretch"):
            st.session_state.demo_round_started_at = datetime.now(tz=tz) - timedelta(minutes=5)
            st.rerun()

    live = st.checkbox("Live countdown (auto refresh)", value=True)
    refresh_ms = st.slider("Refresh interval (ms)", min_value=500, max_value=10_000, value=1_000, step=500)

with right:
    st.subheader("Preview")

    st.markdown(
        "<div class='hero-card'>"
        f"<div><span class='pill'>👤 {name or 'Guest'}</span>"
        f"<span class='pill'>🌐 {language}</span>"
        f"<span class='pill'>Round {int(st.session_state.demo_round_no)}</span></div>"
        "<div style='margin-top:10px; opacity:0.88; font-size:13px;'>"
        "This is a mocked Participant view for portfolio/demo purposes."
        "</div>"
        "</div>",
        unsafe_allow_html=True,
    )

    started_at = st.session_state.demo_round_started_at
    duration_min = int(st.session_state.demo_round_duration_min)
    round_no = int(st.session_state.demo_round_no)

    deg = 0
    status_text = f"Round {round_no}: Go to your new table / 新しいテーブルへ移動"
    countdown_text = "⏳ Time left: --:--"
    label = "Waiting / 待機"

    if started_at:
        now_dt = datetime.now(tz=started_at.tzinfo or tz)
        elapsed = (now_dt - started_at).total_seconds()
        total = max(1, duration_min * 60)
        remaining_seconds = max(0, int(total - elapsed))
        pct = remaining_seconds / total
        deg = int(pct * 360)

        mm = remaining_seconds // 60
        ss = remaining_seconds % 60
        countdown_text = f"⏳ Time left: {mm:02d}:{ss:02d}"
        label = "Table / テーブル"
        status_text = f"Round {round_no}: In progress / 進行中"

    st.markdown(
        f"""
        <div class="ring" style="--deg: {deg}deg;">
            <div class="ring-inner">
                <div class="ring-main">{int(table_number)}</div>
                <div class="ring-label">{label}</div>
                <div class="ring-sub">{countdown_text}</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.info(status_text)

    if started_at:
        st.caption(f"Started at: {started_at.isoformat(timespec='seconds')}")

if live:
    st_autorefresh(interval=int(refresh_ms), key="ui_preview_refresh")

