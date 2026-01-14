from __future__ import annotations

import argparse
import random
from collections import defaultdict
from typing import Dict, List, Tuple

from data.data_structure import Participant
from data.logic import assign_tables


def make_language(r: float, p_en: float, p_jp: float, p_both: float, allow_bilingual: bool) -> str:
    # Ensure contains substrings "English"/"Japanese" to match current code checks
    if allow_bilingual and r < p_both:
        return "English & Japanese"
    if allow_bilingual:
        r -= p_both
    if r < p_en:
        return "English"
    return "Japanese"


def seed_fake_history(participants: List[Participant], tables: int, seed: int) -> None:
    """
    Generate one previous round history with mates, so we can see if the new round
    tries to avoid repeat pairings.
    """
    rng = random.Random(seed)
    shuffled = list(participants)
    rng.shuffle(shuffled)

    prev_tables: List[List[Participant]] = [[] for _ in range(tables)]
    for i, p in enumerate(shuffled):
        prev_tables[i % tables].append(p)

    for idx, t in enumerate(prev_tables, start=1):
        ids = [p.id for p in t]
        for p in t:
            mates = [mid for mid in ids if mid != p.id]
            p.history.append({"at": "FAKE_PREV", "table_number": str(idx), "mates": mates})


def analyze(tables: Dict[str, List[Participant]]) -> Tuple[int, int, int]:
    """
    Returns: (tables_total, tables_mixed, repeat_pairs)
    """
    mixed = 0
    repeat_pairs = 0

    # Build "met before" map from history
    met_before = {}
    for plist in tables.values():
        for p in plist:
            s = set()
            for e in p.history or []:
                if isinstance(e, dict) and isinstance(e.get("mates"), list):
                    for mid in e["mates"]:
                        if isinstance(mid, str):
                            s.add(mid)
            s.discard(p.id)
            met_before[p.id] = s

    for tno, plist in tables.items():
        has_en = any("English" in str(p.language) for p in plist)
        has_jp = any("Japanese" in str(p.language) for p in plist)
        if has_en and has_jp:
            mixed += 1

        ids = [p.id for p in plist]
        # Count repeats within table (pair counted once)
        for i in range(len(ids)):
            for j in range(i + 1, len(ids)):
                a, b = ids[i], ids[j]
                if b in met_before.get(a, set()) or a in met_before.get(b, set()):
                    repeat_pairs += 1

    return len(tables), mixed, repeat_pairs


def main() -> None:
    ap = argparse.ArgumentParser(description="Offline test for table assignment algorithm.")
    ap.add_argument("--total", type=int, default=50)
    ap.add_argument("--max", dest="max_per_table", type=int, default=4)
    ap.add_argument("--min", dest="min_per_table", type=int, default=2)
    ap.add_argument("--seed", type=int, default=1)
    ap.add_argument("--p_en", type=float, default=0.45, help="Probability of EN-only (excluding bilingual)")
    ap.add_argument("--p_jp", type=float, default=0.45, help="Probability of JP-only (excluding bilingual)")
    ap.add_argument("--p_both", type=float, default=0.10, help="Probability of bilingual")
    ap.add_argument("--allow_bilingual", action="store_true", help="Allow generating bilingual participants")
    ap.add_argument("--prev_tables", type=int, default=12, help="How many tables in fake previous round")
    args = ap.parse_args()

    if args.total <= 0:
        raise SystemExit("total must be > 0")
    if args.min_per_table <= 0:
        raise SystemExit("min must be > 0")
    if args.max_per_table < args.min_per_table:
        raise SystemExit("max must be >= min")

    # Normalize probabilities
    s = args.p_en + args.p_jp + args.p_both
    if abs(s - 1.0) > 1e-6:
        args.p_en /= s
        args.p_jp /= s
        args.p_both /= s

    rng = random.Random(args.seed)
    participants: List[Participant] = []
    for i in range(args.total):
        lang = make_language(rng.random(), args.p_en, args.p_jp, args.p_both, args.allow_bilingual)
        p = Participant(name=f"User{i+1}", language=lang)
        participants.append(p)

    # Add a fake previous round history to test priority (3)
    seed_fake_history(participants, tables=max(1, args.prev_tables), seed=args.seed + 999)

    updated, num_tables = assign_tables(
        participants,
        target_per_table=args.max_per_table,
        min_per_table=args.min_per_table,
    )

    # Group tables
    tables: Dict[str, List[Participant]] = defaultdict(list)
    for p in updated:
        tables[str(p.table_number)].append(p)

    # Print summary
    print("=== Simulation Summary ===")
    print(f"total={args.total}  max={args.max_per_table}  min={args.min_per_table}  chosen_tables={num_tables}")
    print(f"lang mix: p_en={args.p_en:.2f} p_jp={args.p_jp:.2f} p_both={args.p_both:.2f}")

    tables_total, mixed, repeat_pairs = analyze(tables)
    print(f"tables_total={tables_total}  tables_mixed(en+jp)={mixed}  repeat_pairs_in_round={repeat_pairs}")
    print("")

    # Per-table details
    for tno in sorted(tables.keys(), key=lambda x: int(x)):
        plist = tables[tno]
        has_en = any("English" in str(p.language) for p in plist)
        has_jp = any("Japanese" in str(p.language) for p in plist)
        langs = [p.language for p in plist]
        print(
            f"Table {tno:>2}: size={len(plist)}  EN={has_en}  JP={has_jp}  langs={langs}"
        )

    # Hard checks for (1)
    bad_max = [tno for tno, plist in tables.items() if len(plist) > args.max_per_table]
    bad_min = [tno for tno, plist in tables.items() if len(plist) < args.min_per_table]
    if bad_max or bad_min:
        print("\n!!! Size constraint violations detected !!!")
        if bad_max:
            print(" > exceeded max on tables:", bad_max)
        if bad_min:
            print(" > below min on tables:", bad_min)
    else:
        print("\nOK: table sizes satisfy min/max (when feasible).")


if __name__ == "__main__":
    main()


