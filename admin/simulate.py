import random
from datetime import datetime

import pytz
import streamlit as st

from data.data_structure import Participant
from data.logic import assign_tables, assign_tables_debug
from data.firebase_db import (
    clear_test_participants,
    create_test_participants,
    get_event_state,
    get_table_activity,
    get_test_participants,
    start_next_round,
    start_round_timer,
)


st.title("🧪 Table Assignment Simulator / Visualizer")
st.caption("No real participants needed. Generates fake users and shows multi-round outcomes.")

st.divider()

col1, col2, col3 = st.columns(3)
with col1:
    total = st.number_input("Total participants", min_value=2, max_value=200, value=50, step=1)
with col2:
    max_per_table = st.number_input("Max people per table", min_value=2, max_value=10, value=4, step=1)
with col3:
    min_per_table = st.number_input("Min people per table", min_value=1, max_value=int(max_per_table), value=2, step=1)

rounds = st.number_input("Rounds to simulate", min_value=1, max_value=10, value=4, step=1)

st.subheader("Fake data generation (by counts)")
st.caption("Your production login is single-choice (English/Japanese), so this defaults to counts.")

allow_bilingual = st.checkbox(
    "Allow bilingual users (edge testing only; production login does not support this)",
    value=False,
)

if allow_bilingual:
    c1, c2, c3 = st.columns(3)
    with c1:
        n_en = st.number_input("English count", min_value=0, max_value=int(total), value=int(total // 2), step=1)
    with c2:
        n_jp = st.number_input("Japanese count", min_value=0, max_value=int(total), value=int(total // 2), step=1)
    with c3:
        n_both = st.number_input(
            "Bilingual count",
            min_value=0,
            max_value=int(total),
            value=int(total) - int(n_en) - int(n_jp),
            step=1,
        )
else:
    c1, c2 = st.columns(2)
    with c1:
        n_en = st.number_input("English count", min_value=0, max_value=int(total), value=int(total // 2), step=1)
    with c2:
        n_jp = st.number_input("Japanese count", min_value=0, max_value=int(total), value=int(total) - int(n_en), step=1)
    n_both = 0

seed = st.number_input("Random seed (reproducible)", min_value=0, max_value=999999, value=1, step=1)

if int(n_en) + int(n_jp) + int(n_both) != int(total):
    st.error("Count mismatch: English + Japanese (+ Bilingual) must equal Total participants.")
    st.stop()

st.caption(f"Counts: English={int(n_en)}  Japanese={int(n_jp)}  Bilingual={int(n_both)}")


def sample_language(r: float) -> str:
    # Unused in "by counts" mode. Kept for potential future "by ratio" mode.
    return "English" if r < 0.5 else "Japanese"

def met_before_ids(p: Participant):
    met = set()
    for e in p.history or []:
        if isinstance(e, dict) and isinstance(e.get("mates"), list):
            for mid in e["mates"]:
                if isinstance(mid, str) and mid:
                    met.add(mid)
    met.discard(p.id)
    return met

def summarize_tables(updated):
    tables = {}
    for p in updated:
        tables.setdefault(str(p.table_number), []).append(p)
    # summary
    sizes = [len(v) for v in tables.values()]
    mixed = 0
    for plist in tables.values():
        has_en = any("English" in str(p.language) for p in plist)
        has_jp = any("Japanese" in str(p.language) for p in plist)
        if has_en and has_jp:
            mixed += 1
    return tables, sizes, mixed

def repeat_pairs_against_prev(tables, prev_met_map):
    # Count pairs that have met before (in prev_met_map), pair counted once
    repeat_pairs = 0
    for plist in tables.values():
        ids = [p.id for p in plist]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if b in prev_met_map.get(a, set()) or a in prev_met_map.get(b, set()):
                    repeat_pairs += 1
    return repeat_pairs


show_process = st.checkbox("Show phase snapshots (best-effort)", value=True)
use_debug = st.checkbox("Show debug JSON (may be large)", value=False)

run = st.button("Run simulation (multi-round)", type="primary", width="stretch")

if run:
    rng = random.Random(int(seed))
    participants = []
    langs = (["English"] * int(n_en)) + (["Japanese"] * int(n_jp))
    if allow_bilingual and int(n_both) > 0:
        langs += (["English & Japanese"] * int(n_both))
    rng.shuffle(langs)
    for i, lang in enumerate(langs):
        participants.append(Participant(name=f"User{i+1}", language=lang))

    round_summaries = []
    round_tables = []
    round_phases = []

    for r in range(1, int(rounds) + 1):
        # Snapshot who has met before THIS round starts (so we can measure repeats correctly)
        prev_met_map = {p.id: met_before_ids(p) for p in participants}

        if use_debug and r == 1:
            # Debug output can be huge; we only dump the full JSON for round 1 by default.
            updated, num_tables, dbg = assign_tables_debug(
                participants, max_per_table=int(max_per_table), min_per_table=int(min_per_table)
            )
        else:
            updated, num_tables = assign_tables(
                participants, target_per_table=int(max_per_table), min_per_table=int(min_per_table)
            )

        tables, sizes, mixed = summarize_tables(updated)
        repeats = repeat_pairs_against_prev(tables, prev_met_map)

        round_summaries.append(
            {
                "round": r,
                "tables": num_tables,
                "min_size": min(sizes) if sizes else 0,
                "max_size": max(sizes) if sizes else 0,
                "mixed_tables(en+jp)": mixed,
                "repeat_pairs_vs_previous": repeats,
            }
        )
        round_tables.append(tables)

        if show_process:
            # capture best-effort phase snapshots
            try:
                import data.logic as logic_mod

                phase_dbg = getattr(logic_mod, "_LAST_ASSIGN_DEBUG", None)
                if phase_dbg and isinstance(phase_dbg, dict):
                    round_phases.append(phase_dbg)
                else:
                    round_phases.append(None)
            except Exception:
                round_phases.append(None)

    st.success(f"Done: {len(participants)} participants, {int(rounds)} rounds.")

    st.subheader("Per-round summary")
    st.dataframe(round_summaries, width="stretch", hide_index=True)

    if use_debug:
        st.divider()
        st.subheader("Round 1 Debug (optional)")
        st.caption("Only shows Round 1 to avoid heavy payloads.")
        st.json(dbg["inputs"])
        st.json(dbg["result"])

    # Table view
    st.divider()
    st.subheader("Per-round tables")
    for r in range(1, int(rounds) + 1):
        tables = round_tables[r - 1]
        with st.expander(f"Round {r} - tables={len(tables)}", expanded=False):
            for tno in sorted(tables.keys(), key=lambda x: int(x)):
                plist = tables[tno]
                has_en = any("English" in str(p.language) for p in plist)
                has_jp = any("Japanese" in str(p.language) for p in plist)
                st.markdown(f"**Table {tno}** | size={len(plist)} | EN={has_en} JP={has_jp}")
                st.write([{"name": p.name, "language": p.language} for p in plist])

    if show_process:
        st.divider()
        st.subheader("Process snapshots (by round)")
        for r in range(1, int(rounds) + 1):
            phase_dbg = round_phases[r - 1] if r - 1 < len(round_phases) else None
            if not phase_dbg:
                continue
            with st.expander(f"Round {r} snapshots", expanded=False):
                phases = phase_dbg.get("phases", [])
                for ph in phases:
                    with st.expander(ph.get("name", "phase"), expanded=False):
                        st.json(ph.get("tables"))

                placements = phase_dbg.get("placements", [])
                if placements:
                    st.subheader("Placement log (repeat cost)")
                    st.write(placements[:200])  # cap output
                    if len(placements) > 200:
                        st.caption(f"Showing first 200 rows out of {len(placements)}.")

st.divider()
st.title("🧪 Firebase Test Data (Real UI)")
st.caption("Seed test users into Firestore to preview the real app behavior.")

tz = pytz.timezone("Pacific/Auckland")
today_str = str(datetime.now(tz=tz).date())

colf1, colf2, colf3 = st.columns(3)
with colf1:
    fb_en = st.number_input("EN test users", min_value=0, max_value=200, value=10, step=1)
with colf2:
    fb_jp = st.number_input("JP test users", min_value=0, max_value=200, value=10, step=1)
with colf3:
    fb_tag = st.text_input("Test tag (optional)", value="demo")

colr1, colr2 = st.columns(2)
with colr1:
    fb_max = st.number_input("Round max per table", min_value=2, max_value=10, value=4, step=1)
with colr2:
    fb_min = st.number_input("Round min per table", min_value=1, max_value=int(fb_max), value=2, step=1)
fb_duration = st.number_input("Round duration (minutes)", min_value=5, max_value=90, value=30, step=5)

confirm = st.checkbox("I understand this writes to Firestore (today only).", value=False)
colb1, colb2, colb3 = st.columns(3)
with colb1:
    if st.button("Seed test users", width="stretch"):
        if not confirm:
            st.error("Please confirm before writing.")
        else:
            created = create_test_participants(int(fb_en), int(fb_jp), tag=fb_tag or None)
            st.success(f"Created {len(created)} test users for {today_str}.")
with colb2:
    if st.button("Seed + Start round", width="stretch"):
        if not confirm:
            st.error("Please confirm before writing.")
        else:
            created = create_test_participants(int(fb_en), int(fb_jp), tag=fb_tag or None)
            tables = start_next_round(int(fb_max), int(fb_min))
            st.success(f"Created {len(created)} users and started round. Tables: {tables}.")
with colb3:
    if st.button("Clear test users", width="stretch"):
        if not confirm:
            st.error("Please confirm before deleting.")
        else:
            deleted = clear_test_participants(tag=fb_tag or None)
            st.success(f"Deleted {deleted} test users.")

colb4, colb5 = st.columns(2)
with colb4:
    if st.button("Start timer (current round)", width="stretch"):
        if not confirm:
            st.error("Please confirm before writing.")
        else:
            ok = start_round_timer(int(fb_duration))
            if not ok:
                st.warning("No active round. Start a round first.")
            else:
                st.success("Timer started.")

st.subheader("Participant UI preview (from test users)")
all_test_users = get_test_participants()
filtered = []
if fb_tag:
    filtered = [u for u in all_test_users if u.get("test_tag") == fb_tag]
test_users = filtered if filtered else all_test_users

if not test_users:
    st.info("No test users found for preview.")
else:
    if fb_tag and not filtered and all_test_users:
        st.warning("No users matched this tag. Showing all test users instead.")
    options = {f"{u.get('name')} ({u.get('language')})": u for u in test_users}
    choice = st.selectbox("Select a test user", list(options.keys()))
    selected = options[choice]
    st.write(
        {
            "name": selected.get("name"),
            "language": selected.get("language"),
            "status": selected.get("status"),
            "table_number": selected.get("table_number"),
        }
    )

    state = get_event_state()
    round_no = int(state.get("current_round") or 0)
    table_no = selected.get("table_number")
    if round_no > 0 and table_no:
        activity = get_table_activity(round_no, str(table_no))
        if activity and activity.get("task_index") is not None:
            task_idx = int(activity["task_index"])
        else:
            task_idx = pick_task_index(today_str, round_no, str(table_no))
        task = TASKS[task_idx]
        st.markdown(f"**Table {table_no} | Round {round_no}**")
        st.markdown(f"**{task['title']}**")
        for line in task["steps"]:
            st.write(f"- {line}")


