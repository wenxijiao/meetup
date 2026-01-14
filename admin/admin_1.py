import streamlit as st
import math
import time
from data.firebase_db import get_active_participants, start_next_round, reset_event


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

col1, col2 = st.columns(2)

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

render_participant_status(target_per_table=target_per_table)

st.divider()

st.subheader("🚀 Actions")

start_btn = st.button("Start Next Round 🎲", type="primary", width="stretch")

if start_btn:
    if total_count < min_per_table:
        st.error("Not enough people to start a round!")
    else:
        with st.spinner(f"Allocating people into tables..."):
            start_next_round(target_per_table=target_per_table, min_per_table=min_per_table)
            # time.sleep(1)
        
        st.session_state.started = True

        st.success("✅ Round Started! Participants can now see their tables.")
        time.sleep(4)
        st.rerun()

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
