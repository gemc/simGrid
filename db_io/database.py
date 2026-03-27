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

from __future__ import annotations

import argparse
import configparser
import json
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Sequence

import pymysql
from pymysql.cursors import DictCursor

DEFAULT_RECENT_SUBMISSIONS_QUERY = (
	"select user, client_time, user_submission_id, pool_node, run_status, priority "
	"from submissions "
	"WHERE STR_TO_DATE(client_time, '%Y-%m-%d %H:%i:%s') > NOW() - INTERVAL 1 DAY ;"
)


def debug(enabled: bool, message: str) -> None:
	"""Print a debug message when enabled."""
	if enabled:
		print(f"[DEBUG] {message}")


def current_timestamp() -> str:
	"""Return current local time formatted for the submissions table."""
	return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


class Database:
	"""Small MySQL wrapper built on top of pymysql."""

	def __init__(
			self,
			credentials_file: str | Path,
			autocommit: bool = True,
			database_name: str | None = None,
	) -> None:
		self.credentials_file = Path(credentials_file)
		self.autocommit = autocommit
		self.database_name = database_name
		self.connection: Optional[pymysql.connections.Connection] = None

	def _read_credentials(self) -> dict[str, str]:
		"""Read connection settings from a MySQL option file."""
		if not self.credentials_file.is_file():
			raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")

		parser = configparser.ConfigParser()
		parser.read(self.credentials_file)

		if "client" not in parser:
			raise ValueError(
				f"Missing [client] section in credentials file: {self.credentials_file}")

		client = parser["client"]
		required_keys = ["user", "password", "host", "database"]
		missing = [key for key in required_keys if key not in client]
		if missing:
			raise ValueError(f"Missing required keys in [client]: {', '.join(missing)}")

		database = client["database"].strip().strip("'").strip('"')
		if self.database_name is not None:
			database = self.database_name

		return {
			"user":     client["user"].strip().strip("'").strip('"'),
			"password": client["password"].strip().strip("'").strip('"'),
			"host":     client["host"].strip().strip("'").strip('"'),
			"database": database,
		}

	def connect(self) -> None:
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

	def close(self) -> None:
		"""Close the current MySQL connection."""
		if self.connection is not None:
			self.connection.close()
			self.connection = None

	def query(self, sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
		"""Run a SELECT-style query and return all rows."""
		if self.connection is None:
			self.connect()

		assert self.connection is not None
		with self.connection.cursor() as cursor:
			cursor.execute(sql, tuple(params) if params is not None else None)
			return list(cursor.fetchall())

	def query_one(self, sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
		"""Run a query and return the first row, or None."""
		rows = self.query(sql, params)
		return rows[0] if rows else None

	def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
		"""Run a non-SELECT statement and return affected row count."""
		if self.connection is None:
			self.connect()

		assert self.connection is not None
		with self.connection.cursor() as cursor:
			affected_rows = cursor.execute(sql, tuple(params) if params is not None else None)
			if not self.autocommit:
				self.connection.commit()
			return affected_rows

	def get_recent_submissions(self) -> list[dict[str, Any]]:
		"""Return recent submissions using the default query."""
		return self.query(DEFAULT_RECENT_SUBMISSIONS_QUERY)

	def get_user_id(self, username: str) -> int | None:
		"""Return the user_id for username, or None if absent."""
		row = self.query_one("SELECT user_id FROM users WHERE user = %s", [username])
		if row is None:
			return None
		return int(row["user_id"])

	def ensure_user(self, username: str, debug_enabled: bool = False) -> int:
		"""Ensure a user exists in the users table and return user_id."""
		existing_user_id = self.get_user_id(username)
		if existing_user_id is not None:
			debug(debug_enabled,
			      f"User '{username}' already exists with user_id={existing_user_id}")
			return existing_user_id

		debug(debug_enabled, f"Creating user '{username}'")
		self.execute("INSERT INTO users (user) VALUES (%s)", [username])

		created_user_id = self.get_user_id(username)
		if created_user_id is None:
			raise RuntimeError(f"Failed to create or retrieve user_id for user '{username}'")
		return created_user_id

	def insert_submission(
			self,
			*,
			username: str,
			user_id: int,
			client_time: str,
			pool_node: str,
			scard: str,
			run_status: str = "Not Submitted",
			client_ip: str | None = None,
			priority: int = 0,
			debug_enabled: bool = False,
	) -> int:
		"""Insert a row into submissions and return user_submission_id."""
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
			[username, user_id, client_time, pool_node, scard, client_ip, run_status, priority],
		)

		row = self.query_one("SELECT LAST_INSERT_ID() AS user_submission_id")
		if row is None or row.get("user_submission_id") is None:
			raise RuntimeError("Failed to retrieve user_submission_id after INSERT")

		submission_id = int(row["user_submission_id"])
		debug(debug_enabled, f"Inserted submission with user_submission_id={submission_id}")
		return submission_id

	def update_priorities(self, prioritized_pending_rows: list[dict[str, Any]]) -> int:
		"""Update the priority field for many submission rows."""
		if not prioritized_pending_rows:
			return 0

		params: list[tuple[str, int]] = []
		for row in prioritized_pending_rows:
			if "user_submission_id" not in row or "priority" not in row:
				raise ValueError(
					"Each row must have 'user_submission_id' and 'priority' keys. "
					f"Got: {list(row.keys())}"
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
			days_past: int | None = None,
			client_time_format: str = "%Y-%m-%d %H:%i:%s",
	) -> list[dict[str, Any]]:
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
			days_past: int | None = None,
			client_time_format: str = "%Y-%m-%d %H:%i:%s",
	) -> list[dict[str, Any]]:
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

	def __enter__(self) -> "Database":
		self.connect()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		self.close()


def build_parser() -> argparse.ArgumentParser:
	"""Build the CLI parser for ad hoc SQL queries."""
	parser = argparse.ArgumentParser(
		description="Run SQL queries against a MySQL database using a credential file."
	)
	parser.add_argument(
		"-c", "--credentials",
		default=str(Path("~/hello.txt").expanduser()),
		help="Path to the credential file. Default: ~/hello.txt"
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
	parser.add_argument("--no-autocommit", action="store_true", help="Disable autocommit.")
	parser.add_argument("--one", action="store_true",
	                    help="Return only the first row for SELECT queries.")
	parser.add_argument("--execute", action="store_true",
	                    help="Treat the SQL as a non-SELECT statement.")
	parser.add_argument("--indent", type=int, default=2, help="JSON indentation for output.")
	parser.add_argument("--database", help="Override the database name from the credential file.")
	return parser


def main() -> int:
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
				payload: Any = {"affected_rows": db.execute(args.query, args.params)}
			elif args.one:
				payload = db.query_one(args.query, args.params)
			else:
				payload = db.query(args.query, args.params)
			print(json.dumps(payload, indent=args.indent, default=str))
		return 0
	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
