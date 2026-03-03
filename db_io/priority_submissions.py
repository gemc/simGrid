#!/usr/bin/env python3
"""
List submission timing information from the `submissions` table, compute
priority for pending jobs, and write those priorities to a JSON file.

This script uses the `Database` class from `database.py` and fetches:

    SELECT user, user_submission_id, client_time, run_status
    FROM submissions

Priorities are assigned only to rows where:

    run_status = 'Not Submitted'

The assigned priority is a sequential integer from 1 to N, where:
- N is the total number of "Not Submitted" jobs considered
- 1 is the highest priority

Supported priority algorithms
-----------------------------
inverse_count
    Score = 1 / number_of_pending_jobs_for_that_user

aging
    Score = 2^(age_days / half_life_days) / number_of_pending_jobs_for_that_user

For both algorithms, rows are ordered by:
1. descending score
2. ascending client_time
3. ascending user_submission_id

The script prints:
- a table of all selected jobs with an added priority column
- a summary table of jobs per user

It also writes a JSON file containing the computed priorities so another
script can later update the MySQL table.

Examples
--------
List all submissions and compute priorities:

    python priority_submissions.py -c db_credentials.cnf

Limit to the last 7 days:

    python priority_submissions.py -c db_credentials.cnf -d 7

Use the aging algorithm with a 1-week half-life:

    python priority_submissions.py -c db_credentials.cnf \
        --priority-algorithm aging \
        --half-life-days 7

Write JSON to a specific file:

    python priority_submissions.py -c db_credentials.cnf \
        --json-out priorities.json
"""

from __future__ import annotations

import argparse
import json
import math
import sys
from collections import Counter
from datetime import datetime
from pathlib import Path

from database import Database


def build_parser() -> argparse.ArgumentParser:
	"""
	Build the command-line parser for this script.
	"""
	parser = argparse.ArgumentParser(
		description=(
			"List user submissions, compute priorities for 'Not Submitted' jobs, "
			"and write the priority mapping to JSON."
		)
	)

	parser.add_argument(
		"-c",
		"--credentials",
		required=True,
		help="Path to the MySQL credential file.",
	)

	parser.add_argument(
		"-d",
		"--days",
		type=int,
		default=None,
		help="Limit client_time to the last N days.",
	)

	parser.add_argument(
		"--time-format",
		default="%Y-%m-%d %H:%M:%S",
		help=(
			"Python datetime format used to parse client_time after retrieval "
			"(default: %(default)s)."
		),
	)

	parser.add_argument(
		"--priority-algorithm",
		choices=["inverse_count", "aging"],
		default="inverse_count",
		help=(
			"Priority scoring algorithm for 'Not Submitted' jobs "
			"(default: %(default)s)."
		),
	)

	parser.add_argument(
		"--half-life-days",
		type=float,
		default=7.0,
		help=(
			"Half-life in days for the aging algorithm "
			"(default: %(default)s)."
		),
	)

	parser.add_argument(
		"--json-out",
		default="submission_priorities.json",
		help=(
			"Path to the JSON file to write computed priorities for later use "
			"(default: %(default)s)."
		),
	)

	return parser


def parse_client_time(value: str, time_format: str) -> datetime:
	"""
	Parse client_time string into a datetime.

	Parameters
	----------
	value:
		Raw client_time string from the database.
	time_format:
		Python datetime format string.

	Returns
	-------
	datetime
		Parsed datetime value.
	"""
	return datetime.strptime(value, time_format)


def compute_priorities(
		rows: list[dict],
		algorithm: str,
		time_format: str,
		half_life_days: float,
) -> tuple[list[dict], list[dict]]:
	"""
	Compute priorities for rows with run_status == 'Not Submitted'.

	Parameters
	----------
	rows:
		All rows retrieved from the database.
	algorithm:
		One of: inverse_count, aging
	time_format:
		Python datetime format string used to parse client_time.
	half_life_days:
		Half-life in days used only for the aging algorithm.

	Returns
	-------
	tuple[list[dict], list[dict]]
		First element:
			all rows with a new 'priority' key
		Second element:
			list of pending rows with computed metadata, ordered by priority
	"""
	pending_rows = [
		row for row in rows
		if str(row.get("run_status", "")).strip() == "Not Submitted"
	]

	pending_counts = Counter(str(row.get("user", "")) for row in pending_rows)
	now = datetime.now()

	scored_pending: list[dict] = []

	for row in pending_rows:
		user = str(row.get("user", ""))
		user_submission_id = row.get("user_submission_id")
		client_time = str(row.get("client_time", ""))
		pending_jobs = pending_counts[user]
		client_dt = parse_client_time(client_time, time_format)

		if algorithm == "inverse_count":
			score = 1.0 / pending_jobs
			age_days = None
		elif algorithm == "aging":
			age_days = (now - client_dt).total_seconds() / 86400.0
			score = math.pow(2.0, age_days / half_life_days) / pending_jobs
		else:
			raise ValueError(f"Unsupported priority algorithm: {algorithm}")

		enriched = dict(row)
		enriched["pending_jobs_for_user"] = pending_jobs
		enriched["score"] = score
		enriched["age_days"] = age_days
		enriched["_client_dt"] = client_dt
		scored_pending.append(enriched)

	scored_pending.sort(
		key=lambda row: (
			-row["score"],
			row["_client_dt"],
			row["user_submission_id"],
		)
	)

	for index, row in enumerate(scored_pending, start=1):
		row["priority"] = index

	priority_by_submission_id = {
		row["user_submission_id"]: row["priority"] for row in scored_pending
	}

	output_rows: list[dict] = []
	for row in rows:
		new_row = dict(row)
		new_row["priority"] = priority_by_submission_id.get(row["user_submission_id"])
		output_rows.append(new_row)

	for row in scored_pending:
		del row["_client_dt"]

	return output_rows, scored_pending


