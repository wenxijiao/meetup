import streamlit as st
import math
import time
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


@st.fragment(run_every=30)
def render_participant_status(target_per_table):
    participants = get_active_participants()
    total_count = len(participants)

    if total_count == 0:
        st.warning("⚠️ No participants checked in yet. Waiting...")
    else:
        st.info(f"✅ **{total_count}** participants are ready.")

    suggested_tables = math.ceil(total_count / target_per_table)
    if suggested_tables > 1:
        st.markdown(
        f"""
        > 💡 **Logic Check:** > {total_count} people ÷ {target_per_table} per table ≈ **{math.ceil(total_count / target_per_table)} tables**.  
        """
        )
    else:
        st.markdown(
        f"""
        > 💡 **Logic Check:** > {total_count} people ÷ {target_per_table} per table ≈ **1 table**.  
        """
        )


st.title("🎮 Event Operations")
st.caption("Setup the rules and control the flow.")

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
    if total_count > 0:
        suggested_tables = math.ceil(total_count / target_per_table)
    else:
        suggested_tables = 1
        
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

start_btn = st.button("Start Next Round 🎲", type="primary", width="stretch")
timer_btn = st.button("Start Timer ⏱️", type="secondary", width="stretch")

if start_btn:
    if total_count < min_per_table:
        st.error("Not enough people to start a round!")
    else:
        with st.spinner(f"Allocating people into tables..."):
            start_next_round(
                target_per_table=target_per_table,
                min_per_table=min_per_table,
            )
            # time.sleep(1)
        
        st.session_state.started = True

        st.success("✅ Round Started! Participants can now see their tables.")
        time.sleep(4)
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

state_now = get_event_state()
round_no = int(state_now.get("current_round") or 0)
started_now = bool(state_now.get("started"))
st.caption(f"Round={round_no} | Started={started_now}")

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

st.write("")
st.write("")
with st.expander("⚠️ Danger Zone (Reset)"):
    st.warning("This will clear all table assignments. Use only at the start of a new event.")
    if st.button("Reset Entire Event", type="secondary"):
        reset_event()
        st.session_state.started = False
        st.toast("Event has been reset.", icon="🔥")
        time.sleep(2)
        st.rerun()

st.divider()

st.subheader("💳 Payment Code Requirement")
st.caption("Control whether participants must enter a one-time payment code to check in. / 支払いコード必須を切り替え。")

state = get_event_state()
payment_required = bool(state.get("payment_code_required", True))

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