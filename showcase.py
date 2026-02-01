import random

import streamlit as st

from data.data_structure import Participant
from data.logic import assign_tables, assign_tables_debug


st.set_page_config(page_title="Demo / Showcase", page_icon="🧪", layout="wide")

st.title("🧪 Demo / Showcase")
st.caption(
    "This is a public, read-only demo page. No password, no one-time payment code, and no database writes."
)

st.divider()

st.subheader("Table assignment simulator (local only)")
st.caption("Generates fake participants in memory and runs the same assignment algorithm used in the app.")

col1, col2, col3, col4 = st.columns(4)
with col1:
    total = st.number_input("Total participants", min_value=2, max_value=200, value=40, step=1)
with col2:
    max_per_table = st.number_input("Max per table", min_value=2, max_value=10, value=4, step=1)
with col3:
    min_per_table = st.number_input(
        "Min per table",
        min_value=1,
        max_value=int(max_per_table),
        value=min(2, int(max_per_table)),
        step=1,
    )
with col4:
    rounds = st.number_input("Rounds", min_value=1, max_value=10, value=3, step=1)

st.caption("Language distribution (counts)")
col_en, col_jp, col_seed = st.columns(3)
with col_en:
    n_en = st.number_input("English count", min_value=0, max_value=int(total), value=int(total // 2), step=1)
with col_jp:
    n_jp = st.number_input(
        "Japanese count",
        min_value=0,
        max_value=int(total),
        value=int(total) - int(n_en),
        step=1,
    )
with col_seed:
    seed = st.number_input("Random seed", min_value=0, max_value=999999, value=1, step=1)

if int(n_en) + int(n_jp) != int(total):
    st.error("Count mismatch: English + Japanese must equal Total participants.")
    st.stop()

show_process = st.checkbox("Show process snapshots (best-effort)", value=True)
show_debug_json = st.checkbox("Show debug JSON (can be large)", value=False)

run = st.button("Run demo", type="primary", width="stretch")


def _met_before_ids(p: Participant) -> set[str]:
    met: set[str] = set()
    for e in p.history or []:
        if isinstance(e, dict) and isinstance(e.get("mates"), list):
            for mid in e["mates"]:
                if isinstance(mid, str) and mid:
                    met.add(mid)
    met.discard(p.id)
    return met


def _summarize_tables(updated: list[Participant]):
    tables: dict[str, list[Participant]] = {}
    for p in updated:
        tables.setdefault(str(p.table_number), []).append(p)
    sizes = [len(v) for v in tables.values()]
    mixed = 0
    for plist in tables.values():
        has_en = any("English" in str(p.language) for p in plist)
        has_jp = any("Japanese" in str(p.language) for p in plist)
        if has_en and has_jp:
            mixed += 1
    return tables, sizes, mixed


def _repeat_pairs_against_prev(tables: dict[str, list[Participant]], prev_met_map: dict[str, set[str]]) -> int:
    repeat_pairs = 0
    for plist in tables.values():
        ids = [p.id for p in plist]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if b in prev_met_map.get(a, set()) or a in prev_met_map.get(b, set()):
                    repeat_pairs += 1
    return repeat_pairs


if run:
    rng = random.Random(int(seed))
    langs = (["English"] * int(n_en)) + (["Japanese"] * int(n_jp))
    rng.shuffle(langs)

    participants = [Participant(name=f"User{i+1}", language=lang) for i, lang in enumerate(langs)]

    round_summaries: list[dict] = []
    round_tables: list[dict[str, list[Participant]]] = []
    round_phases: list[dict | None] = []

    dbg = None
    for r in range(1, int(rounds) + 1):
        prev_met_map = {p.id: _met_before_ids(p) for p in participants}

        if show_debug_json and r == 1:
            updated, num_tables, dbg = assign_tables_debug(
                participants, max_per_table=int(max_per_table), min_per_table=int(min_per_table)
            )
        else:
            updated, num_tables = assign_tables(
                participants,
                target_per_table=int(max_per_table),
                min_per_table=int(min_per_table),
            )

        tables, sizes, mixed = _summarize_tables(updated)
        repeats = _repeat_pairs_against_prev(tables, prev_met_map)

        round_summaries.append(
            {
                "round": r,
                "tables": int(num_tables),
                "min_size": min(sizes) if sizes else 0,
                "max_size": max(sizes) if sizes else 0,
                "mixed_tables(en+jp)": int(mixed),
                "repeat_pairs_vs_previous": int(repeats),
            }
        )
        round_tables.append(tables)

        if show_process:
            try:
                import data.logic as logic_mod

                phase_dbg = getattr(logic_mod, "_LAST_ASSIGN_DEBUG", None)
                round_phases.append(phase_dbg if isinstance(phase_dbg, dict) else None)
            except Exception:
                round_phases.append(None)

    st.success(f"Done: {len(participants)} participants, {int(rounds)} rounds.")

    st.subheader("Per-round summary")
    st.dataframe(round_summaries, width="stretch", hide_index=True)

    if show_debug_json and dbg:
        st.divider()
        st.subheader("Round 1 debug (optional)")
        st.caption("Only shows Round 1 to avoid heavy payloads.")
        st.json(dbg.get("inputs"))
        st.json(dbg.get("result"))

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
                for ph in phase_dbg.get("phases", []) or []:
                    with st.expander(ph.get("name", "phase"), expanded=False):
                        st.json(ph.get("tables"))

                placements = phase_dbg.get("placements", []) or []
                if placements:
                    st.subheader("Placement log (repeat cost)")
                    st.write(placements[:200])
                    if len(placements) > 200:
                        st.caption(f"Showing first 200 rows out of {len(placements)}.")

