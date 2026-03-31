#!/usr/bin/env python3
"""
MySQL database helper utilities for submissions.

This module centralizes:
- connection handling
- shared debug/timestamp helpers
- common query helpers
- user lookup/creation
- submission insert helpers
"""

import argparse
import configparser
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence

import pymysql
from pymysql.cursors import DictCursor

DEFAULT_RECENT_SUBMISSIONS_QUERY = (
	"select user, client_time, user_submission_id, pool_node, run_status, priority "
	"from submissions "
	"WHERE STR_TO_DATE(client_time, '%Y-%m-%d %H:%i:%s') > NOW() - INTERVAL 1 DAY ;"
)

DEFAULT_CREDENTIALS_FILE = Path("/home/gemc/msql_conn.txt").expanduser()


def debug(enabled, message):
	"""Print a debug message when enabled."""
	if enabled:
		print("[DEBUG] {0}".format(message))


def current_timestamp():
	"""Return current local time formatted for the submissions table."""
	return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database(object):
	"""Small MySQL wrapper built on top of pymysql."""

	def __init__(
			self,
			credentials_file=None,  # type: Optional[str]
			autocommit=True,  # type: bool
			database_name=None  # type: Optional[str]
	):
		# type: (...) -> None
		self.credentials_file = (
			Path(credentials_file).expanduser()
			if credentials_file is not None
			else DEFAULT_CREDENTIALS_FILE
		)
		self.autocommit = autocommit
		self.database_name = database_name
		self.connection = None  # type: Optional[pymysql.connections.Connection]

	def _read_credentials(self):
		# type: () -> Dict[str, str]
		"""Read connection settings from a MySQL option file."""
		if not self.credentials_file.is_file():
			raise FileNotFoundError(
				"Credentials file not found: {0}".format(self.credentials_file)
			)

		parser = configparser.ConfigParser()
		parser.read(str(self.credentials_file))

		if "client" not in parser:
			raise ValueError(
				"Missing [client] section in credentials file: {0}".format(
					self.credentials_file
				)
			)

		client = parser["client"]
		required_keys = ["user", "password", "host", "database"]
		missing = [key for key in required_keys if key not in client]
		if missing:
			raise ValueError(
				"Missing required keys in [client]: {0}".format(", ".join(missing))
			)

		database = client["database"].strip().strip("'").strip('"')
		if self.database_name is not None:
			database = self.database_name

		return {
			"user":     client["user"].strip().strip("'").strip('"'),
			"password": client["password"].strip().strip("'").strip('"'),
			"host":     client["host"].strip().strip("'").strip('"'),
			"database": database,
		}

	def connect(self):
		# type: () -> None
		"""Open the MySQL connection if needed."""
		if self.connection is not None:
			return

		creds = self._read_credentials()
		self.connection = pymysql.connect(
			host=creds["host"],
			user=creds["user"],
			password=creds["password"],
			database=creds["database"],
			cursorclass=DictCursor,
			autocommit=self.autocommit,
		)

	def close(self):
		# type: () -> None
		"""Close the current MySQL connection."""
		if self.connection is not None:
			self.connection.close()
			self.connection = None

	def query(self, sql, params=None):
		# type: (str, Optional[Sequence[Any]]) -> List[Dict[str, Any]]
		"""Run a SELECT-style query and return all rows."""
		if self.connection is None:
			self.connect()

		assert self.connection is not None
		with self.connection.cursor() as cursor:
			cursor.execute(sql, tuple(params) if params is not None else None)
			return list(cursor.fetchall())

	def query_one(self, sql, params=None):
		# type: (str, Optional[Sequence[Any]]) -> Optional[Dict[str, Any]]
		"""Run a query and return the first row, or None."""
		rows = self.query(sql, params)
		return rows[0] if rows else None

	def execute(self, sql, params=None):
		# type: (str, Optional[Sequence[Any]]) -> int
		"""Run a non-SELECT statement and return affected row count."""
		if self.connection is None:
			self.connect()

		assert self.connection is not None
		with self.connection.cursor() as cursor:
			affected_rows = cursor.execute(
				sql, tuple(params) if params is not None else None
			)
			if not self.autocommit:
				self.connection.commit()
			return affected_rows

	def get_recent_submissions(self):
		# type: () -> List[Dict[str, Any]]
		"""Return recent submissions using the default query."""
		return self.query(DEFAULT_RECENT_SUBMISSIONS_QUERY)

	def get_user_id(self, username):
		# type: (str) -> Optional[int]
		"""Return the user_id for username, or None if absent."""
		row = self.query_one("SELECT user_id FROM users WHERE user = %s", [username])
		if row is None:
			return None
		return int(row["user_id"])

	def ensure_user(self, username, debug_enabled=False):
		# type: (str, bool) -> int
		"""Ensure a user exists in the users table and return user_id."""
		existing_user_id = self.get_user_id(username)
		if existing_user_id is not None:
			debug(
				debug_enabled,
				"User '{0}' already exists with user_id={1}".format(
					username, existing_user_id
				),
			)
			return existing_user_id

		debug(debug_enabled, "Creating user '{0}'".format(username))
		self.execute("INSERT INTO users (user) VALUES (%s)", [username])

		created_user_id = self.get_user_id(username)
		if created_user_id is None:
			raise RuntimeError(
				"Failed to create or retrieve user_id for user '{0}'".format(username)
			)
		return created_user_id

	def insert_submission(
			self,
			username,  # type: str
			user_id,  # type: int
			client_time,  # type: str
			pool_node,  # type: str
			scard,  # type: str
			run_status="Not Submitted",  # type: str
			client_ip=None,  # type: Optional[str]
			priority=0,  # type: int
			debug_enabled=False  # type: bool
	):
		# type: (...) -> int
		"""Insert a row into submissions and return user_submission_id."""
		if self.database_name == "CLAS12TEST":
			priority = 1

		debug(debug_enabled, "Inserting submission row")
		sql = """
            INSERT INTO submissions (
                user,
                user_id,
                client_time,
                pool_node,
                scard,
                client_ip,
                run_status,
                priority
            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        """
		self.execute(
			sql,
			[
				username,
				user_id,
				client_time,
				pool_node,
				scard,
				client_ip,
				run_status,
				priority,
			],
		)

		row = self.query_one("SELECT LAST_INSERT_ID() AS user_submission_id")
		if row is None or row.get("user_submission_id") is None:
			raise RuntimeError("Failed to retrieve user_submission_id after INSERT")

		submission_id = int(row["user_submission_id"])
		debug(
			debug_enabled,
			"Inserted submission with user_submission_id={0}".format(submission_id),
		)
		return submission_id

	def update_priorities(self, prioritized_pending_rows):
		# type: (List[Dict[str, Any]]) -> int
		"""Update the priority field for many submission rows."""
		if not prioritized_pending_rows:
			return 0

		params = []  # type: List[tuple]
		for row in prioritized_pending_rows:
			if "user_submission_id" not in row or "priority" not in row:
				raise ValueError(
					"Each row must have 'user_submission_id' and 'priority' keys. "
					"Got: {0}".format(list(row.keys()))
				)
			params.append((str(row["priority"]), int(row["user_submission_id"])))

		if self.connection is None:
			self.connect()

		assert self.connection is not None
		sql = """
            UPDATE submissions
            SET priority = %s
            WHERE user_submission_id = %s
        """
		with self.connection.cursor() as cursor:
			affected_rows = cursor.executemany(sql, params)
			if not self.autocommit:
				self.connection.commit()
		return affected_rows

	def get_submissions_with_status(
			self,
			days_past=None,  # type: Optional[int]
			client_time_format="%Y-%m-%d %H:%i:%s"  # type: str
	):
		# type: (...) -> List[Dict[str, Any]]
		"""Return submission rows including run_status."""
		if days_past is None:
			return self.query(
				"""
				SELECT user, user_submission_id, client_time, run_status
				FROM submissions
				ORDER BY user_submission_id
				"""
			)

		return self.query(
			"""
			SELECT user, user_submission_id, client_time, run_status
			FROM submissions
			WHERE client_time IS NOT NULL
			  AND TRIM(client_time) != ''
			  AND STR_TO_DATE(client_time, %s) IS NOT NULL
			  AND STR_TO_DATE(client_time, %s) >= NOW() - INTERVAL %s DAY
			ORDER BY user_submission_id
			""",
			[client_time_format, client_time_format, days_past],
		)

	def get_submission_times(
			self,
			days_past=None,  # type: Optional[int]
			client_time_format="%Y-%m-%d %H:%i:%s"  # type: str
	):
		# type: (...) -> List[Dict[str, Any]]
		"""Return submission rows with timing fields only."""
		if days_past is None:
			return self.query(
				"""
				SELECT user, user_submission_id, client_time
				FROM submissions
				ORDER BY user_submission_id
				"""
			)

		return self.query(
			"""
			SELECT user, user_submission_id, client_time
			FROM submissions
			WHERE STR_TO_DATE(client_time, %s) >= NOW() - INTERVAL %s DAY
			ORDER BY user_submission_id
			""",
			[client_time_format, days_past],
		)

	def insert_owner_submission_snapshot(
			self,
			database_name,  # type: str
			owner,  # type: str
			update_time,  # type: str
			payload,  # type: Dict[str, Any]
			keep_last=100,  # type: int
			debug_enabled=False  # type: bool
	):
		# type: (...) -> int
		"""Insert one owner-submission JSON snapshot and keep only the newest N rows."""
		payload_json = json.dumps(payload, default=str)

		debug(
			debug_enabled,
			"Inserting owner submission snapshot for database={0}, owner={1}".format(
				database_name, owner
			),
		)

		sql = """
			INSERT INTO owner_submission_snapshots (
				database_name,
				owner,
				update_time,
				payload_json
			) VALUES (%s, %s, %s, %s)
		"""
		self.execute(sql, [database_name, owner, update_time, payload_json])

		row = self.query_one("SELECT LAST_INSERT_ID() AS snapshot_id")
		if row is None or row.get("snapshot_id") is None:
			raise RuntimeError("Failed to retrieve snapshot_id after INSERT")

		snapshot_id = int(row["snapshot_id"])

		self.prune_owner_submission_snapshots(
			database_name=database_name,
			owner=owner,
			keep_last=keep_last,
			debug_enabled=debug_enabled,
		)

		return snapshot_id

	def prune_owner_submission_snapshots(
			self,
			database_name,  # type: str
			owner,  # type: str
			keep_last=100,  # type: int
			debug_enabled=False  # type: bool
	):
		# type: (...) -> int
		"""Delete older owner-submission snapshots, keeping only the newest N."""
		if keep_last <= 0:
			raise ValueError("keep_last must be > 0")

		debug(
			debug_enabled,
			"Pruning owner submission snapshots for database={0}, owner={1}, keep_last={2}".format(
				database_name, owner, keep_last
			),
		)

		sql = """
			DELETE FROM owner_submission_snapshots
			WHERE database_name = %s
			  AND owner = %s
			  AND snapshot_id NOT IN (
				  SELECT snapshot_id
				  FROM (
					  SELECT snapshot_id
					  FROM owner_submission_snapshots
					  WHERE database_name = %s
					    AND owner = %s
					  ORDER BY update_time DESC, snapshot_id DESC
					  LIMIT %s
				  ) AS kept
			  )
		"""
		return self.execute(sql, [database_name, owner, database_name, owner, keep_last])

	def get_latest_owner_submission_snapshot(
			self,
			database_name,  # type: str
			owner  # type: str
	):
		# type: (...) -> Optional[Dict[str, Any]]
		"""Return the latest stored owner-submission payload as a Python dict."""
		row = self.query_one(
			"""
			SELECT snapshot_id, update_time, payload_json
			FROM owner_submission_snapshots
			WHERE database_name = %s
			  AND owner = %s
			ORDER BY update_time DESC, snapshot_id DESC
			LIMIT 1
			""",
			[database_name, owner],
		)

		if row is None:
			return None

		payload = row["payload_json"]
		if isinstance(payload, str):
			payload = json.loads(payload)

		return {
			"snapshot_id": row["snapshot_id"],
			"update_time": row["update_time"],
			"payload":     payload,
		}

	def get_owner_submission_snapshots(
			self,
			database_name,  # type: str
			owner,  # type: str
			limit=100  # type: int
	):
		# type: (...) -> List[Dict[str, Any]]
		"""Return up to limit stored owner-submission payloads, newest first."""
		rows = self.query(
			"""
			SELECT snapshot_id, update_time, payload_json
			FROM owner_submission_snapshots
			WHERE database_name = %s
			  AND owner = %s
			ORDER BY update_time DESC, snapshot_id DESC
			LIMIT %s
			""",
			[database_name, owner, limit],
		)

		results = []
		for row in rows:
			payload = row["payload_json"]
			if isinstance(payload, str):
				payload = json.loads(payload)

			results.append(
				{
					"snapshot_id": row["snapshot_id"],
					"update_time": row["update_time"],
					"payload":     payload,
				}
			)

		return results

	def export_latest_owner_submission_payload(
			self,
			database_name,  # type: str
			owner  # type: str
	):
		# type: (...) -> Optional[Dict[str, Any]]
		"""Compatibility helper: return only the latest JSON payload."""
		row = self.get_latest_owner_submission_snapshot(database_name, owner)
		if row is None:
			return None
		return row["payload"]

	def __enter__(self):
		# type: () -> "Database"
		self.connect()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb):
		# type: (Any, Any, Any) -> None
		self.close()


