from datetime import datetime, timedelta
import pytz
from data.data_structure import Participant
from data.logic import assign_tables
from app_config import get_firebase_service_account
import secrets
import string
from google.api_core.exceptions import AlreadyExists
from google.auth.exceptions import DefaultCredentialsError
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

if not firebase_admin._apps:
    service_account = get_firebase_service_account()
    if service_account:
        firebase_admin.initialize_app(credentials.Certificate(service_account))
    else:
        # Cloud Run and local `gcloud auth application-default login` use ADC.
        firebase_admin.initialize_app()
try:
    db = firestore.client()
except DefaultCredentialsError as exc:
    raise RuntimeError(
        "Firebase credentials are not configured. Add "
        "FIREBASE_SERVICE_ACCOUNT_JSON to Streamlit Secrets or configure ADC."
    ) from exc

ROOT_COLLECTION = "meetups"
tz = pytz.timezone("Pacific/Auckland")
META_COLLECTION = "meta"
STATE_DOC_ID = "state"
ACTIVITIES_DOC_ID = "activities"
PAYMENT_CODES_COLLECTION = "payment_codes"

# Data retention (best-effort cleanup). We store each event under meetups/{YYYY-MM-DD}/...
RETENTION_DAYS = 7

def _today_doc():
    return db.collection(ROOT_COLLECTION).document(str(datetime.now(tz=tz).date()))

def _state_ref():
    return _today_doc().collection(META_COLLECTION).document(STATE_DOC_ID)

def _activities_root_ref():
    return _today_doc().collection(META_COLLECTION).document(ACTIVITIES_DOC_ID)

def _payment_codes_ref():
    return _today_doc().collection(PAYMENT_CODES_COLLECTION)

def _activity_ref(round_no: int, table_no: str):
    return _activities_root_ref().collection(str(round_no)).document(str(table_no))

def _delete_collection_recursive(col_ref, *, batch_size: int = 200) -> int:
    """
    Recursively delete all documents in a collection (and their subcollections).
    Returns number of deleted documents (best-effort count).
    """
    deleted = 0
    while True:
        snaps = list(col_ref.limit(batch_size).stream())
        if not snaps:
            break

        batch = db.batch()
        for snap in snaps:
            # delete subcollections first
            for sub_col in snap.reference.collections():
                deleted += _delete_collection_recursive(sub_col, batch_size=batch_size)
            batch.delete(snap.reference)
            deleted += 1
        batch.commit()
    return deleted


def _delete_document_recursive(doc_ref, *, batch_size: int = 200) -> int:
    """
    Recursively delete a document and all its subcollections.
    Returns number of deleted documents including itself (best-effort count).
    """
    deleted = 0
    for col in doc_ref.collections():
        deleted += _delete_collection_recursive(col, batch_size=batch_size)
    doc_ref.delete()
    deleted += 1
    return deleted


def cleanup_old_meetups(*, retention_days: int = RETENTION_DAYS, batch_size: int = 200) -> int:
    """
    Delete meetup documents older than retention_days (based on doc id 'YYYY-MM-DD').
    This keeps Firestore storage small and avoids accumulating old activity data.
    Returns number of top-level meetup docs deleted (not total sub-doc count).
    """
    cutoff_date = datetime.now(tz=tz).date() - timedelta(days=int(retention_days))
    cutoff_id = str(cutoff_date)  # 'YYYY-MM-DD'

    root = db.collection(ROOT_COLLECTION)
    snaps = list(root.stream())
    old = [s for s in snaps if isinstance(s.id, str) and s.id < cutoff_id]

    deleted_top = 0
    for s in old:
        _delete_document_recursive(s.reference, batch_size=batch_size)
        deleted_top += 1
    return deleted_top

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
            "last_cleanup_date": None,
            "payment_codes_total": 0,
            "payment_codes_unused": 0,
            # Participant payment gate (one-time payment code).
            # If True, participant login requires a valid unused payment code unless already paid today.
            "payment_code_required": True,
        }
    data = doc.to_dict() or {}
    data.setdefault("started", False)
    data.setdefault("current_round", 0)
    data.setdefault("table_counts", {})
    data.setdefault("max_per_table", None)
    data.setdefault("min_per_table", None)
    data.setdefault("round_started_at", None)
    data.setdefault("round_duration_min", None)
    data.setdefault("last_cleanup_date", None)
    data.setdefault("payment_codes_total", 0)
    data.setdefault("payment_codes_unused", 0)
    data.setdefault("payment_code_required", True)
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