def print_table(rows: list[dict]) -> None:
	"""
	Print rows as a simple aligned text table.
	"""
	headers = ["user", "user_submission_id", "client_time", "priority"]

	if not rows:
		print("No rows found.")
		return

	widths = {}
	for header in headers:
		widths[header] = max(
			len(header),
			max(len("" if row.get(header) is None else str(row.get(header))) for row in rows),
		)

	header_line = "  ".join(header.ljust(widths[header]) for header in headers)
	separator_line = "  ".join("-" * widths[header] for header in headers)

	print(header_line)
	print(separator_line)

	for row in rows:
		print(
			"  ".join(
				("" if row.get(header) is None else str(row.get(header))).ljust(widths[header])
				for header in headers
			)
		)


def print_summary(rows: list[dict], days_considered: int | None = None) -> None:
	"""
	Print a summary table with the number of jobs per user.

	One row in the `submissions` table is counted as one job.
	"""
	if not rows:
		return

	counts = Counter(str(row.get("user", "")) for row in rows)

	summary_rows = [
		{"user": user, "jobs": count}
		for user, count in sorted(counts.items(), key=lambda item: (-item[1], item[0]))
	]

	headers = ["user", "jobs"]

	widths = {}
	for header in headers:
		widths[header] = max(
			len(header),
			max(len(str(row.get(header, ""))) for row in summary_rows),
		)

	print()
	print("Summary: jobs per user")
	print("  ".join(header.ljust(widths[header]) for header in headers))
	print("  ".join("-" * widths[header] for header in headers))

	for row in summary_rows:
		print(
			"  ".join(
				str(row.get(header, "")).ljust(widths[header])
				for header in headers
			)
		)

	total_pending = sum(
		1 for row in rows if str(row.get("run_status", "")).strip() == "Not Submitted"
	)

	print()
	if days_considered is None:
		print("Days considered: all")
	else:
		print(f"Days considered: last {days_considered}")

	print(f"Total jobs: {len(rows)}")
	print(f"Total users: {len(summary_rows)}")
	print(f"Total 'Not Submitted' jobs: {total_pending}")


def write_priority_json(
		json_path: str | Path,
		prioritized_pending_rows: list[dict],
		algorithm: str,
		half_life_days: float,
) -> None:
	"""
	Write the computed pending-job priorities to a JSON file for later use.

	Parameters
	----------
	json_path:
		Output JSON path.
	prioritized_pending_rows:
		Pending rows already ordered and annotated with priority.
	algorithm:
		Algorithm used to compute priority.
	half_life_days:
		Half-life used for the aging algorithm.
	"""
	payload = {
		"priority_algorithm":       algorithm,
		"half_life_days":           half_life_days if algorithm == "aging" else None,
		"total_not_submitted_jobs": len(prioritized_pending_rows),
		"priorities":               [
			{
				"user_submission_id":    row["user_submission_id"],
				"user":                  row["user"],
				"client_time":           row["client_time"],
				"run_status":            row["run_status"],
				"priority":              row["priority"],
				"pending_jobs_for_user": row["pending_jobs_for_user"],
				"score":                 row["score"],
				"age_days":              row["age_days"],
			}
			for row in prioritized_pending_rows
		],
	}

	path = Path(json_path)
	path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")


def main() -> int:
	"""
	Script entry point.

	Returns
	-------
	int
		Process exit code.
	"""
	args = build_parser().parse_args()

	try:
		with Database(args.credentials) as db:
			rows = db.get_submissions_with_status(
				days_past=args.days,
				client_time_format="%Y-%m-%d %H:%i:%s",
			)

		rows_with_priority, prioritized_pending_rows = compute_priorities(
			rows=rows,
			algorithm=args.priority_algorithm,
			time_format=args.time_format,
			half_life_days=args.half_life_days,
		)

		print_table(rows_with_priority)
		print_summary(rows_with_priority, args.days)

		write_priority_json(
			json_path=args.json_out,
			prioritized_pending_rows=prioritized_pending_rows,
			algorithm=args.priority_algorithm,
			half_life_days=args.half_life_days,
		)

		print()
		print(f"Wrote priority JSON: {args.json_out}")

		return 0

	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
