from pathlib import Path
from datetime import datetime
import pytz
from data.data_structure import Participant
from data.logic import assign_tables
from activities.registry import (
    create_activity_state,
    choose_random_activity_id,
    ACTIVITY_UNDERCOVER,
    ACTIVITY_STORY_CHAIN,
)
import random

import firebase_admin
from firebase_admin import credentials, firestore
from google.cloud.firestore import FieldFilter

SERVICE_ACCOUNT_PATH = Path(__file__).parent / "meetup-table-assign-firebase-adminsdk-fbsvc-fda1739a4a.json"
if not firebase_admin._apps:
    cred = credentials.Certificate(str(SERVICE_ACCOUNT_PATH))
    firebase_admin.initialize_app(cred)
db = firestore.client()

ROOT_COLLECTION = "meetups"
tz = pytz.timezone("Pacific/Auckland")
META_COLLECTION = "meta"
STATE_DOC_ID = "state"
ACTIVITIES_DOC_ID = "activities"

def _today_doc():
    return db.collection(ROOT_COLLECTION).document(str(datetime.now(tz=tz).date()))

def _state_ref():
    return _today_doc().collection(META_COLLECTION).document(STATE_DOC_ID)

def _activities_root_ref():
    return _today_doc().collection(META_COLLECTION).document(ACTIVITIES_DOC_ID)

def _activity_ref(round_no: int, table_no: str):
    return _activities_root_ref().collection(str(round_no)).document(str(table_no))

def get_event_state():
    doc = _state_ref().get()
    if not doc.exists:
        return {
            "started": False,
            "current_round": 0,
            "max_per_table": None,
            "min_per_table": None,
            "round_started_at": None,
            "round_duration_min": None,
            "table_counts": {},
        }
    data = doc.to_dict() or {}
    data.setdefault("started", False)
    data.setdefault("current_round", 0)
    data.setdefault("table_counts", {})
    data.setdefault("max_per_table", None)
    data.setdefault("min_per_table", None)
    data.setdefault("round_started_at", None)
    data.setdefault("round_duration_min", None)
    return data

def set_event_state(state: dict):
    _state_ref().set(state, merge=True)

def get_table_activity(round_no: int, table_no: str):
    doc = _activity_ref(round_no, table_no).get()
    if not doc.exists:
        return None
    return doc.to_dict() or None

def set_table_activity_doc(round_no: int, table_no: str, data: dict):
    _activity_ref(round_no, table_no).set(data, merge=True)


def get_active_participants_by_table(table_no: str):
    query = (
        _participants_ref()
        .where(filter=FieldFilter("status", "==", "Checked In"))
        .where(filter=FieldFilter("table_number", "==", str(table_no)))
        .stream()
    )
    return [Participant.from_dict(ans.to_dict()) for ans in query]