def _now_str():
    return datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")

def _generate_code(length: int = 6) -> str:
    # Digits-only is easiest to speak at a front desk.
    alphabet = string.digits
    return "".join(secrets.choice(alphabet) for _ in range(int(length)))

def _create_single_payment_code(*, code_length: int = 6, created_by: str = "auto") -> str:
    """
    Create ONE unused payment code document (doc id == code).
    Retries on rare collisions.
    Returns the created code.
    """
    code_length = int(code_length)
    now = _now_str()
    for _ in range(30):
        code = _generate_code(code_length)
        ref = _payment_codes_ref().document(code)
        try:
            ref.create(
                {
                    "code": code,
                    "status": "unused",
                    "created_at": now,
                    "created_by": created_by,
                }
            )
            return code
        except AlreadyExists:
            continue
    raise RuntimeError("Failed to generate a unique payment code (too many collisions)")

def ensure_payment_codes(*, min_unused: int = 1, code_length: int = 6, created_by: str = "auto") -> int:
    """
    Ensure there are at least min_unused unused codes for today.
    Returns number of newly created codes.
    """
    state = get_event_state()
    unused = int(state.get("payment_codes_unused") or 0)
    need = max(0, int(min_unused) - unused)
    if need <= 0:
        return 0

    created = 0
    for _ in range(need):
        _create_single_payment_code(code_length=code_length, created_by=created_by)
        created += 1

    _state_ref().set(
        {
            "payment_codes_total": firestore.Increment(created),
            "payment_codes_unused": firestore.Increment(created),
        },
        merge=True,
    )
    return created

def generate_payment_codes(*, n: int = 50, code_length: int = 6, created_by: str = "cashier") -> int:
    """
    Create N new unused payment codes for today.
    Returns number of codes actually created.
    """
    n = int(n)
    if n <= 0:
        return 0
    code_length = int(code_length)
    created = 0
    for _ in range(n):
        _create_single_payment_code(code_length=code_length, created_by=created_by)
        created += 1

    # Update counters (fast reads on cashier page)
    _state_ref().set(
        {
            "payment_codes_total": firestore.Increment(created),
            "payment_codes_unused": firestore.Increment(created),
        },
        merge=True,
    )
    return created

def get_next_unused_payment_code() -> str | None:
    """
    Returns one unused code (best-effort). Avoid scanning by limiting to 1.
    """
    q = _payment_codes_ref().where(filter=FieldFilter("status", "==", "unused")).limit(1).stream()
    docs = list(q)
    if not docs:
        # Auto-create so the cashier never gets stuck.
        ensure_payment_codes(min_unused=1, created_by="auto")
        q2 = _payment_codes_ref().where(filter=FieldFilter("status", "==", "unused")).limit(1).stream()
        docs2 = list(q2)
        if not docs2:
            return None
        return str(docs2[0].id)
    return str(docs[0].id)

@firestore.transactional
def _void_payment_code_txn(transaction, code_ref, *, voided_by: str, reason: str | None):
    snap = code_ref.get(transaction=transaction)
    if not snap.exists:
        return False
    data = snap.to_dict() or {}
    if data.get("status") != "unused":
        # Already used/voided -> nothing to do
        return False

    transaction.update(
        code_ref,
        {
            "status": "void",
            "voided_at": _now_str(),
            "voided_by": (voided_by or "").strip() or "cashier",
            "void_reason": (reason or "").strip() or None,
        },
    )
    transaction.set(
        _state_ref(),
        {"payment_codes_unused": firestore.Increment(-1)},
        merge=True,
    )
    return True


