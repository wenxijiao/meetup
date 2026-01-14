from __future__ import annotations

import math
import random
from datetime import datetime
from typing import Dict, List, Optional, Set, Tuple

import pytz

from data.data_structure import Participant

tz = pytz.timezone("Pacific/Auckland")

def _snapshot_tables(tables: List[List[Participant]]) -> List[List[dict]]:
    return [
        [{"id": p.id, "name": p.name, "language": p.language} for p in t]
        for t in tables
    ]

def _repeat_pairs_in_tables(tables: List[List[Participant]]) -> int:
    # Build met-before map from history
    met_before: Dict[str, Set[str]] = {}
    for t in tables:
        for p in t:
            met_before[p.id] = _met_before_ids(p)

    repeat_pairs = 0
    for t in tables:
        ids = [p.id for p in t]
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if b in met_before.get(a, set()) or a in met_before.get(b, set()):
                    repeat_pairs += 1
    return repeat_pairs

def _has_english(p: Participant) -> bool:
    return "English" in str(p.language)

def _has_japanese(p: Participant) -> bool:
    return "Japanese" in str(p.language)

def _met_before_ids(p: Participant) -> Set[str]:
    """
    Returns a set of participant ids that `p` has been seated with before.
    We rely on history entries like: {"at": "...", "table_number": "1", "mates": ["id1", ...]}
    """
    met: Set[str] = set()
    if not p.history:
        return met
    for entry in p.history:
        if not isinstance(entry, dict):
            continue
        mates = entry.get("mates")
        if isinstance(mates, list):
            for mid in mates:
                if isinstance(mid, str) and mid:
                    met.add(mid)
    # Never count self
    met.discard(getattr(p, "id", None))
    return met

def _last_round_mates(p: Participant) -> Set[str]:
    """
    Return mates from the most recent round (by max round number).
    Falls back to empty set if no round info.
    """
    if not p.history:
        return set()
    last_round = None
    last_mates: Set[str] = set()
    for entry in p.history:
        if not isinstance(entry, dict):
            continue
        r = entry.get("round")
        mates = entry.get("mates")
        if r is None or not isinstance(mates, list):
            continue
        try:
            r_int = int(r)
        except Exception:
            continue
        if (last_round is None) or (r_int > last_round):
            last_round = r_int
            last_mates = {m for m in mates if isinstance(m, str)}
    last_mates.discard(getattr(p, "id", None))
    return last_mates