def ensure_table_activity(round_no: int, table_no: str, updated_by: str):
    """
    Ensure an activity exists for (round, table). If missing, pick random and init state.
    If exists but missing assignment for current user (due to late join), extend assignments.
    """
    doc = get_table_activity(round_no, table_no)
    if not doc or not doc.get("activity_id"):
        participants = get_active_participants_by_table(table_no)
        participant_ids = [p.id for p in participants]
        rng = random.Random()
        activity_id = choose_random_activity_id(rng)
        state = create_activity_state(activity_id, participant_ids, rng)
        new_doc = {
            "activity_id": activity_id,
            "state": state,
            "updated_by": updated_by,
            "updated_at": datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
        }
        set_table_activity_doc(round_no, table_no, new_doc)
        return new_doc

    # extend state for late joiners without reshuffling the whole table
    activity_id = doc.get("activity_id")
    state = doc.get("state") or {}
    if activity_id == ACTIVITY_UNDERCOVER:
        assignments = state.get("assignments") or {}
        if updated_by not in assignments:
            participants = get_active_participants_by_table(table_no)
            participant_ids = [p.id for p in participants]
            missing = [pid for pid in participant_ids if pid not in assignments]
            if missing:
                pair = (state.get("pair") or {})
                common = pair.get("common")
                if common:
                    for pid in missing:
                        assignments[pid] = common
                    state["assignments"] = assignments
                    doc["state"] = state
                    doc["updated_at"] = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                    set_table_activity_doc(round_no, table_no, {"state": state, "updated_at": doc["updated_at"]})
    elif activity_id == ACTIVITY_STORY_CHAIN:
        remaining = state.get("remaining") or {}
        quota = state.get("quota") or {}
        order = state.get("order") or []
        if updated_by not in remaining:
            participants = get_active_participants_by_table(table_no)
            participant_ids = [p.id for p in participants]
            missing = [pid for pid in participant_ids if pid not in remaining]
            if missing:
                rng = random.Random()
                for pid in missing:
                    q = rng.choice([2, 2, 3])
                    quota[pid] = int(q)
                    remaining[pid] = int(q)
                    if pid not in order:
                        order.append(pid)
                state["quota"] = quota
                state["remaining"] = remaining
                state["order"] = order
                state.setdefault("turn_idx", 0)
                # Backward-compatible: older docs might not have a prompt yet.
                state.setdefault("prompt", create_activity_state(ACTIVITY_STORY_CHAIN, participant_ids, rng).get("prompt"))
                doc["state"] = state
                doc["updated_at"] = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
                set_table_activity_doc(round_no, table_no, {"state": state, "updated_at": doc["updated_at"]})
    return doc


def _story_chain_next_turn_idx(order: list, remaining: dict, start_idx: int) -> int | None:
    if not order:
        return None
    n = len(order)
    for step in range(1, n + 1):
        i = (start_idx + step) % n
        pid = order[i]
        if int(remaining.get(pid, 0)) > 0:
            return i
    return None


@firestore.transactional
def _story_chain_finish_turn_txn(transaction, doc_ref, participant_id: str, updated_by: str):
    snap = doc_ref.get(transaction=transaction)
    if not snap.exists:
        raise ValueError("Activity doc not found")

    doc = snap.to_dict() or {}
    if doc.get("activity_id") != ACTIVITY_STORY_CHAIN:
        raise ValueError("Not a story chain activity")

    state = doc.get("state") or {}
    remaining = state.get("remaining") or {}
    quota = state.get("quota") or {}
    order = state.get("order") or []
    turn_idx = int(state.get("turn_idx") or 0)
    done = bool(state.get("done"))

    # late joiners: add quota/remaining on the fly
    if participant_id not in remaining:
        q = random.Random().choice([2, 2, 3])
        quota[participant_id] = int(q)
        remaining[participant_id] = int(q)
        if participant_id not in order:
            order.append(participant_id)

    if done:
        return doc

    current_pid = order[turn_idx] if order and 0 <= turn_idx < len(order) else None
    if current_pid != participant_id:
        # Not your turn -> no-op
        return doc

    r = int(remaining.get(participant_id, 0))
    if r > 0:
        remaining[participant_id] = r - 1

    # Determine if finished; else advance turn
    finished = all(int(v) <= 0 for v in remaining.values()) if remaining else True
    next_idx = None if finished else _story_chain_next_turn_idx(order, remaining, turn_idx)
    if next_idx is None and not finished:
        finished = True

    new_state = dict(state)
    new_state["quota"] = quota
    new_state["remaining"] = remaining
    new_state["order"] = order
    new_state["done"] = bool(finished)
    if next_idx is not None:
        new_state["turn_idx"] = int(next_idx)
    else:
        new_state["turn_idx"] = int(turn_idx)

    transaction.set(
        doc_ref,
        {
            "state": new_state,
            "updated_by": updated_by,
            "updated_at": datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
        },
        merge=True,
    )
    doc["state"] = new_state
    return doc


def story_chain_finish_turn(round_no: int, table_no: str, participant_id: str, updated_by: str):
    """
    Transaction-safe turn advance for Story Chain:
    decrement your remaining by 1 (only if it's your turn), then advance to next participant.
    """
    doc_ref = _activity_ref(round_no, table_no)
    transaction = db.transaction()
    return _story_chain_finish_turn_txn(transaction, doc_ref, participant_id, updated_by)