def void_payment_code(code: str, *, voided_by: str = "cashier", reason: str | None = "manual_skip") -> bool:
    """
    Mark a payment code as unusable (void) so cashier can move on if a code is problematic.
    - Only affects codes with status == 'unused'
    - Transaction-safe
    Returns True if the code was voided, False otherwise.
    """
    code = (code or "").strip()
    if not code:
        return False
    code_ref = _payment_codes_ref().document(code)
    transaction = db.transaction()
    ok = bool(_void_payment_code_txn(transaction, code_ref, voided_by=voided_by, reason=reason))
    if ok:
        # Keep the pipeline filled so cashier never gets stuck.
        ensure_payment_codes(min_unused=1, created_by="auto")
    return ok

@firestore.transactional
def _redeem_payment_code_txn(transaction, code_ref, *, used_by_id: str, used_by_name: str):
    snap = code_ref.get(transaction=transaction)
    if not snap.exists:
        raise ValueError("Invalid code")
    data = snap.to_dict() or {}
    if data.get("status") != "unused":
        raise ValueError("Code already used")

    transaction.update(
        code_ref,
        {
            "status": "used",
            "used_at": _now_str(),
            "used_by_id": used_by_id,
            "used_by_name": used_by_name,
        },
    )
    transaction.set(
        _state_ref(),
        {"payment_codes_unused": firestore.Increment(-1)},
        merge=True,
    )
    return True

def redeem_payment_code(code: str, *, used_by_id: str, used_by_name: str) -> bool:
    """
    Atomically mark a payment code as used (one-time).
    Raises ValueError if invalid/used.
    """
    code = (code or "").strip()
    if not code:
        raise ValueError("Code is required")
    code_ref = _payment_codes_ref().document(code)
    transaction = db.transaction()
    ok = bool(_redeem_payment_code_txn(transaction, code_ref, used_by_id=used_by_id, used_by_name=used_by_name))
    # Auto-generate the "next" code so cashier always has codes without clicking.
    if ok:
        ensure_payment_codes(min_unused=1, created_by="auto")
    return ok

def checkin_with_optional_payment_code(id: str | None, name: str, language: str, payment_code: str | None):
    """
    Unified participant check-in:
    - If existing participant is already Checked In with a table: resume (no code).
    - Else if existing participant has paid=True: allow check-in (no code).
    - Else require a valid unused payment_code (redeem once), then mark paid on participant.
    Returns (participant_id, final_name).
    """
    name = (name or "").strip()
    language = (language or "").strip()
    if not name or not language:
        raise ValueError("Name and language are required")

    existing = None
    if id:
        try:
            existing = get_my_status(id)
        except Exception:
            existing = None

    # Resume session: already checked in & seated
    if existing and existing.status == "Checked In" and existing.table_number:
        existing.name = name.strip().title()
        existing.language = language
        _participants_ref().document(existing.id).set(existing.to_dict())
        return existing.id, existing.name

    # Already paid today -> no need to redeem again
    if existing and bool(getattr(existing, "paid", False)):
        participant_id, final_name = login_user(existing.id, name, language)
        return participant_id, final_name

    # Admin may disable payment code requirement for today/event.
    # If disabled, we treat the participant as paid so future logins won't re-prompt.
    try:
        state = get_event_state()
    except Exception:
        state = {}
    payment_required = bool(state.get("payment_code_required", True))
    if not payment_required:
        # check-in (create or update participant)
        if existing:
            participant_id, final_name = login_user(existing.id, name, language)
        else:
            participant_id, final_name = logup_user(name, language, id=(id or None))

        _participants_ref().document(participant_id).set(
            {"paid": True, "paid_code": "waived", "paid_at": _now_str()},
            merge=True,
        )
        return participant_id, final_name

    # Need a fresh one-time code
    if not payment_code:
        raise ValueError("Payment code is required")

    participant_id = existing.id if existing else (id or Participant(name=name, language=language).id)
    # redeem first (atomic). If later writes fail, code is still consumed (acceptable for simplicity).
    redeem_payment_code(payment_code, used_by_id=participant_id, used_by_name=name.strip().title())

    # check-in (create or update participant)
    if existing:
        participant_id, final_name = login_user(existing.id, name, language)
    else:
        participant_id, final_name = logup_user(name, language, id=participant_id)

    # mark paid on participant doc
    _participants_ref().document(participant_id).set(
        {"paid": True, "paid_code": (payment_code or "").strip(), "paid_at": _now_str()},
        merge=True,
    )
    return participant_id, final_name


