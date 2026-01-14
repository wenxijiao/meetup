import argparse
from datetime import datetime

import pytz

from data.firebase_db import (
    clear_test_participants,
    create_test_participants,
    start_next_round,
    start_round_timer,
)


tz = pytz.timezone("Pacific/Auckland")


def main():
    ap = argparse.ArgumentParser(description="Seed Firebase with test participants.")
    ap.add_argument("--en", type=int, default=10, help="English participants")
    ap.add_argument("--jp", type=int, default=10, help="Japanese participants")
    ap.add_argument("--max", dest="max_per_table", type=int, default=4)
    ap.add_argument("--min", dest="min_per_table", type=int, default=2)
    ap.add_argument("--duration", dest="round_duration_min", type=int, default=30)
    ap.add_argument("--tag", type=str, default=None, help="Optional tag for cleanup")
    ap.add_argument("--start-round", action="store_true", help="Start a round after seeding")
    ap.add_argument("--start-timer", action="store_true", help="Start timer for current round")
    ap.add_argument("--clear", action="store_true", help="Clear test participants first")
    ap.add_argument("--confirm", action="store_true", help="Actually perform writes/deletes")
    args = ap.parse_args()

    today = str(datetime.now(tz=tz).date())
    if not args.confirm:
        print("Dry run. Add --confirm to perform writes/deletes.")
        print(f"Would target date: {today}")
        print(f"Would seed: EN={args.en}, JP={args.jp}, tag={args.tag}")
        if args.clear:
            print("Would clear test participants first.")
        if args.start_round:
            print(
                f"Would start round with max={args.max_per_table}, min={args.min_per_table}."
            )
        if args.start_timer:
            print(f"Would start timer with duration={args.round_duration_min}.")
        return

    if args.clear:
        deleted = clear_test_participants(tag=args.tag)
        print(f"Cleared {deleted} test participants (tag={args.tag}).")

    created = create_test_participants(args.en, args.jp, tag=args.tag)
    print(f"Created {len(created)} test participants for {today} (tag={args.tag}).")

    if args.start_round:
        tables = start_next_round(args.max_per_table, args.min_per_table)
        print(f"Started round. Tables: {tables}")
    if args.start_timer:
        ok = start_round_timer(args.round_duration_min)
        print(f"Started timer: {ok}")


if __name__ == "__main__":
    main()

