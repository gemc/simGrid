#!/usr/bin/env python3
"""
list_owner_submission.py

Build a combined view of:
1. HTCondor batches for one owner (via get_owner_batches)
2. Matching MySQL submission rows where submissions.pool_node == ClusterId
3. Extra MySQL rows with pending or terminal pre-submit statuses

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
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
	sys.path.insert(0, PROJECT_ROOT)

from db_io.database import Database, DEFAULT_CREDENTIALS_FILE, print_job
from statuses import FAILED_TO_READ_DIRECTORY, NOTSUBMITTED

PRODUCTION_DATABASE = "CLAS12OCR"
TEST_DATABASE = "CLAS12TEST"
TERMINAL_PRE_SUBMIT_STATUSES = {FAILED_TO_READ_DIRECTORY}
PROGRESS_WINDOW_HOURS = 6
PROGRESS_SNAPSHOT_LIMIT = 100


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
	parser.add_argument(
		"--store-db",
		action="store_true",
		help="Store the generated payload into owner_submission_snapshots.",
	)
	parser.add_argument(
		"--from-db",
		action="store_true",
		help="Read the latest payload from owner_submission_snapshots instead of rebuilding it.",
	)
	parser.add_argument(
		"--keep-last",
		type=int,
		default=100,
		help="How many snapshots to keep per database/owner. Default: %(default)s",
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
	from htcondor_utils import format_submitted_time
	total = safe_int(batch.get("total_submit_procs")) or 0
	counts = batch.get("counts", {})

	run = safe_int(counts.get("RUN")) or 0
	idle = safe_int(counts.get("IDLE")) or 0
	hold = safe_int(counts.get("HOLD")) or 0
	other = safe_int(counts.get("OTHER")) or 0

	done = max(total - run - idle - hold - other, 0)

	condor_osg_id = str(cluster_id)

	return {
		"user":               batch.get("owner"),
		"submission id":      None,
		"submitted on":       format_submitted_time(batch.get("submitted_epoch")),
		"jobs":               total,
		"done":               done,
		"run":                run,
		"idle":               idle,
		"hold":               hold,
		"osg id":             condor_osg_id,
		"pool_node":          condor_osg_id,
		"mysql_status":       None,
		"mysql_client_time":  None,
		"user_submission_id": None,
		"priority":           batch.get("current_priority"),
	}


def apply_terminal_pre_submit_status(entry, status):
	# type: (Dict[str, Any], str) -> None
	"""Show terminal pre-submit failures as DB status, not Condor state."""
	if status not in TERMINAL_PRE_SUBMIT_STATUSES:
		return

	entry["jobs"] = None
	entry["done"] = None
	entry["run"] = None
	entry["idle"] = None
	entry["hold"] = None
	entry["osg id"] = status
	entry["pool_node"] = None


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


def snapshot_update_time(snapshot):
	# type: (Dict[str, Any]) -> Optional[datetime]
	"""Return a snapshot update time as a datetime."""
	value = snapshot.get("update_time")
	if isinstance(value, datetime):
		return value
	if isinstance(value, str):
		for time_format in ("%Y-%m-%d %H:%M:%S.%f", "%Y-%m-%d %H:%M:%S"):
			try:
				return datetime.strptime(value, time_format)
			except ValueError:
				continue
	return None


def select_progress_snapshot(snapshots, current_time, window_hours=PROGRESS_WINDOW_HOURS):
	# type: (List[Dict[str, Any]], datetime, int) -> Optional[Dict[str, Any]]
	"""Return the newest snapshot at least window_hours older than current_time."""
	cutoff = current_time - timedelta(hours=window_hours)
	eligible = [
		snapshot
		for snapshot in snapshots
		if snapshot_update_time(snapshot) is not None
		and snapshot_update_time(snapshot) <= cutoff
	]
	if not eligible:
		return None
	return max(eligible, key=lambda snapshot: snapshot_update_time(snapshot))


def add_progress_history(current_results, historical_snapshot, database_name, current_time):
	# type: (List[Dict[str, Any]], Optional[Dict[str, Any]], str, datetime) -> None
	"""Attach previous done counts to rows also present in a historical snapshot."""
	if historical_snapshot is None:
		return

	historical_time = snapshot_update_time(historical_snapshot)
	if historical_time is None:
		return

	payload = historical_snapshot.get("payload", {})
	database_payload = payload.get(database_name, {}) if isinstance(payload, dict) else {}
	historical_results = database_payload.get("results", [])
	if not isinstance(historical_results, list):
		return

	historical_done = {}
	for row in historical_results:
		if not isinstance(row, dict):
			continue
		submission_id = safe_int(row.get("user_submission_id", row.get("submission id")))
		done = safe_int(row.get("done"))
		if submission_id is not None and done is not None:
			historical_done[submission_id] = done

	window_hours = (current_time - historical_time).total_seconds() / 3600.0
	for row in current_results:
		submission_id = safe_int(row.get("user_submission_id", row.get("submission id")))
		if submission_id in historical_done:
			row["progress_previous_done"] = historical_done[submission_id]
			row["progress_window_hours"] = round(window_hours, 3)


## type: (str, str, str) -> Dict[str, Any]
def collect_for_database(owner, credentials, database_name):
	from htcondor_utils import get_owner_batches
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

			condor_pool_node = str(cluster_id)

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
				[condor_pool_node],
			)

			if mysql_row is None:
				continue

			if mysql_row.get("user_submission_id") is not None:
				entry["submission id"] = mysql_row["user_submission_id"]
				entry["user_submission_id"] = mysql_row["user_submission_id"]
				seen_submission_ids.add(int(mysql_row["user_submission_id"]))

			entry["osg id"] = str(mysql_row.get("pool_node")) if mysql_row.get(
				"pool_node") is not None else entry["osg id"]
			entry["pool_node"] = mysql_row.get("pool_node")
			entry["mysql_status"] = mysql_row.get("run_status")
			entry["mysql_client_time"] = mysql_row.get("client_time")
			entry["priority"] = mysql_row.get("priority", entry["priority"])
			apply_terminal_pre_submit_status(entry, entry["mysql_status"])

			if mysql_row.get("user") is not None:
				entry["user"] = mysql_row["user"]

			results.append(entry)

		extra_statuses = [NOTSUBMITTED, FAILED_TO_READ_DIRECTORY]
		extra_rows = db.query(
			"""
			SELECT user,
			       user_submission_id,
			       client_time,
			       pool_node,
			       run_status,
			       priority
			FROM submissions
			WHERE run_status IN (%s, %s)
			ORDER BY user_submission_id
			""",
			extra_statuses,
		)

		for row in extra_rows:
			submission_id = safe_int(row.get("user_submission_id"))
			pool_node = row.get("pool_node")
			run_status = row.get("run_status")

			if submission_id is not None and submission_id in seen_submission_ids:
				continue

			if run_status in TERMINAL_PRE_SUBMIT_STATUSES:
				pool_node = None

			entry = {
				"user":               row.get("user"),
				"submission id":      submission_id,
				"submitted on":       row.get("client_time"),
				"jobs":               None,
				"done":               None,
				"run":                None,
				"idle":               None,
				"hold":               None,
				"osg id":             str(pool_node) if pool_node is not None else run_status,
				"pool_node":          pool_node,
				"mysql_status":       run_status,
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

	if (
			not args.print_screen
			and not args.json_file
			and not args.store_db
			and not args.from_db
	):
		print(
			"Error: use -q and/or -j FILE and/or --store-db and/or --from-db",
			file=sys.stderr,
		)
		return 1

	selected_database = TEST_DATABASE if args.dev else PRODUCTION_DATABASE
	current_time = datetime.now()
	update_time = current_time.strftime("%Y-%m-%d %H:%M:%S")

	try:
		with Database(
				credentials_file=args.credentials,
				database_name=selected_database,
		) as db:

			if args.from_db:
				final_payload = db.export_latest_owner_submission_payload(
					database_name=selected_database,
					owner=args.owner,
				)
				if final_payload is None:
					raise RuntimeError(
						"No stored snapshot found for database={0}, owner={1}".format(
							selected_database, args.owner
						)
					)
			else:
				selected_payload = collect_for_database(
					owner=args.owner,
					credentials=args.credentials,
					database_name=selected_database,
				)

				final_payload = {
					"CLAS12OCR":  empty_db_payload(
						PRODUCTION_DATABASE, args.owner, update_time
					),
					"CLAS12TEST": empty_db_payload(
						TEST_DATABASE, args.owner, update_time
					),
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

				snapshots = db.get_owner_submission_snapshots(
					database_name=selected_database,
					owner=args.owner,
					limit=PROGRESS_SNAPSHOT_LIMIT,
				)
				historical_snapshot = select_progress_snapshot(
					snapshots,
					current_time,
				)
				add_progress_history(
					final_payload[selected_database]["results"],
					historical_snapshot,
					selected_database,
					current_time,
				)

				if args.store_db:
					db.insert_owner_submission_snapshot(
						database_name=selected_database,
						owner=args.owner,
						update_time=update_time,
						payload=final_payload,
						keep_last=args.keep_last,
					)

		if args.print_screen:
			results = final_payload.get(selected_database, {}).get("results", [])
			for entry in results:
				print_job(entry)

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
