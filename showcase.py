"""Public, read-only product tour for recruiters and portfolio reviewers."""

from __future__ import annotations

import random

import streamlit as st

from data.data_structure import Participant
from data.logic import assign_tables


st.set_page_config(page_title="MeetupOps | Recruiter Tour", page_icon="🤝", layout="wide")


DEMO_PARTICIPANTS = 24
DEMO_ROUNDS = 3
DEMO_TABLE_SIZE = 4


def _met_before_ids(participant: Participant) -> set[str]:
    met: set[str] = set()
    for entry in participant.history or []:
        if not isinstance(entry, dict):
            continue
        for participant_id in entry.get("mates", []):
            if isinstance(participant_id, str) and participant_id:
                met.add(participant_id)
    met.discard(participant.id)
    return met


def _group_by_table(participants: list[Participant]) -> dict[str, list[Participant]]:
    tables: dict[str, list[Participant]] = {}
    for participant in participants:
        tables.setdefault(str(participant.table_number), []).append(participant)
    return tables


def _count_repeat_pairs(
    tables: dict[str, list[Participant]], previous_mates: dict[str, set[str]]
) -> int:
    repeats = 0
    for table in tables.values():
        participant_ids = [participant.id for participant in table]
        for index, first_id in enumerate(participant_ids):
            for second_id in participant_ids[index + 1 :]:
                if second_id in previous_mates.get(first_id, set()):
                    repeats += 1
    return repeats


@st.cache_data(show_spinner=False)
def build_demo(seed: int = 7) -> tuple[list[dict], list[dict[str, list[dict]]]]:
    """Run the production assignment algorithm entirely in memory."""
    random.seed(seed)
    languages = ["English"] * (DEMO_PARTICIPANTS // 2) + ["Japanese"] * (
        DEMO_PARTICIPANTS // 2
    )
    random.shuffle(languages)
    participants = [
        Participant(name=f"Guest {index + 1}", language=language)
        for index, language in enumerate(languages)
    ]

    summaries: list[dict] = []
    rounds: list[dict[str, list[dict]]] = []
    for round_number in range(1, DEMO_ROUNDS + 1):
        previous_mates = {
            participant.id: _met_before_ids(participant) for participant in participants
        }
        participants, _ = assign_tables(
            participants,
            target_per_table=DEMO_TABLE_SIZE,
            min_per_table=2,
        )
        tables = _group_by_table(participants)
        mixed_tables = sum(
            1
            for table in tables.values()
            if {participant.language for participant in table}
            == {"English", "Japanese"}
        )
        summaries.append(
            {
                "Round": round_number,
                "Tables": len(tables),
                "Language-balanced tables": mixed_tables,
                "Repeated pairs": _count_repeat_pairs(tables, previous_mates),
            }
        )
        rounds.append(
            {
                table_number: [
                    {"Name": participant.name, "Language": participant.language}
                    for participant in table
                ]
                for table_number, table in tables.items()
            }
        )
    return summaries, rounds


st.title("MeetupOps")
st.subheader("A real-time operations platform for multilingual community events")
st.caption(
    "Portfolio demo · No login required · Uses the production assignment algorithm · "
    "Does not write to the database"
)

st.info(
    "**Reviewer shortcut:** this page tells the complete story in about two minutes. "
    "Use **Staff / Participant Login** in the sidebar only if you want to explore the live workflows."
)

st.markdown("### The problem and the product")
problem_col, product_col = st.columns(2)
with problem_col:
    with st.container(border=True):
        st.markdown("#### Before")
        st.write(
            "Event staff coordinate payment, check-in, table allocation, round changes, "
            "and activities across separate spreadsheets and chat messages."
        )
with product_col:
    with st.container(border=True):
        st.markdown("#### With MeetupOps")
        st.write(
            "Participants, front-desk staff, and organizers use role-specific views backed "
            "by one shared Firestore event state."
        )

st.markdown("### One event, three connected experiences")
participant_col, cashier_col, organizer_col = st.columns(3)
with participant_col:
    with st.container(border=True):
        st.markdown("#### 🙋 Participant")
        st.write("1. Enter name and language")
        st.write("2. Receive a live table assignment")
        st.write("3. Join synchronized table activities")
with cashier_col:
    with st.container(border=True):
        st.markdown("#### 💳 Front desk")
        st.write("1. Assist check-in without a device")
        st.write("2. Optionally issue payment codes")
        st.write("3. Resolve participant status quickly")
with organizer_col:
    with st.container(border=True):
        st.markdown("#### 🎛️ Organizer")
        st.write("1. Configure and start each round")
        st.write("2. Monitor attendance and table balance")
        st.write("3. Override assignments when needed")

st.markdown("### Live assignment simulation")
st.write(
    "The sample below seats 24 fictional guests across three rounds. It prioritizes "
    "English/Japanese balance and reduces repeat meetings."
)

summaries, demo_rounds = build_demo()
metric_1, metric_2, metric_3, metric_4 = st.columns(4)
metric_1.metric("Participants", DEMO_PARTICIPANTS)
metric_2.metric("Rounds", DEMO_ROUNDS)
metric_3.metric("Tables per round", summaries[0]["Tables"])
metric_4.metric(
    "Balanced tables",
    f'{summaries[-1]["Language-balanced tables"]}/{summaries[-1]["Tables"]}',
)

st.dataframe(summaries, hide_index=True, width="stretch")

round_tabs = st.tabs([f"Round {round_number}" for round_number in range(1, DEMO_ROUNDS + 1)])
for round_index, round_tab in enumerate(round_tabs):
    with round_tab:
        tables = demo_rounds[round_index]
        table_columns = st.columns(3)
        for table_index, table_number in enumerate(
            sorted(tables, key=lambda value: int(value))
        ):
            with table_columns[table_index % 3]:
                with st.container(border=True):
                    st.markdown(f"**Table {table_number}**")
                    for guest in tables[table_number]:
                        language_icon = "🇬🇧" if guest["Language"] == "English" else "🇯🇵"
                        st.write(f'{language_icon} {guest["Name"]}')

with st.expander("Technical notes for reviewers"):
    st.markdown(
        """
- **Frontend:** Streamlit multi-role application with English/Japanese copy
- **Backend:** Firebase Admin SDK and Cloud Firestore shared event state
- **Core logic:** multi-round table assignment with capacity, language balance, and meeting-history constraints
- **Security:** runtime secrets, signed staff cookies, ignored service-account files, and cleaned Git history
- **Deployment:** Streamlit Community Cloud with a public read-only portfolio path

The simulation above calls the same assignment function as the live organizer workflow, but uses only fictional in-memory data.
"""
    )

st.success(
    "Want to inspect the real app? Choose **Staff / Participant Login** in the sidebar. "
    "Admin and Cashier demo password: **123456**. Participant login does not require a code."
)