def story_chain_restart(round_no: int, table_no: str, updated_by: str):
    """
    Reset Story Chain within the same meetup round (not "Start Next Round").
    This clears done state, re-rolls quotas (2-3 each), resets turn index, and picks a new opening prompt.
    """
    participants = get_active_participants_by_table(table_no)
    participant_ids = sorted([p.id for p in participants])
    rng = random.Random()
    state = create_activity_state(ACTIVITY_STORY_CHAIN, participant_ids, rng)
    patch = {
        "activity_id": ACTIVITY_STORY_CHAIN,
        "state": state,
        "updated_by": updated_by,
        "updated_at": datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
    }
    set_table_activity_doc(round_no, table_no, patch)
    return patch


def switch_table_activity(round_no: int, table_no: str, updated_by: str):
    participants = get_active_participants_by_table(table_no)
    participant_ids = [p.id for p in participants]
    current = get_table_activity(round_no, table_no) or {}
    current_id = current.get("activity_id")
    rng = random.Random()
    new_id = choose_random_activity_id(rng, exclude=current_id)
    state = create_activity_state(new_id, participant_ids, rng)
    new_doc = {
        "activity_id": new_id,
        "state": state,
        "updated_by": updated_by,
        "updated_at": datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
    }
    set_table_activity_doc(round_no, table_no, new_doc)
    return new_doc


def regenerate_undercover_words(round_no: int, table_no: str, updated_by: str):
    """
    Regenerate word pair + undercover assignment for current table, staying in undercover activity.
    """
    participants = get_active_participants_by_table(table_no)
    participant_ids = [p.id for p in participants]
    rng = random.Random()
    state = create_activity_state(ACTIVITY_UNDERCOVER, participant_ids, rng)
    patch = {
        "activity_id": ACTIVITY_UNDERCOVER,
        "state": state,
        "updated_by": updated_by,
        "updated_at": datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S"),
    }
    set_table_activity_doc(round_no, table_no, patch)
    return patch

def _participants_ref():
    return _today_doc().collection("participants")

def login_user(id, name, language):
    query = _participants_ref().where(filter=FieldFilter("id", "==", id)).stream()
    results = [ans.to_dict() for ans in query]
    if len(results) > 0:
        user_data = results[0]
        # If the user is already checked-in and has a table, treat this as a "resume session"
        # to avoid double-seating and corrupting table_counts.
        if user_data.get("status") == "Checked In" and user_data.get("table_number"):
            user = Participant.from_dict(user_data)
            user.name = name.strip().title()
            user.language = language
            _participants_ref().document(user.id).set(user.to_dict())
            return id, user.name

        user = Participant(
            name=name,
            language=language,
            id=user_data["id"],
            table_number=user_data.get("table_number"),
            check_in_time=user_data.get("check_in_time"),
            status="Checked In",
            history=user_data.get("history", [])
        )
        user.check_in()
        user, persisted = _assign_table_if_event_started(user)
        if not persisted:
            _participants_ref().document(user.id).set(user.to_dict())
        return id, name
    else:
        return logup_user(name, language, id=id)

def logup_user(name, language, id=None):
    user = Participant(name=name, language=language, id=id)
    user.check_in()
    user, persisted = _assign_table_if_event_started(user)
    if not persisted:
        _participants_ref().document(user.id).set(user.to_dict())
    return user.id, user.name


def admin_add_participant(name: str, language: str) -> Participant:
    """
    Admin-side manual check-in (for users without devices).
    Returns the created Participant (may already be assigned a table if event started).
    """
    user = Participant(name=name, language=language)
    user.check_in()
    user, persisted = _assign_table_if_event_started(user)
    if not persisted:
        _participants_ref().document(user.id).set(user.to_dict())
    return user