def build_parser():
	# type: () -> argparse.ArgumentParser
	"""Build the CLI parser for ad hoc SQL queries."""
	parser = argparse.ArgumentParser(
		description="Run SQL queries against a MySQL database using a credential file."
	)
	parser.add_argument(
		"-c",
		"--credentials",
		default=str(DEFAULT_CREDENTIALS_FILE),
		help="Path to the credential file. Default: {0}".format(
			DEFAULT_CREDENTIALS_FILE
		),
	)
	parser.add_argument(
		"-q",
		"--query",
		default=DEFAULT_RECENT_SUBMISSIONS_QUERY,
		help="SQL query or statement to execute. Defaults to the recent submissions query.",
	)
	parser.add_argument(
		"-p",
		"--params",
		nargs="*",
		default=[],
		help="Optional positional SQL parameters, passed in order.",
	)
	parser.add_argument(
		"--no-autocommit",
		action="store_true",
		help="Disable autocommit."
	)
	parser.add_argument(
		"--one",
		action="store_true",
		help="Return only the first row for SELECT queries."
	)
	parser.add_argument(
		"--execute",
		action="store_true",
		help="Treat the SQL as a non-SELECT statement."
	)
	parser.add_argument(
		"--indent",
		type=int,
		default=2,
		help="JSON indentation for output."
	)
	parser.add_argument(
		"--database",
		help="Override the database name from the credential file."
	)
	return parser


def main():
	# type: () -> int
	"""Run the database command-line utility."""
	parser = build_parser()
	args = parser.parse_args()

	try:
		with Database(
				args.credentials,
				autocommit=not args.no_autocommit,
				database_name=args.database,
		) as db:
			if args.execute:
				payload = {"affected_rows": db.execute(args.query, args.params)}
			elif args.one:
				payload = db.query_one(args.query, args.params)
			else:
				payload = db.query(args.query, args.params)

			print(json.dumps(payload, indent=args.indent, default=str))
		return 0
	except Exception as exc:
		print("Error: {0}".format(exc), file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
