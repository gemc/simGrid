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
    Score = 1 / history_load_for_user

    Uses the recency-weighted history load (see below) rather than a raw
    pending-job count, so users with a large job history are penalised even
    when they have few jobs currently pending.

aging
    Score = 2^(age_days / half_life_days) /
            (history_load_for_user ^ queue_penalty_exponent)

aging_interleaved
    Same score as aging, but priorities are assigned in rounds with per-user
    interleaving (burst_per_user) to avoid long consecutive runs of a single
    user.

History-weighted load
---------------------
For ALL algorithms the denominator combines two components:

    history_load_for_user = history_load_submitted + history_load_pending

history_load_submitted  (decay-weighted, non-pending jobs only)
    --history-half-life-days controls the exponential decay applied to jobs
    whose run_status is NOT 'Not Submitted'.  The weight of such a job whose
    client_time is `age_days` old is:

        weight(age_days) = 2 ^ (-age_days / history_half_life_days)

    A completed job right now has weight 1; one submitted T_h days ago has
    weight 0.5; and so on.  Jobs with missing/malformed timestamps are treated
    as brand-new (weight 1) as a conservative fallback.

history_load_pending  (raw count, no decay)
    Jobs whose run_status is 'Not Submitted' each contribute exactly 1,
    regardless of their age.  --history-half-life-days has no effect here.

Together:

    history_load_for_user =
        Σ  2^(-age_j / T_h)          (over non-pending jobs)
      + N_pending                     (raw count of pending jobs)

For all algorithms, ties are broken by:
1. ascending client_time
2. ascending user_submission_id

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