def logout_user(id):
    query = _participants_ref().where(filter=FieldFilter("id", "==", id)).stream()
    results = [ans.to_dict() for ans in query]
    if len(results) > 0:
        user_data = results[0]
        user = Participant.from_dict(user_data)
        prev_table = user.table_number
        user.check_out()
        _participants_ref().document(user.id).set(user.to_dict())

        # If event is started, decrement table_counts so future joiners can fill freed seats.
        state = get_event_state()
        if state.get("started") and prev_table:
            table_counts = state.get("table_counts") or {}
            if str(prev_table) in table_counts:
                table_counts[str(prev_table)] = max(0, int(table_counts.get(str(prev_table), 0)) - 1)
                if table_counts[str(prev_table)] == 0:
                    table_counts.pop(str(prev_table), None)
                state["table_counts"] = table_counts
                set_event_state(state)
    else:
        raise ValueError("Participant not found")

def get_my_status(id):
    query = _participants_ref().where(filter=FieldFilter("id", "==", id)).stream()
    results = [ans.to_dict() for ans in query]
    if len(results) > 0:
        user_data = results[0]
        return Participant.from_dict(user_data)
    else:
        raise ValueError("Participant not found")

def get_all_participants():
    query = _participants_ref().stream()
    return [Participant.from_dict(ans.to_dict()) for ans in query]

def get_active_participants():
    query = _participants_ref().where(filter=FieldFilter("status", "==", "Checked In")).stream()
    return [Participant.from_dict(ans.to_dict()) for ans in query]

def batch_update_participants(participants):
    batch = db.batch()
    today_ref = _participants_ref()
    for participant in participants:
        doc_ref = today_ref.document(participant.id)
        batch.set(doc_ref, participant.to_dict())
    batch.commit()

def _assign_table_if_event_started(user: Participant):
    """
    If event is started, immediately assign a table to a newly checked-in user.
    Policy:
    - Prefer existing tables with available capacity (< max_per_table), choose the least filled.
    - If all full, create a new table.
    - Update `history` mates for both the new user and existing table-mates (best-effort).
    """
    state = get_event_state()
    if not state.get("started"):
        return user, False

    max_per_table = state.get("max_per_table")
    current_round = int(state.get("current_round") or 0)
    if not max_per_table:
        # started but missing config; best-effort: don't assign
        return user, False

    table_counts = state.get("table_counts") or {}
    # Find an existing table with free slots
    candidate_tables = [(int(tno), int(cnt)) for tno, cnt in table_counts.items()]
    candidate_tables = [(tno, cnt) for tno, cnt in candidate_tables if cnt < int(max_per_table)]
    if candidate_tables:
        candidate_tables.sort(key=lambda x: (x[1], x[0]))  # least filled, then smallest no
        chosen = candidate_tables[0][0]
    else:
        chosen = (max([int(tno) for tno in table_counts.keys()] or [0]) + 1)

    table_no = str(chosen)

    # Fetch current mates at that table
    mates_query = _participants_ref().where(filter=FieldFilter("status", "==", "Checked In")).where(
        filter=FieldFilter("table_number", "==", table_no)
    ).stream()
    mates = [Participant.from_dict(doc.to_dict()) for doc in mates_query]
    mate_ids = [m.id for m in mates]

    now_str = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
    user.table_number = table_no
    user.history = user.history or []
    user.history.append(
        {"at": now_str, "round": current_round, "table_number": table_no, "mates": mate_ids, "join": True}
    )

    # Update mates' history to include the newcomer in the same round/table (best-effort)
    for m in mates:
        m.history = m.history or []
        updated = False
        for entry in reversed(m.history):
            if isinstance(entry, dict) and entry.get("round") == current_round and entry.get("table_number") == table_no:
                mates_list = entry.get("mates")
                if isinstance(mates_list, list):
                    if user.id not in mates_list:
                        mates_list.append(user.id)
                    entry["mates"] = mates_list
                else:
                    entry["mates"] = [user.id]
                updated = True
                break
        if not updated:
            m.history.append(
                {"at": now_str, "round": current_round, "table_number": table_no, "mates": [user.id], "join_update": True}
            )

    # Persist updates (participants + event state)
    batch = db.batch()
    today_ref = _participants_ref()
    batch.set(today_ref.document(user.id), user.to_dict())
    for m in mates:
        batch.set(today_ref.document(m.id), m.to_dict())

    # Update state counts
    table_counts[table_no] = int(table_counts.get(table_no, 0)) + 1
    state["table_counts"] = table_counts
    batch.set(_state_ref(), state, merge=True)
    batch.commit()

    return user, True

