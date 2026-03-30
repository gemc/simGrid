#!/usr/bin/env python3
"""
list_owner_submission.py

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
  -dev          use CLAS12TEST instead of production CLAS12OCR

Behavior:
  - no options => print help and exit
"""

import os
import sys
import argparse
import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from htcondor_utils import get_owner_batches, format_submitted_time
from db_io.database import Database, DEFAULT_CREDENTIALS_FILE

PRODUCTION_DATABASE = "CLAS12OCR"
TEST_DATABASE = "CLAS12TEST"


def build_parser():
	# type: () -> argparse.ArgumentParser
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
		default=str(DEFAULT_CREDENTIALS_FILE),
		help="MySQL credential file. Default: {0}".format(DEFAULT_CREDENTIALS_FILE),
	)
	parser.add_argument(
		"-dev",
		action="store_true",
		help="Use test database CLAS12TEST instead of production CLAS12OCR.",
	)
	return parser


def safe_int(value):
	# type: (Any) -> Optional[int]
	if value is None:
		return None
	try:
		return int(value)
	except (TypeError, ValueError):
		return None


def build_condor_entry(cluster_id, batch):
	# type: (int, Dict[str, Any]) -> Dict[str, Any]
	total = safe_int(batch.get("total_submit_procs")) or 0
	counts = batch.get("counts", {})

	run = safe_int(counts.get("RUN")) or 0
	idle = safe_int(counts.get("IDLE")) or 0
	hold = safe_int(counts.get("HOLD")) or 0
	other = safe_int(counts.get("OTHER")) or 0

	done = max(total - run - idle - hold - other, 0)

	return {
		"user":               batch.get("owner"),
		"job id":             cluster_id,
		"submitted":          format_submitted_time(batch.get("submitted_epoch")),
		"total":              total,
		"done":               done,
		"run":                run,
		"idle":               idle,
		"hold":               hold,
		"osg id":             None,
		"pool_node":          str(cluster_id),
		"mysql_status":       None,
		"mysql_client_time":  None,
		"user_submission_id": None,
		"priority":           batch.get("current_priority"),
	}


def empty_db_payload(database_name, owner, timestamp):
	# type: (str, str, str) -> Dict[str, Any]
	return {
		"update_timestamp": {
			"time": timestamp,
		},
		"database":         database_name,
		"owner":            owner,
		"count":            0,
		"results":          [],
	}


def collect_for_database(owner, credentials, database_name):
	# type: (str, str, str) -> Dict[str, Any]
	batches = get_owner_batches(owner)

	results = []  # type: List[Dict[str, Any]]
	seen_submission_ids = set()  # type: Set[int]

	with Database(
			credentials_file=credentials,
			database_name=database_name,
	) as db:

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

			# Do not show condor-only jobs that are not present in the database
			if mysql_row is None:
				continue

			if mysql_row.get("user_submission_id") is not None:
				entry["osg id"] = str(mysql_row["user_submission_id"])
				entry["user_submission_id"] = mysql_row["user_submission_id"]
				seen_submission_ids.add(int(mysql_row["user_submission_id"]))

			entry["mysql_status"] = mysql_row.get("run_status")
			entry["mysql_client_time"] = mysql_row.get("client_time")
			entry["priority"] = mysql_row.get("priority", entry["priority"])

			if mysql_row.get("user") is not None:
				entry["user"] = mysql_row["user"]

			results.append(entry)

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
			pool_node = row.get("pool_node")

			if submission_id is not None and submission_id in seen_submission_ids:
				continue

			entry = {
				"user":               row.get("user"),
				"job id":             safe_int(pool_node),
				"submitted":          row.get("client_time"),
				"total":              None,
				"done":               None,
				"run":                None,
				"idle":               None,
				"hold":               None,
				"osg id":             str(submission_id) if submission_id is not None else None,
				"pool_node":          pool_node,
				"mysql_status":       row.get("run_status"),
				"mysql_client_time":  row.get("client_time"),
				"user_submission_id": submission_id,
				"priority":           row.get("priority"),
			}
			results.append(entry)

	return {
		"database": database_name,
		"owner":    owner,
		"count":    len(results),
		"results":  results,
	}


def main():
	# type: () -> int
	parser = build_parser()

	if len(sys.argv) == 1:
		parser.print_help()
		return 0

	args = parser.parse_args()

	if not args.print_screen and not args.json_file:
		print("Error: use -q and/or -j FILE", file=sys.stderr)
		return 1

	selected_database = TEST_DATABASE if args.dev else PRODUCTION_DATABASE
	update_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

	try:
		selected_payload = collect_for_database(
			owner=args.owner,
			credentials=args.credentials,
			database_name=selected_database,
		)

		final_payload = {
			"CLAS12OCR":  empty_db_payload(PRODUCTION_DATABASE, args.owner, update_time),
			"CLAS12TEST": empty_db_payload(TEST_DATABASE, args.owner, update_time),
		}

		final_payload[selected_database] = {
			"update_timestamp": {
				"time": update_time,
			},
			"database":         selected_payload["database"],
			"owner":            selected_payload["owner"],
			"count":            selected_payload["count"],
			"results":          selected_payload["results"],
		}

		if args.print_screen:
			print(json.dumps(final_payload, indent=2, default=str))

		if args.json_file:
			output_path = Path(args.json_file).expanduser()
			output_dir = output_path.parent
			if not output_dir.exists():
				output_dir.mkdir(parents=True)

			with output_path.open("w") as fh:
				json.dump(final_payload, fh, indent=2, default=str)
				fh.write("\n")

		return 0

	except Exception as exc:
		print("Error: {0}".format(exc), file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