Use the interleaved aging algorithm with a separate history half-life:

    python priority_submissions.py -c db_credentials.cnf \
        --priority-algorithm aging_interleaved \
        --half-life-days 0.5 \
        --history-half-life-days 7 \
        --queue-penalty-exponent 0.25 \
        --burst-per-user 1

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
ESTIMATE_HOURS_PER_JOB = 10.0


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
		choices=["inverse_count", "aging", "aging_interleaved"],
		default="inverse_count",
		help=(
			"Priority scoring algorithm for 'Not Submitted' jobs "
			"(default: %(default)s)."
		),
	)

	parser.add_argument(
		"--queue-penalty-exponent",
		type=float,
		default=1.0,
		help=(
			"Exponent applied to the history-weighted per-user load in aging-based "
			"priority scoring. 1.0 means 1/N, 0.5 means 1/sqrt(N). "
			"Used by aging and aging_interleaved."
		),
	)

	parser.add_argument(
		"--burst-per-user",
		type=int,
		default=1,
		help=(
			"Maximum number of jobs taken from a user per round for "
			"aging_interleaved (default: %(default)s)."
		),
	)

	parser.add_argument(
		"--half-life-days",
		type=float,
		default=7.0,
		help=(
			"Half-life in days for the age boost in aging-based algorithms "
			"(default: %(default)s)."
		),
	)

	parser.add_argument(
		"--history-half-life-days",
		type=float,
		default=None,
		help=(
			"Half-life in days for weighting historical job counts in the "
			"denominator (smooth exponential decay). "
			"If omitted, defaults to --half-life-days."
		),
	)

	parser.add_argument(
		"--no-queue-penalty",
		action="store_true",
		default=False,
		help=(
			"Ignore pending jobs in the denominator. "
			"Forces history_load_pending to zero for all users, so the "
			"denominator depends only on the decay-weighted history of "
			"completed jobs."
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

	parser.add_argument(
		"--write-to-db",
		action="store_true",
		default=False,
		help=(
			"If set, write the computed priorities back to the `priority` column "
			"of the `submissions` table in the database."
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


def get_total_not_submitted_queue_hours(
		rows: list[dict],
		time_format: str,
) -> float:
	"""
	Return the total queue time in hours for rows whose run_status is
	'Not Submitted'.
	"""
	now = datetime.now()
	total_hours = 0.0

	for row in rows:
		status = str(row.get("run_status", "")).strip()
		if status != "Not Submitted":
			continue

		client_time = str(row.get("client_time", "")).strip()
		if not client_time:
			continue

		try:
			client_dt = datetime.strptime(client_time, time_format)
		except ValueError:
			continue

		diff_hours = (now - client_dt).total_seconds() / 3600.0
		if diff_hours > 0:
			total_hours += diff_hours

	return total_hours


def get_queue_hours(client_time: str, time_format: str) -> float:
	"""
	Return queue time in hours from client_time until now.

	If parsing fails or the computed value is negative, return 0.0.
	"""
	try:
		client_dt = datetime.strptime(str(client_time).strip(), time_format)
	except (ValueError, TypeError):
		return 0.0

	diff_hours = (datetime.now() - client_dt).total_seconds() / 3600.0
	return diff_hours if diff_hours > 0 else 0.0


def compute_history_loads(
		rows: list[dict],
		time_format: str,
		history_half_life_days: float,
		no_queue_penalty: bool = False,
) -> tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, int]]:
	"""
	Compute per-user history loads, split by run_status.

	The denominator used for priority scoring is:

	    history_load_for_user = history_load_submitted + history_load_pending

	history_load_submitted
	    Smooth exponential decay over jobs whose run_status is NOT
	    'Not Submitted':

	        weight(age_days) = 2 ^ (-age_days / history_half_life_days)

	    Jobs with missing/malformed timestamps are treated as brand-new
	    (weight 1.0) as a conservative fallback.

	history_load_pending
	    Raw count of jobs whose run_status IS 'Not Submitted'.  Each
	    contributes exactly 1 regardless of age.
	    --history-half-life-days has no effect on this component.

	    If no_queue_penalty is True, this component is forced to 0.0 for
	    all users, so the denominator depends only on completed-job history.

	Parameters
	----------
	rows:
		All rows returned from the database (any run_status).
	time_format:
		Python datetime format string for client_time.
	history_half_life_days:
		Half-life for the exponential decay applied to non-pending jobs
		(must be > 0).
	no_queue_penalty:
		If True, pending jobs contribute 0 to the denominator instead of 1.

	Returns
	-------
	tuple[dict[str, float], dict[str, float], dict[str, float], dict[str, int]]
		(history_load_by_user, submitted_load_by_user,
		 pending_load_by_user, jobs_for_user_counts)
	"""
	if history_half_life_days <= 0:
		raise ValueError("history_half_life_days must be > 0")

	now = datetime.now()
	submitted_load_by_user: dict[str, float] = {}
	pending_load_by_user: dict[str, float] = {}
	jobs_for_user_counts: dict[str, int] = Counter()

	for row in rows:
		user = str(row.get("user", ""))
		jobs_for_user_counts[user] += 1

		if user not in submitted_load_by_user:
			submitted_load_by_user[user] = 0.0
		if user not in pending_load_by_user:
			pending_load_by_user[user] = 0.0

		status = str(row.get("run_status", "")).strip()

		if status == "Not Submitted":
			# Pending jobs count as exactly 1 each, no decay —
			# unless --no-queue-penalty is set, in which case they contribute 0.
			if not no_queue_penalty:
				pending_load_by_user[user] += 1.0
			continue

		# Non-pending jobs: smooth exponential decay by age.
		client_time = str(row.get("client_time", "")).strip()
		if not client_time:
			# Conservative fallback: treat as brand-new (weight 1).
			submitted_load_by_user[user] += 1.0
			continue

		try:
			client_dt = parse_client_time(client_time, time_format)
		except ValueError:
			# Conservative fallback: treat as brand-new (weight 1).
			submitted_load_by_user[user] += 1.0
			continue

		age_days = (now - client_dt).total_seconds() / 86400.0
		if age_days < 0:
			age_days = 0.0

		weight = math.pow(2.0, -age_days / history_half_life_days)
		submitted_load_by_user[user] += weight

	history_load_by_user = {
		user: submitted_load_by_user.get(user, 0.0) + pending_load_by_user.get(user, 0.0)
		for user in jobs_for_user_counts
	}

	return history_load_by_user, submitted_load_by_user, pending_load_by_user, jobs_for_user_counts


def compute_priorities(
		rows: list[dict],
		algorithm: str,
		time_format: str,
		half_life_days: float,
		queue_penalty_exponent: float,
		history_half_life_days: float,
		burst_per_user: int = 1,
		no_queue_penalty: bool = False,
) -> tuple[list[dict], list[dict], dict[str, float], dict[str, float]]:
	"""
	Compute priorities for rows with run_status == 'Not Submitted'.

	Important:
	- pending_jobs_for_user counts only pending jobs.
	- jobs_for_user counts ALL jobs in the selected dataset.
	- history_load_for_user = submitted_load_for_user + pending_load_for_user
	  and is used in the denominator for all algorithms.
	  submitted_load_for_user is decay-weighted (non-pending jobs only).
	  pending_load_for_user is a raw count (pending jobs, no decay).

	Algorithms
	----------
	inverse_count
		Score each pending row as:
		    1 / (history_load_for_user ^ queue_penalty_exponent)

		Uses the full history load rather than a raw pending-job count, so a
		heavy historical user is penalised even if they currently have few
		pending jobs.  queue_penalty_exponent lets you soften the penalty
		(e.g. 0.5 = square-root damping).

	aging
		Score each pending row as:
		    2^(age_days / half_life_days) /
		    (history_load_for_user ^ queue_penalty_exponent)
		and sort globally

	aging_interleaved
		Compute a user-level score from the next pending job for each user, then
		assign priorities in rounds, taking at most burst_per_user jobs per user
		per round. This avoids large contiguous blocks from the same user.
	"""
	if half_life_days <= 0:
		raise ValueError("half_life_days must be > 0")

	if burst_per_user <= 0:
		raise ValueError("burst_per_user must be > 0")

	pending_rows = [
		row for row in rows
		if str(row.get("run_status", "")).strip() == "Not Submitted"
	]

	pending_counts = Counter(str(row.get("user", "")) for row in pending_rows)
	history_load_by_user, submitted_load_by_user, pending_load_by_user, jobs_for_user_counts = compute_history_loads(
		rows=rows,
		time_format=time_format,
		history_half_life_days=history_half_life_days,
		no_queue_penalty=no_queue_penalty,
	)

	now = datetime.now()

	def row_age_days(row: dict) -> float:
		client_dt = parse_client_time(str(row.get("client_time", "")), time_format)
		return (now - client_dt).total_seconds() / 86400.0

	def row_queue_hours(row: dict) -> float:
		return get_queue_hours(str(row.get("client_time", "")), time_format)

	def aging_score(age_days: float, history_load_for_user: float) -> float:
		effective_load = max(history_load_for_user, 1e-12)
		return math.pow(2.0, age_days / half_life_days) / math.pow(
			effective_load, queue_penalty_exponent
		)

	def inverse_count_score(history_load_for_user: float) -> float:
		effective_load = max(history_load_for_user, 1e-12)
		return 1.0 / math.pow(effective_load, queue_penalty_exponent)

	scored_pending: list[dict] = []

	if algorithm in {"inverse_count", "aging"}:
		for row in pending_rows:
			user = str(row.get("user", ""))

			pending_jobs = pending_counts[user]
			jobs_for_user = jobs_for_user_counts[user]
			history_load_for_user = history_load_by_user.get(user, 0.0)

			client_dt = parse_client_time(str(row.get("client_time", "")), time_format)
			estimate_time_hours = ESTIMATE_HOURS_PER_JOB

			if algorithm == "inverse_count":
				score = inverse_count_score(history_load_for_user)
				age_days = None
			else:
				age_days = row_age_days(row)
				score = aging_score(age_days, history_load_for_user)

			enriched = dict(row)
			enriched["pending_jobs_for_user"] = pending_jobs
			enriched["jobs_for_user"] = jobs_for_user
			enriched["submitted_load_for_user"] = submitted_load_by_user.get(user, 0.0)
			enriched["pending_load_for_user"] = pending_load_by_user.get(user, 0.0)
			enriched["history_load_for_user"] = history_load_for_user
			enriched["score"] = score
			enriched["age_days"] = age_days
			enriched["estimate_time_hours"] = estimate_time_hours
			enriched["_client_dt"] = client_dt
			scored_pending.append(enriched)

		scored_pending.sort(
			key=lambda row: (
				-row["score"],
				row["_client_dt"],
				row["user_submission_id"],
			)
		)

	elif algorithm == "aging_interleaved":
		per_user: dict[str, list[dict]] = {}
		for row in pending_rows:
			user = str(row.get("user", ""))
			enriched = dict(row)
			enriched["_client_dt"] = parse_client_time(
				str(row.get("client_time", "")),
				time_format,
			)
			estimate_time_hours = ESTIMATE_HOURS_PER_JOB
			enriched["estimate_time_hours"] = ESTIMATE_HOURS_PER_JOB
			enriched["age_days"] = row_age_days(row)
			enriched["pending_jobs_for_user"] = pending_counts[user]
			enriched["jobs_for_user"] = jobs_for_user_counts[user]
			enriched["submitted_load_for_user"] = submitted_load_by_user.get(user, 0.0)
			enriched["pending_load_for_user"] = pending_load_by_user.get(user, 0.0)
			enriched["history_load_for_user"] = history_load_by_user.get(user, 0.0)
			per_user.setdefault(user, []).append(enriched)

		for user in per_user:
			per_user[user].sort(
				key=lambda row: (row["_client_dt"], row["user_submission_id"])
			)

		ordered_pending: list[dict] = []

		while per_user:
			active_users = []
			for user, user_rows in per_user.items():
				head = user_rows[0]
				score = aging_score(
					head["age_days"],
					head["history_load_for_user"],
				)
				active_users.append((
					user,
					score,
					head["_client_dt"],
					head["user_submission_id"],
				))

			active_users.sort(key=lambda item: (-item[1], item[2], item[3]))

			users_to_delete = []
			for user, _, _, _ in active_users:
				user_rows = per_user[user]
				take_n = min(burst_per_user, len(user_rows))

				for _ in range(take_n):
					job = user_rows.pop(0)
					job["score"] = aging_score(
						job["age_days"],
						job["history_load_for_user"],
					)
					ordered_pending.append(job)

				if not user_rows:
					users_to_delete.append(user)

			for user in users_to_delete:
				del per_user[user]

		scored_pending = ordered_pending

	else:
		raise ValueError(f"Unsupported priority algorithm: {algorithm}")

	for index, row in enumerate(scored_pending, start=1):
		row["priority"] = index

	output_rows: list[dict] = []
	pending_by_submission_id = {
		row["user_submission_id"]: row for row in scored_pending
	}

	for row in rows:
		new_row = dict(row)
		pending_info = pending_by_submission_id.get(row["user_submission_id"])

		if pending_info is not None:
			new_row["priority"] = pending_info["priority"]
			new_row["estimate_time_hours"] = pending_info["estimate_time_hours"]
		else:
			new_row["priority"] = None
			new_row["estimate_time_hours"] = None

		output_rows.append(new_row)

	for row in scored_pending:
		del row["_client_dt"]

	return output_rows, scored_pending, submitted_load_by_user, pending_load_by_user


def print_table(rows: list[dict]) -> None:
	"""
	Print rows as a simple aligned text table.
	"""
	headers = ["user", "user_submission_id", "client_time", "order", "wait_time"]

	if not rows:
		print("No rows found.")
		return

	def format_cell(row: dict, header: str) -> str:
		if header == "order":
			value = row.get("priority")
			return "" if value is None else str(value)
		elif header == "wait_time":
			if str(row.get("run_status", "")).strip() != "Not Submitted":
				return ""
			client_time = str(row.get("client_time", "")).strip()
			if not client_time:
				return ""
			try:
				client_dt = datetime.strptime(client_time, "%Y-%m-%d %H:%M:%S")
				hours = (datetime.now() - client_dt).total_seconds() / 3600.0
				return f"{hours:.1f}h" if hours >= 0 else ""
			except ValueError:
				return ""
		else:
			value = row.get(header)
			return "" if value is None else str(value)

	widths = {}
	for header in headers:
		widths[header] = max(
			len(header),
			max(len(format_cell(row, header)) for row in rows),
		)

	header_line = "  ".join(header.ljust(widths[header]) for header in headers)
	separator_line = "  ".join("-" * widths[header] for header in headers)

	print(header_line)
	print(separator_line)

	for row in rows:
		cells = [format_cell(row, header).ljust(widths[header]) for header in headers]
		print("  ".join(cells))


def print_summary(
		rows: list[dict],
		submitted_load_by_user: dict[str, float],
		pending_load_by_user: dict[str, float],
		days_considered: int | None = None,
		time_format: str = "%Y-%m-%d %H:%M:%S",
		no_queue_penalty: bool = False,
) -> None:
	"""
	Print a summary table with the number of jobs per user, estimated time
	for 'Not Submitted' jobs, and the two denominator components used for
	priority scoring.

	Columns
	-------
	user          : user identifier
	total_submissions    : total job count (all statuses)
	estimate_days : estimated queue time in days for pending jobs
	weight        : decay-weighted count of non-pending jobs
	                (controlled by --history-half-life-days)
	pending_jobs  : integer count of 'Not Submitted' jobs (no decay)

	One row in the `submissions` table is counted as one job.
	Each pending job contributes 10 estimated hours.
	"""
	if not rows:
		print()
		print("Summary: jobs per user")
		print("No rows found.")
		print()
		if days_considered is None:
			print("Days considered: all")
		else:
			print(f"Days considered: last {days_considered}")
		print("Total jobs: 0")
		print("Total users: 0")
		print("Total 'Not Submitted' jobs: 0")
		print("Total estimated time for 'Not Submitted' jobs (days): 0.0")
		return

	job_counts = Counter(str(row.get("user", "")) for row in rows)

	estimate_time_by_user: dict[str, float] = {}
	for row in rows:
		user = str(row.get("user", ""))
		status = str(row.get("run_status", "")).strip()

		if user not in estimate_time_by_user:
			estimate_time_by_user[user] = 0.0

		if status == "Not Submitted":
			estimate_time_by_user[user] += ESTIMATE_HOURS_PER_JOB / 24.0

	summary_rows = [
		{
			"user":         user,
			"total_submissions":   count,
			"estimate_days": estimate_time_by_user.get(user, 0.0),
			"weight":       submitted_load_by_user.get(user, 0.0),
			"pending_jobs": int(round(pending_load_by_user.get(user, 0.0))),
		}
		for user, count in sorted(job_counts.items(), key=lambda item: (-item[1], item[0]))
	]

	headers = ["user", "total_submissions", "estimate_days", "weight", "pending_jobs"]

	widths = {}
	for header in headers:
		if header in {"estimate_days", "weight"}:
			widths[header] = max(
				len(header),
				max(len(f"{row.get(header, 0.0):.2f}") for row in summary_rows),
			)
		else:
			widths[header] = max(
				len(header),
				max(len(str(row.get(header, ""))) for row in summary_rows),
			)

	print()
	print("Summary: jobs per user")
	if no_queue_penalty:
		print("  (--no-queue-penalty: pending-job count excluded from denominator)")
	print("  ".join(header.ljust(widths[header]) for header in headers))
	print("  ".join("-" * widths[header] for header in headers))

	for row in summary_rows:
		print(
			"  ".join([
				str(row["user"]).ljust(widths["user"]),
				str(row["total_submissions"]).ljust(widths["total_submissions"]),
				f"{row['estimate_days']:.2f}".ljust(widths["estimate_days"]),
				f"{row['weight']:.2f}".ljust(widths["weight"]),
				str(row["pending_jobs"]).ljust(widths["pending_jobs"]),
			])
		)

	total_pending = sum(
		1 for row in rows if str(row.get("run_status", "")).strip() == "Not Submitted"
	)
	total_submissions = row["total_submissions"]

	total_estimate_time = sum(estimate_time_by_user.values())

	print()
	if days_considered is None:
		print("Days considered: all")
	else:
		print(f"Days considered: last {days_considered}")
	print(f"Total submissions: {total_submissions}")
	print(f"Total users: {len(summary_rows)}")
	print(f"Total 'Not Submitted' jobs: {total_pending}")
	print(f"Total estimated time for 'Not Submitted' jobs (days): {total_estimate_time:.1f}")


def write_priority_json(
		json_path: str | Path,
		prioritized_pending_rows: list[dict],
		all_rows: list[dict],
		algorithm: str,
		half_life_days: float,
		history_half_life_days: float,
		days_considered: int | None,
		submitted_load_by_user: dict[str, float],
		pending_load_by_user: dict[str, float],
		no_queue_penalty: bool = False,
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
		Half-life used for the age boost.
	history_half_life_days:
		Half-life used for the smooth exponential history weighting.
	submitted_load_by_user:
		Decay-weighted count of non-pending jobs per user.
	pending_load_by_user:
		Raw count of pending jobs per user.
	"""
	now = datetime.now()
	user_counts = Counter(str(row.get("user", "")) for row in all_rows)

	pending_hours_by_user: dict[str, float] = {}
	for row in all_rows:
		user = str(row.get("user", ""))
		if str(row.get("run_status", "")).strip() == "Not Submitted":
			pending_hours_by_user[user] = pending_hours_by_user.get(user, 0.0) + ESTIMATE_HOURS_PER_JOB

	summary_jobs_per_user = [
		{
			"user":           user,
			"jobs":           count,
			"submitted_load": round(submitted_load_by_user.get(user, 0.0), 4),
			"pending_jobs":   int(round(pending_load_by_user.get(user, 0.0))),
			"estimate_days":  round(pending_hours_by_user.get(user, 0.0) / 24.0, 4),
		}
		for user, count in sorted(user_counts.items(), key=lambda item: (-item[1], item[0]))
	]

	payload = {
		"priority_algorithm":       algorithm,
		"half_life_days":           half_life_days if algorithm in {"aging",
		                                                            "aging_interleaved"} else None,
		"history_half_life_days":   history_half_life_days,
		"no_queue_penalty":         no_queue_penalty,
		"days_considered":          days_considered,
		"total_submissions":               len(all_rows),
		"total_users":              len(summary_jobs_per_user),
		"total_not_submitted_jobs": len(prioritized_pending_rows),
		"jobs_per_user":            summary_jobs_per_user,
		"priorities":               [
			{
				"user_submission_id":     row["user_submission_id"],
				"user":                   row["user"],
				"client_time":            row["client_time"],
				"run_status":             row["run_status"],
				"priority":               row["priority"],
				"estimate_time_hours":    row["estimate_time_hours"],
				"pending_jobs_for_user":  row.get("pending_jobs_for_user"),
				"jobs_for_user":          row.get("jobs_for_user"),
				"submitted_load_for_user": row.get("submitted_load_for_user"),
				"pending_load_for_user":  row.get("pending_load_for_user"),
				"history_load_for_user":  row.get("history_load_for_user"),
				"score": round(row["score"], 1),
				"age_days":               row["age_days"],
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

	history_half_life_days = (
		args.history_half_life_days
		if args.history_half_life_days is not None
		else args.half_life_days
	)

	try:
		with Database(args.credentials) as db:
			rows = db.get_submissions_with_status(
				days_past=args.days,
				client_time_format="%Y-%m-%d %H:%i:%s",
			)
			print(f"DEBUG fetched rows: {len(rows)}")

			if args.days is not None:
				total_all = db.query_one("SELECT COUNT(*) AS n FROM submissions")
				print(f"DEBUG total rows in submissions: {total_all['n']}")

				bad_time = db.query_one(
					"""
					SELECT COUNT(*) AS n
					FROM submissions
					WHERE client_time IS NULL
					   OR TRIM(client_time) = ''
					   OR STR_TO_DATE(client_time, %s) IS NULL
					""",
					["%Y-%m-%d %H:%i:%s"],
				)
				print(f"DEBUG unparsable/blank client_time rows: {bad_time['n']}")

		rows_with_priority, prioritized_pending_rows, submitted_load_by_user, pending_load_by_user = compute_priorities(
			rows=rows,
			algorithm=args.priority_algorithm,
			time_format=args.time_format,
			half_life_days=args.half_life_days,
			queue_penalty_exponent=args.queue_penalty_exponent,
			history_half_life_days=history_half_life_days,
			burst_per_user=args.burst_per_user,
			no_queue_penalty=args.no_queue_penalty,
		)

		print_table(rows_with_priority)
		print_summary(
			rows_with_priority,
			submitted_load_by_user=submitted_load_by_user,
			pending_load_by_user=pending_load_by_user,
			days_considered=args.days,
			time_format=args.time_format,
			no_queue_penalty=args.no_queue_penalty,
		)

		write_priority_json(
			json_path=args.json_out,
			prioritized_pending_rows=prioritized_pending_rows,
			all_rows=rows_with_priority,
			algorithm=args.priority_algorithm,
			half_life_days=args.half_life_days,
			history_half_life_days=history_half_life_days,
			days_considered=args.days,
			submitted_load_by_user=submitted_load_by_user,
			pending_load_by_user=pending_load_by_user,
			no_queue_penalty=args.no_queue_penalty,
		)

		print()
		print(f"Wrote priority JSON: {args.json_out}")

		if args.write_to_db:
			with Database(args.credentials) as db:
				db.execute(
					"UPDATE submissions SET priority = '0' WHERE run_status != %s",
					["Not Submitted"],
				)
				updated = db.update_priorities(prioritized_pending_rows)
			print(f"Updated {updated} row(s) in the database.")

		return 0

	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())