def _choose_table_count(
    total: int,
    max_per_table: int,
    min_per_table: int,
    en_count: int,
    jp_count: int,
) -> int:
    """
    Choose a table count that:
    1) Is feasible w.r.t. min/max sizes when possible.
    2) Is as close to `max_per_table` as possible (i.e., minimize table count).
    3) Language mix is handled during assignment (best-effort) after table count is chosen.
    """
    if total <= 0:
        return 0

    def size_distribution(t: int) -> List[int]:
        base = total // t
        rem = total % t
        return [base + 1] * rem + [base] * (t - rem)

    # Preferred feasible range:
    # - Need enough tables so no table exceeds max_per_table => tables >= ceil(total / max_per_table)
    # - Not too many tables so each can have >= min_per_table => tables <= floor(total / min_per_table)
    t_min = max(1, math.ceil(total / max_per_table))
    t_max = max(1, total // min_per_table)

    if t_max >= t_min:
        # Feasible: choose the smallest table count => tables as full as possible (close to max_per_table)
        return t_min

    # Infeasible to satisfy both min and max simultaneously.
    # Pick the table count that minimizes constraint violations (prefer not exceeding max),
    # and then prefers fewer tables (closer to max_per_table).
    best: Optional[Tuple[int, int, int]] = None  # (violate_max, violate_min, t)
    for t in range(1, total + 1):
        sizes = size_distribution(t)
        violate_max = sum(max(0, s - max_per_table) for s in sizes)
        violate_min = sum(max(0, min_per_table - s) for s in sizes)
        key = (violate_max, violate_min, t)
        if best is None or key < best:
            best = key
    return best[2] if best else 1

def _seed_tables_for_language(
    tables: List[List[Participant]],
    participants: List[Participant],
) -> List[Participant]:
    """
    Greedily seed each table to try to get at least one EN and one JP.
    Returns remaining participants.
    """
    # Split into buckets
    both: List[Participant] = []
    en_only: List[Participant] = []
    jp_only: List[Participant] = []
    other: List[Participant] = []

    for p in participants:
        has_en = _has_english(p)
        has_jp = _has_japanese(p)
        if has_en and has_jp:
            both.append(p)
        elif has_en:
            en_only.append(p)
        elif has_jp:
            jp_only.append(p)
        else:
            other.append(p)

    random.shuffle(both)
    random.shuffle(en_only)
    random.shuffle(jp_only)
    random.shuffle(other)

    def pick_best(candidates: List[Participant], table: List[Participant]) -> Participant:
        """
        Pick a candidate that minimizes repeat pairing with current table.
        Ties are broken randomly.
        """
        if len(candidates) == 1:
            return candidates.pop()
        best_idx = 0
        best_cost = 10**9
        tie_indices = []
        for idx, cand in enumerate(candidates):
            met = _met_before_ids(cand)
            last = _last_round_mates(cand)
            cost = sum(1 for m in table if m.id in met) + 3 * sum(1 for m in table if m.id in last)
            if cost < best_cost:
                best_cost = cost
                tie_indices = [idx]
            elif cost == best_cost:
                tie_indices.append(idx)
        chosen_idx = random.choice(tie_indices)
        return candidates.pop(chosen_idx)

    # Pass 1: place EN-only into each table if possible
    for i in range(len(tables)):
        if en_only:
            tables[i].append(pick_best(en_only, tables[i]))

    # Pass 2: ensure JP presence: prefer JP-only; else use bilingual; else leave unsatisfied
    for i in range(len(tables)):
        if any(_has_japanese(x) for x in tables[i]):
            continue
        if jp_only:
            tables[i].append(pick_best(jp_only, tables[i]))
        elif both:
            tables[i].append(pick_best(both, tables[i]))

    # Pass 3: ensure EN presence similarly (for tables that got only JP or only bilingual missing EN)
    for i in range(len(tables)):
        if any(_has_english(x) for x in tables[i]):
            continue
        if en_only:
            tables[i].append(pick_best(en_only, tables[i]))
        elif both:
            tables[i].append(pick_best(both, tables[i]))

    remaining = both + en_only + jp_only + other
    random.shuffle(remaining)
    return remaining

def _fill_tables_min_repeat(
    tables: List[List[Participant]],
    remaining: List[Participant],
    max_per_table: int,
    debug: Optional[dict] = None,
) -> None:
    """
    Fill tables up to max_per_table, minimizing repeated pairings.
    Greedy: place each participant into the table that causes the smallest increase in repeats.
    """
    met_cache: Dict[str, Set[str]] = {p.id: _met_before_ids(p) for p in remaining}
    last_cache: Dict[str, Set[str]] = {p.id: _last_round_mates(p) for p in remaining}
    for t in tables:
        for p in t:
            met_cache.setdefault(p.id, _met_before_ids(p))
            last_cache.setdefault(p.id, _last_round_mates(p))

    def incremental_cost(p: Participant, table: List[Participant]) -> int:
        met = met_cache.get(p.id, set())
        last = last_cache.get(p.id, set())
        return sum(1 for m in table if m.id in met) + 3 * sum(1 for m in table if m.id in last)

    for p in remaining:
        sizes_before = [len(t) for t in tables]
        best_i: Optional[int] = None
        best_cost = 10**9
        best_size = 10**9
        for i, t in enumerate(tables):
            if len(t) >= max_per_table:
                continue
            cost = incremental_cost(p, t)
            # Tie-break: prefer smaller table (helps meet min evenly)
            if cost < best_cost or (cost == best_cost and len(t) < best_size):
                best_cost = cost
                best_size = len(t)
                best_i = i
        if best_i is None:
            # Shouldn't happen if table count was chosen correctly, but be safe:
            # put into the smallest table.
            best_i = min(range(len(tables)), key=lambda i: len(tables[i]))
        tables[best_i].append(p)
        if debug is not None:
            debug.setdefault("placements", []).append(
                {
                    "participant": {"id": p.id, "name": p.name, "language": p.language},
                    "chosen_table_index": best_i,
                    "incremental_repeat_cost": best_cost,
                    "table_sizes_before": sizes_before,
                    "table_sizes_after": [len(t) for t in tables],
                }
            )

def assign_tables(
    participants: List[Participant],
    target_per_table: int,
    min_per_table: int,
    round_number: Optional[int] = None,
) -> Tuple[List[Participant], int]:
    """
    Assign `table_number` for participants.

    - Chooses a table count that tries to respect `target_per_table`, while ensuring
      each table has at least `min_per_table` participants when possible.
    - Shuffles participants to make allocation fair/simple.
    - Appends a small entry into `history` for each assignment.
    """
    total_count = len(participants)
    if total_count == 0:
        return [], 0

    max_per_table = target_per_table  # treat "target" as a hard max for your priority order

    # Count languages
    en_count = sum(1 for p in participants if _has_english(p))
    jp_count = sum(1 for p in participants if _has_japanese(p))

    num_tables = _choose_table_count(
        total=total_count,
        max_per_table=max_per_table,
        min_per_table=min_per_table,
        en_count=en_count,
        jp_count=jp_count,
    )
    if num_tables <= 0:
        return [], 0

    # Initialize tables
    tables: List[List[Participant]] = [[] for _ in range(num_tables)]
    pool = list(participants)
    random.shuffle(pool)

    # 1) Seed for language mix (best effort)
    debug: dict = {"phases": []}

    debug["phases"].append({"name": "after_choose_table_count", "tables": _snapshot_tables(tables)})

    remaining = _seed_tables_for_language(tables, pool)
    debug["phases"].append({"name": "after_language_seeding", "tables": _snapshot_tables(tables)})

    # 2) Fill remaining minimizing repeats (best effort)
    _fill_tables_min_repeat(tables, remaining, max_per_table=max_per_table, debug=debug)
    debug["phases"].append({"name": "after_fill_min_repeat", "tables": _snapshot_tables(tables)})

    # 3) Validate min_per_table best effort by moving from larger tables to smaller ones
    # (rarely needed if table count chosen correctly)
    def smallest_idx() -> int:
        return min(range(num_tables), key=lambda i: len(tables[i]))

    def largest_idx() -> int:
        return max(range(num_tables), key=lambda i: len(tables[i]))

    guard = 0
    while guard < 500:
        guard += 1
        si = smallest_idx()
        li = largest_idx()
        if len(tables[si]) >= min_per_table:
            break
        if len(tables[li]) <= min_per_table:
            break
        # Move a participant from largest to smallest with minimal repeat penalty
        candidate = None
        best_delta = 10**9
        for p in list(tables[li]):
            # Avoid breaking language mix too much: keep at least one EN/JP when possible
            li_after = [x for x in tables[li] if x.id != p.id]
            if any(_has_english(x) for x in tables[li]) and not any(_has_english(x) for x in li_after):
                continue
            if any(_has_japanese(x) for x in tables[li]) and not any(_has_japanese(x) for x in li_after):
                continue

            met = _met_before_ids(p)
            delta = sum(1 for m in tables[si] if m.id in met)
            if delta < best_delta:
                best_delta = delta
                candidate = p
        if candidate is None:
            candidate = tables[li][-1]
        tables[li].remove(candidate)
        tables[si].append(candidate)

    # 4) Assign table numbers and write mate history
    now_str = datetime.now(tz=tz).strftime("%Y-%m-%d %H:%M:%S")
    updated: List[Participant] = []
    for idx, table in enumerate(tables, start=1):
        table_no = str(idx)
        ids = [p.id for p in table]
        for p in table:
            p.table_number = table_no
            if p.history is None:
                p.history = []
            mates = [mid for mid in ids if mid != p.id]
            entry = {"at": now_str, "table_number": table_no, "mates": mates}
            if round_number is not None:
                entry["round"] = int(round_number)
            p.history.append(entry)
            updated.append(p)

    # Stash last debug snapshot in module-level for optional inspection tools/pages.
    # This is intentionally best-effort and should not be relied upon in production logic.
    global _LAST_ASSIGN_DEBUG
    _LAST_ASSIGN_DEBUG = debug

    return updated, num_tables

def assign_tables_debug(
    participants: List[Participant],
    max_per_table: int,
    min_per_table: int,
    round_number: Optional[int] = None,
) -> Tuple[List[Participant], int, dict]:
    """
    Same as `assign_tables`, but returns a `debug` dict you can use to visualize the process.
    This does NOT touch Firestore; it only mutates the provided Participant objects in memory.
    """
    debug: dict = {}
    total_count = len(participants)
    debug["inputs"] = {
        "total": total_count,
        "max_per_table": max_per_table,
        "min_per_table": min_per_table,
        "en_count": sum(1 for p in participants if _has_english(p)),
        "jp_count": sum(1 for p in participants if _has_japanese(p)),
    }

    updated, num_tables = assign_tables(
        participants=participants,
        target_per_table=max_per_table,
        min_per_table=min_per_table,
        round_number=round_number,
    )

    # Rebuild tables for summary/snapshots
    tables: List[List[Participant]] = [[] for _ in range(num_tables)]
    for p in updated:
        if p.table_number is None:
            continue
        idx = int(p.table_number) - 1
        if 0 <= idx < num_tables:
            tables[idx].append(p)

    debug["result"] = {
        "chosen_tables": num_tables,
        "table_sizes": [len(t) for t in tables],
        "tables_snapshot": _snapshot_tables(tables),
        "tables_mixed_count": sum(
            1
            for t in tables
            if any(_has_english(x) for x in t) and any(_has_japanese(x) for x in t)
        ),
        "repeat_pairs_in_round": _repeat_pairs_in_tables(tables),
    }

    return updated, num_tables, debug

def decide_table_count(total_count: int, target_per_table: int, min_per_table: int) -> int:
    """
    Decide table count given constraints:
    - Prefer close to `target_per_table` (i.e., fewer tables).
    - Ensure every table has at least `min_per_table` when feasible (i.e., not too many tables).
    """
    if total_count <= 0:
        return 1

    min_tables = max(1, math.ceil(total_count / target_per_table))
    max_tables = max(1, total_count // min_per_table)

    # If constraints conflict, prioritize min_per_table (avoid tiny tables),
    # even if that means exceeding target_per_table.
    if max_tables < min_tables:
        return max_tables

    return min_tables

def reset_event():
    pass
