#!/usr/bin/env python3
"""Mark recent submissions that have disappeared from the main-page snapshot as completed."""

from __future__ import annotations

import argparse
import os
import sys
from typing import Any

_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _REPO_ROOT not in sys.path:
    sys.path.insert(0, _REPO_ROOT)

from db_io.database import DEFAULT_CREDENTIALS_FILE, Database
from statuses import COMPLETED, SUBMITTED


CANDIDATE_LIMIT = 100
# How many recent snapshots to scan for a candidate's last observed 'done' count.
# Snapshots are pruned to the last 100, so this covers the full retained history.
SNAPSHOT_LOOKBACK = 100
DEFAULT_DATABASE = "CLAS12OCR"
DEFAULT_OWNER = "gemc"


def build_parser() -> argparse.ArgumentParser:
    """Build the command-line parser."""
    parser = argparse.ArgumentParser(
        description=(
            "Mark the newest 100 'Submitted to OSG' rows as completed when they are absent from the "
            "latest main-page snapshot. The default is a dry run."
        )
    )
    parser.add_argument(
        "-c",
        "--credentials",
        default=str(DEFAULT_CREDENTIALS_FILE),
        help="MySQL credential file. Default: %(default)s",
    )
    parser.add_argument(
        "--database",
        default=DEFAULT_DATABASE,
        help="Database containing submissions and snapshots. Default: %(default)s",
    )
    parser.add_argument(
        "-o",
        "--owner",
        default=DEFAULT_OWNER,
        help="Owner used to select the main-page snapshot. Default: %(default)s",
    )
    parser.add_argument(
        "--write-to-db",
        action="store_true",
        help="Write the Completed status. Without this option, only print candidates.",
    )
    return parser


def _submission_id(value: Any) -> int | None:
    """Return a submission ID as an integer, or None for an unusable value."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def _done_count(value: Any) -> int | None:
    """Return a 'done' job count as an integer, or None for an unusable value."""
    if value is None:
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def build_last_done_map(snapshots: list[dict[str, Any]], database_name: str) -> dict[int, int | None]:
    """Map submission ID to its most recent observed 'done' count across snapshots.

    Snapshots are expected newest-first, so the first occurrence of each submission
    is its last observed 'done' value before it left the main-page snapshot.
    """
    last_done: dict[int, int | None] = {}
    for snapshot in snapshots:
        payload = snapshot.get("payload")
        if not isinstance(payload, dict):
            continue
        database_payload = payload.get(database_name)
        if not isinstance(database_payload, dict):
            continue
        results = database_payload.get("results")
        if not isinstance(results, list):
            continue
        for row in results:
            if not isinstance(row, dict):
                continue
            submission_id = _submission_id(row.get("user_submission_id", row.get("submission id")))
            if submission_id is None or submission_id in last_done:
                continue
            last_done[submission_id] = _done_count(row.get("done"))
    return last_done


def extract_visible_submission_ids(payload: dict[str, Any], database_name: str) -> set[int]:
    """Return submission IDs in one database block of a main-page payload."""
    database_payload = payload.get(database_name)
    if not isinstance(database_payload, dict):
        raise ValueError(f"Snapshot has no valid {database_name!r} database block")

    results = database_payload.get("results")
    if not isinstance(results, list):
        raise ValueError(f"Snapshot {database_name!r} block has no valid results list")

    visible_ids = set()
    for row in results:
        if not isinstance(row, dict):
            continue
        submission_id = _submission_id(row.get("user_submission_id", row.get("submission id")))
        if submission_id is not None:
            visible_ids.add(submission_id)
    return visible_ids


def get_recent_submitted_rows(db: Database) -> list[dict[str, Any]]:
    """Return the newest 100 rows that are still marked Submitted to OSG."""
    return db.query(
        """
        SELECT user_submission_id, user, pool_node, run_status
        FROM submissions
        WHERE run_status = %s
        ORDER BY user_submission_id DESC
        LIMIT %s
        """,
        [SUBMITTED, CANDIDATE_LIMIT],
    )


def find_completion_candidates(
    submitted_rows: list[dict[str, Any]],
    visible_submission_ids: set[int],
) -> list[dict[str, Any]]:
    """Return submitted rows whose IDs are absent from the main-page snapshot."""
    candidates = []
    for row in submitted_rows:
        submission_id = _submission_id(row.get("user_submission_id"))
        if submission_id is not None and submission_id not in visible_submission_ids:
            candidates.append(row)
    return candidates


def mark_completed(db: Database, candidates: list[dict[str, Any]]) -> int:
    """Mark candidates Completed, recording their last 'done' count and completion time.

    Each candidate carries its own last observed 'done' value (attached in run()), so
    rows are updated one at a time. Every update stays guarded by the current
    Submitted status so a concurrent status change is not clobbered.
    """
    updated = 0
    for row in candidates:
        submission_id = _submission_id(row.get("user_submission_id"))
        if submission_id is None:
            continue
        updated += db.execute(
            """
            UPDATE submissions
            SET run_status = %s,
                done = %s,
                completion_time = NOW()
            WHERE run_status = %s
              AND user_submission_id = %s
            """,
            [COMPLETED, _done_count(row.get("done")), SUBMITTED, submission_id],
        )
    return updated


def run(args: argparse.Namespace) -> int:
    """Find completion candidates and optionally update them."""
    with Database(
        credentials_file=args.credentials,
        database_name=args.database,
    ) as db:
        snapshots = db.get_owner_submission_snapshots(
            args.database, args.owner, limit=SNAPSHOT_LOOKBACK
        )
        if not snapshots:
            raise RuntimeError(
                f"No main-page snapshot found for database={args.database}, owner={args.owner}"
            )

        latest = snapshots[0]
        visible_ids = extract_visible_submission_ids(latest["payload"], args.database)
        last_done = build_last_done_map(snapshots, args.database)
        submitted_rows = get_recent_submitted_rows(db)
        candidates = find_completion_candidates(submitted_rows, visible_ids)
        for row in candidates:
            row["done"] = last_done.get(_submission_id(row.get("user_submission_id")))

        print(
            f"Snapshot {latest['snapshot_id']} from {latest['update_time']}: "
            f"{len(visible_ids)} visible submission(s)"
        )
        print(f"Checked {len(submitted_rows)} recent {SUBMITTED!r} row(s).")
        for row in candidates:
            print(
                "Candidate {0}: user={1}, pool_node={2}, done={3}".format(
                    row.get("user_submission_id"),
                    row.get("user"),
                    row.get("pool_node"),
                    row.get("done"),
                )
            )

        if not args.write_to_db:
            print(f"Dry run: {len(candidates)} candidate(s); no rows updated.")
            return 0

        updated = mark_completed(db, candidates)
        print(f"Marked {updated} submission(s) as {COMPLETED!r}.")
        return 0


def main(argv: list[str] | None = None) -> int:
    """Command-line entry point."""
    args = build_parser().parse_args(argv)
    try:
        return run(args)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