def start_next_round(target_per_table: int, min_per_table: int):
    active_participants = get_active_participants()
    total_count = len(active_participants)
    if total_count == 0:
        return 0

    state = get_event_state()
    next_round = int(state.get("current_round") or 0) + 1

    updated_participants, num_tables = assign_tables(
        active_participants,
        target_per_table=target_per_table,
        min_per_table=min_per_table,
        round_number=next_round,
    )
    batch_update_participants(updated_participants)

    # Update event state so newcomers can be seated immediately
    table_counts = {}
    for p in updated_participants:
        if p.table_number:
            table_counts[str(p.table_number)] = int(table_counts.get(str(p.table_number), 0)) + 1
    state["started"] = True
    state["max_per_table"] = target_per_table
    state["min_per_table"] = min_per_table
    state["current_round"] = next_round
    state["table_counts"] = table_counts
    # Timer is started separately by admin action
    state["round_started_at"] = None
    state["round_duration_min"] = None
    set_event_state(state)

    return num_tables


def start_round_timer(round_duration_min: int = 30) -> bool:
    """
    Start (or restart) the round timer without changing table assignments.
    Returns True if timer started, False if no active round.
    """
    state = get_event_state()
    if int(state.get("current_round") or 0) <= 0:
        return False
    state["round_started_at"] = datetime.now(tz=tz).isoformat()
    state["round_duration_min"] = int(round_duration_min)
    set_event_state(state)
    return True


def reset_event():
    participants = get_active_participants()
    for p in participants:
        p.table_number = None
        
    batch_update_participants(participants)
    set_event_state(
        {
            "started": False,
            "current_round": 0,
            "max_per_table": None,
            "min_per_table": None,
            "round_started_at": None,
            "round_duration_min": None,
            "table_counts": {},
        }
    )
    

def create_test_participants(n_en: int, n_jp: int, name_prefix: str = "SimUser", tag: str | None = None):
    """
    Create test participants in today's collection.
    These records are marked with is_test=True and optional test_tag for safe cleanup.
    """
    participants = []
    for i in range(n_en):
        p = Participant(name=f"{name_prefix}-EN-{i+1}", language="English")
        p.check_in()
        participants.append(p)
    for i in range(n_jp):
        p = Participant(name=f"{name_prefix}-JP-{i+1}", language="Japanese")
        p.check_in()
        participants.append(p)

    batch = db.batch()
    today_ref = _participants_ref()
    for p in participants:
        data = p.to_dict()
        data["is_test"] = True
        if tag:
            data["test_tag"] = tag
        batch.set(today_ref.document(p.id), data)
    batch.commit()
    return participants


def clear_test_participants(tag: str | None = None) -> int:
    """
    Delete test participants from today's collection.
    If tag is provided, only deletes records with matching test_tag.
    Returns number of deleted documents.
    """
    query = _participants_ref().where(filter=FieldFilter("is_test", "==", True)).stream()
    docs = list(query)
    if tag:
        docs = [d for d in docs if d.to_dict().get("test_tag") == tag]

    if not docs:
        return 0

    batch = db.batch()
    for d in docs:
        batch.delete(d.reference)
    batch.commit()
    return len(docs)


def get_test_participants(tag: str | None = None):
    """
    Return test participant docs (raw dicts), optionally filtered by test_tag.
    """
    query = _participants_ref().where(filter=FieldFilter("is_test", "==", True)).stream()
    docs = [d.to_dict() for d in query]
    if tag:
        docs = [d for d in docs if d.get("test_tag") == tag]
    return docs
    