def admin_add_participant(name: str, language: str, *, created_by_role: str = "admin") -> Participant:
    """
    Admin-side manual check-in (for users without devices).
    Returns the created Participant (may already be assigned a table if event started).
    """
    user = Participant(name=name, language=language)
    # Mark this record so dashboards can list "no-device/manual" participants separately.
    user.created_source = "manual"
    user.created_by_role = (created_by_role or "").strip() or "admin"
    user.check_in()
    # Manual check-in implies front desk has handled payment; allow later web login without code.
    user.paid = True
    user.paid_code = "manual"
    user.paid_at = _now_str()
    user, persisted = _assign_table_if_event_started(user)
    if not persisted:
        _participants_ref().document(user.id).set(user.to_dict())
    return user


@firestore.transactional
def _admin_override_table_txn(transaction, participant_ref, state_ref, *, new_table_no: str, updated_by: str):
    p_snap = participant_ref.get(transaction=transaction)
    if not p_snap.exists:
        raise ValueError("Participant not found")
    p_data = p_snap.to_dict() or {}

    state_snap = state_ref.get(transaction=transaction)
    state = (state_snap.to_dict() or {}) if state_snap.exists else {}

    prev_table = p_data.get("table_number")
    new_table_no = str(new_table_no)

    # Update participant table_number only (do NOT append to history; next round assignment shouldn't be affected).
    patch = {
        "table_number": new_table_no,
        "table_override": {
            "at": _now_str(),
            "by": (updated_by or "").strip() or "admin",
            "from": prev_table,
            "to": new_table_no,
            "round": int(state.get("current_round") or 0),
        },
    }
    transaction.set(participant_ref, patch, merge=True)

    # Keep event_state.table_counts consistent so late joiners seating stays sane.
    if bool(state.get("started")):
        table_counts = dict(state.get("table_counts") or {})
        if prev_table and prev_table != new_table_no:
            if str(prev_table) in table_counts:
                table_counts[str(prev_table)] = max(0, int(table_counts.get(str(prev_table), 0)) - 1)
                if int(table_counts.get(str(prev_table), 0)) <= 0:
                    table_counts.pop(str(prev_table), None)
        if new_table_no and prev_table != new_table_no:
            table_counts[str(new_table_no)] = int(table_counts.get(str(new_table_no), 0)) + 1
        transaction.set(state_ref, {"table_counts": table_counts}, merge=True)

    return {"from": prev_table, "to": new_table_no}


def admin_override_participant_table(participant_id: str, table_no: str, *, updated_by: str = "admin") -> dict:
    """
    Admin-only: move one participant to a specific table number for the CURRENT round.
    - Does not write `history` (so it won't affect next round assignment logic)
    - Best-effort updates event_state.table_counts for late-join seating
    Returns dict with {from, to}.
    """
    participant_id = (participant_id or "").strip()
    if not participant_id:
        raise ValueError("Participant id is required")
    table_no = (table_no or "").strip()
    if not table_no:
        raise ValueError("Table number is required")

    participant_ref = _participants_ref().document(participant_id)
    state_ref = _state_ref()
    transaction = db.transaction()
    return _admin_override_table_txn(
        transaction,
        participant_ref,
        state_ref,
        new_table_no=table_no,
        updated_by=updated_by,
    )

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
    # Best-effort cleanup to avoid accumulating old data in Firestore.
    # Throttled: run at most once per natural day.
    state = get_event_state()
    today_id = str(datetime.now(tz=tz).date())  # 'YYYY-MM-DD'
    if state.get("last_cleanup_date") != today_id:
        try:
            cleanup_old_meetups(retention_days=RETENTION_DAYS)
        except Exception:
            # Cleanup is non-critical; never block starting a round due to cleanup failure.
            pass
        state["last_cleanup_date"] = today_id
        # Persist immediately so repeated clicks today won't redo cleanup.
        set_event_state(state)

    active_participants = get_active_participants()
    total_count = len(active_participants)
    if total_count == 0:
        return 0

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
