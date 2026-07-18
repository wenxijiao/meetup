import streamlit as st
import math
import time
from datetime import datetime

import pytz
from data.firebase_db import (
    get_active_participants,
    start_next_round,
    start_round_timer,
    reset_event,
    admin_add_participant,
    get_event_state,
    set_event_state,
    admin_override_participant_table,
)

tz = pytz.timezone("Pacific/Auckland")


@st.fragment(run_every=5)
def render_event_status():
    """Always-visible event status: round, timer, headcount."""
    state = get_event_state()
    participants = get_active_participants()
    round_no = int(state.get("current_round") or 0)
    started_at = state.get("round_started_at")
    duration_min = int(state.get("round_duration_min") or 0)

    timer_text = "Not started / 未開始"
    if started_at:
        try:
            started_dt = datetime.fromisoformat(started_at)
            if started_dt.tzinfo is None:
                started_dt = started_dt.replace(tzinfo=tz)
            elapsed = (datetime.now(tz=started_dt.tzinfo) - started_dt).total_seconds()
            remaining = max(0, int(duration_min * 60 - elapsed))
            if remaining > 0:
                timer_text = f"{remaining // 60}:{remaining % 60:02d} left"
            else:
                timer_text = "Time's up / 終了"
        except Exception:
            pass

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Round", round_no if round_no else "—")
    with col2:
        st.metric("⏱️ Timer", timer_text)
    with col3:
        st.metric("Checked in", len(participants))


@st.fragment(run_every=30)
def render_participant_status(target_per_table):
    participants = get_active_participants()
    total_count = len(participants)

    if total_count == 0:
        st.warning("⚠️ No participants checked in yet. Waiting...")
    else:
        st.info(f"✅ **{total_count}** participants are ready.")

    suggested_tables = max(1, math.ceil(total_count / target_per_table))
    st.markdown(
        f"> 💡 **Logic Check:** {total_count} people ÷ {target_per_table} per table "
        f"≈ **{suggested_tables} table{'s' if suggested_tables > 1 else ''}**."
    )


st.title("🎮 Event Operations")
st.caption("Setup the rules and control the flow.")

render_event_status()

participants = get_active_participants()
total_count = len(participants)

st.divider()

st.subheader("⚙️ Round Settings")

col1, col2, col3 = st.columns(3)

with col1:
    target_per_table = st.number_input(
        "Max People Per Table",
        min_value=2,
        max_value=10,
        value=4,
        help="Hard max number of people for each table."
    )

with col2:
    min_per_table = st.number_input(
        "Min People Per Table",
        min_value=1,
        max_value=target_per_table,
        value=2,
        help="The minimum number of people for each table."
    )

with col3:
    round_duration_min = st.number_input(
        "Round Duration (minutes)",
        min_value=5,
        max_value=90,
        value=30,
        help="Timer length shown to participants.",
    )

render_participant_status(target_per_table=target_per_table)

st.divider()

st.subheader("🚀 Actions")

auto_timer = st.checkbox(
    "Start timer automatically / タイマーも同時に開始",
    value=True,
    help="Starts the round timer right after tables are assigned.",
)
start_btn = st.button("Start Next Round 🎲", type="primary", width="stretch")
timer_btn = st.button("Start Timer ⏱️", type="secondary", width="stretch",
                      help="Manual start/restart, e.g. if you skipped auto-start.")

if start_btn:
    if total_count < min_per_table:
        st.error("Not enough people to start a round!")
    else:
        with st.spinner("Allocating people into tables..."):
            start_next_round(
                target_per_table=target_per_table,
                min_per_table=min_per_table,
            )
        if auto_timer:
            start_round_timer(round_duration_min)

        st.session_state.started = True

        st.success("✅ Round started! Participants can now see their tables.")
        time.sleep(2)
        st.rerun()

if timer_btn:
    started = start_round_timer(round_duration_min)
    if not started:
        st.warning("Start a round first, then start the timer.")
    else:
        st.success("⏱️ Timer started!")
        time.sleep(1)
        st.rerun()

st.divider()
st.subheader("🪑 Assign Table (Override for current round)")
st.caption(
    "Move a participant to a specific table now. Table options are existing tables + one new table (max+1). "
    "This does NOT affect next round assignment."
)

if not participants:
    st.info("No active participants yet.")
else:
    table_ints: list[int] = []
    for p in participants:
        if not p.table_number:
            continue
        try:
            table_ints.append(int(str(p.table_number)))
        except Exception:
            continue

    max_table = max(table_ints) if table_ints else 0
    table_options = [str(i) for i in range(1, max_table + 2)]  # always includes +1
    new_table = str(max_table + 1)

    col_o1, col_o2, col_o3 = st.columns([0.56, 0.22, 0.22], vertical_alignment="center")
    with col_o1:
        target_user = st.selectbox(
            "Participant / 参加者",
            options=participants,
            format_func=lambda p: f"{p.name}  (Table: {p.table_number or '-'})",
        )
    with col_o2:
        target_table = st.selectbox(
            "Table / テーブル",
            options=table_options,
            format_func=lambda t: f"{t} (new)" if str(t) == new_table else str(t),
        )
    with col_o3:
        st.write("")
        st.write("")
        if st.button("Assign / 指定", type="primary", width="stretch"):
            try:
                res = admin_override_participant_table(target_user.id, str(target_table), updated_by="admin")
                st.toast(
                    f"Updated {target_user.name}: {res.get('from') or '-'} → {res.get('to')}",
                    icon="✅",
                )
                time.sleep(0.5)
                st.rerun()
            except Exception as e:
                st.error(f"Failed: {e}")

st.subheader("🧍 Manual Check-in (No Device)")
st.caption("Use this when a participant cannot access the web app.")

with st.form("manual_checkin_form"):
    manual_name = st.text_input("Name")
    manual_language = st.selectbox("Language", ["English", "Japanese"])
    submitted = st.form_submit_button("Add Participant")
    if submitted:
        if not manual_name.strip():
            st.error("Please enter a name.")
        else:
            user = admin_add_participant(manual_name, manual_language, created_by_role="admin")
            table_info = user.table_number or "-"
            st.success(f"Added {user.name}. Table: {table_info}")

st.divider()

st.subheader("💳 Payment Code Requirement")
st.caption("Control whether participants must enter a one-time payment code to check in. / 支払いコード必須を切り替え。")

state = get_event_state()
payment_required = bool(state.get("payment_code_required", False))

col_pay1, col_pay2 = st.columns([0.45, 0.55], vertical_alignment="center")
with col_pay1:
    payment_required_ui = st.checkbox(
        "Require payment code / 支払いコード必須",
        value=payment_required,
    )
with col_pay2:
    st.caption("If disabled, participants can check in without a code (and will be marked as paid=waived).")

if st.button("Save / 保存", type="primary", width="stretch"):
    set_event_state({"payment_code_required": bool(payment_required_ui)})
    st.toast("Saved / 保存しました", icon="✅")
    time.sleep(0.6)
    st.rerun()

st.divider()

with st.expander("⚠️ Danger Zone (Reset)"):
    st.warning("This will clear all table assignments and rounds. Use only at the start of a new event.")
    confirm_reset = st.checkbox(
        "I understand this resets the whole event. / イベント全体をリセットすることを理解しました。"
    )
    if st.button("Reset Entire Event", type="secondary", disabled=not confirm_reset):
        reset_event()
        st.session_state.started = False
        st.toast("Event has been reset.", icon="🔥")
        time.sleep(2)
        st.rerun()
