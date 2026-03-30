#!/usr/bin/env python3
"""
list_owner_submissions.py

Build a combined view of:
1. HTCondor batches for one owner (via get_owner_batches)
2. Matching MySQL submission rows where submissions.pool_node == ClusterId
3. Extra MySQL rows with run_status = 'Not Submitted'

Options:
  -h            show help
  -q            print results to screen as JSON
  -j FILE       write results to JSON file
  -o OWNER      Condor owner to query
  -c FILE       MySQL credential file
  -d DATABASE   Override database name from credential file

Behavior:
  - no options => print help and exit
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from htcondor_utils import get_owner_batches, format_submitted_time
from database import Database, DEFAULT_CREDENTIALS_FILE


def build_parser() -> argparse.ArgumentParser:
	parser = argparse.ArgumentParser(
		description="List HTCondor owner batches joined with MySQL submissions."
	)
	parser.add_argument(
		"-o",
		"--owner",
		default="gemc",
		help="HTCondor owner to query. Default: %(default)s",
	)
	parser.add_argument(
		"-q",
		"--print-screen",
		action="store_true",
		help="Print JSON results to stdout.",
	)
	parser.add_argument(
		"-j",
		"--json-file",
		help="Write JSON results to this file.",
	)
	parser.add_argument(
		"-c",
		"--credentials",
		default=str(DEFAULT_RECENT_CREDENTIALS_FILE()),
		help=f"MySQL credential file. Default: {DEFAULT_RECENT_CREDENTIALS_FILE()}",
	)
	parser.add_argument(
		"-d",
		"--database",
		help="Override database name from credential file.",
	)
	return parser


def DEFAULT_RECENT_CREDENTIALS_FILE() -> Path:
	return Path(DEFAULT_CREDENTIALS_FILE).expanduser()


def safe_int(value: Any) -> int | None:
	if value is None:
		return None
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def build_condor_entry(cluster_id: int, batch: dict[str, Any]) -> dict[str, Any]:
	total = safe_int(batch.get("total_submit_procs")) or 0
	counts = batch.get("counts", {})

	run = safe_int(counts.get("RUN")) or 0
	idle = safe_int(counts.get("IDLE")) or 0
	hold = safe_int(counts.get("HOLD")) or 0
	other = safe_int(counts.get("OTHER")) or 0

	# DONE is what has left the queue out of the original submitted total.
	done = max(total - run - idle - hold - other, 0)

	return {
		"user": batch.get("owner"),
		"job id": cluster_id,
		"submitted": format_submitted_time(batch.get("submitted_epoch")),
		"total": total,
		"done": done,
		"run": run,
		"idle": idle,
		"hold": hold,
		"osg id": None,
		"pool_node": str(cluster_id),
		"mysql_status": None,
		"mysql_client_time": None,
		"user_submission_id": None,
		"priority": batch.get("current_priority"),
	}


def main() -> int:
	parser = build_parser()

	# no options => -h behavior
	if len(sys.argv) == 1:
		parser.print_help()
		return 0

	args = parser.parse_args()

	if not args.print_screen and not args.json_file:
		print("Error: use -q and/or -j FILE", file=sys.stderr)
		return 1

	try:
		# 1. submissions = get_owner_batches(owner)
		batches = get_owner_batches(args.owner)

		results: list[dict[str, Any]] = []
		seen_submission_ids: set[int] = set()
		seen_pool_nodes: set[str] = set()

		with Database(
			credentials_file=args.credentials,
			database_name=args.database,
		) as db:
			# 2. for each condor batch, find mysql row where pool_node matches job id
			for cluster_id in sorted(batches):
				batch = batches[cluster_id]
				entry = build_condor_entry(cluster_id, batch)

				mysql_row = db.query_one(
					"""
					SELECT user,
					       user_submission_id,
					       client_time,
					       pool_node,
					       run_status,
					       priority
					FROM submissions
					WHERE pool_node = %s
					ORDER BY user_submission_id DESC
					LIMIT 1
					""",
					[str(cluster_id)],
				)

				if mysql_row is not None:
					entry["osg id"] = (
						str(mysql_row["user_submission_id"])
						if mysql_row.get("user_submission_id") is not None
						else None
					)
					entry["user_submission_id"] = mysql_row.get("user_submission_id")
					entry["mysql_status"] = mysql_row.get("run_status")
					entry["mysql_client_time"] = mysql_row.get("client_time")
					entry["priority"] = mysql_row.get("priority", entry["priority"])

					if mysql_row.get("user") is not None:
						entry["user"] = mysql_row["user"]

					if mysql_row.get("user_submission_id") is not None:
						seen_submission_ids.add(int(mysql_row["user_submission_id"]))

					if mysql_row.get("pool_node") is not None:
						seen_pool_nodes.add(str(mysql_row["pool_node"]))

				results.append(entry)

			# 4. add all mysql jobs with submitted = "Not Submitted"
			not_submitted_rows = db.query(
				"""
				SELECT user,
				       user_submission_id,
				       client_time,
				       pool_node,
				       run_status,
				       priority
				FROM submissions
				WHERE run_status = %s
				ORDER BY user_submission_id
				""",
				["Not Submitted"],
			)

			for row in not_submitted_rows:
				submission_id = safe_int(row.get("user_submission_id"))
				pool_node = str(row.get("pool_node") or "")

				# Avoid duplicates if already matched above
				if submission_id is not None and submission_id in seen_submission_ids:
					continue

				entry = {
					"user": row.get("user"),
					"job id": safe_int(pool_node),
					"submitted": row.get("client_time"),
					"total": None,
					"done": None,
					"run": None,
					"idle": None,
					"hold": None,
					"osg id": str(submission_id) if submission_id is not None else None,
					"pool_node": row.get("pool_node"),
					"mysql_status": row.get("run_status"),
					"mysql_client_time": row.get("client_time"),
					"user_submission_id": submission_id,
					"priority": row.get("priority"),
				}
				results.append(entry)

		payload = {
			"owner": args.owner,
			"count": len(results),
			"results": results,
		}

		if args.print_screen:
			print(json.dumps(payload, indent=2, default=str))

		if args.json_file:
			output_path = Path(args.json_file).expanduser()
			output_path.parent.mkdir(parents=True, exist_ok=True)
			output_path.write_text(json.dumps(payload, indent=2, default=str) + "\n", encoding="utf-8")

		return 0

	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())