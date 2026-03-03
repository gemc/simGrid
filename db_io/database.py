#!/usr/bin/env python3
"""
Simple MySQL database helper built on top of pymysql.

This module provides a `Database` class that:

- reads connection credentials from a MySQL-style option file
- connects to a MySQL database using `pymysql`
- exposes methods to run queries and statements
- provides a convenience method to retrieve submission timing data

Expected credential file format:

    [client]
    user='user'
    password='pwd'
    host='address'
    database='dbname'

Example usage in Python:

    from database import Database

    with Database("db_credentials.cnf") as db:
        rows = db.query("SELECT * FROM submissions LIMIT 10")
        for row in rows:
            print(row)

Notes:
- Query results are returned as dictionaries keyed by column name.
- Positional SQL parameters use `%s` placeholders, as required by pymysql.
- For safety, prefer parameterized queries over string interpolation.
"""

from __future__ import annotations

import argparse
import configparser
import json
import sys
from pathlib import Path
from typing import Any, Optional, Sequence

import pymysql
from pymysql.cursors import DictCursor


class Database:
	"""
	Simple MySQL database wrapper using pymysql.

	The connection settings are read from a credential file with a `[client]`
	section containing:

		user='username'
		password='password'
		host='hostname'
		database='dbname'

	Parameters
	----------
	credentials_file:
		Path to the credential file.
	autocommit:
		Whether to enable autocommit on the database connection.
	"""

	def __init__(self, credentials_file: str | Path, autocommit: bool = True) -> None:
		self.credentials_file = Path(credentials_file)
		self.autocommit = autocommit
		self.connection: Optional[pymysql.connections.Connection] = None

	def _read_credentials(self) -> dict[str, str]:
		"""
		Read and validate database credentials from the option file.

		Returns
		-------
		dict[str, str]
			Dictionary containing user, password, host, and database.

		Raises
		------
		FileNotFoundError
			If the credential file does not exist.
		ValueError
			If the `[client]` section is missing or required keys are absent.
		"""
		if not self.credentials_file.is_file():
			raise FileNotFoundError(
				f"Credentials file not found: {self.credentials_file}"
			)

		parser = configparser.ConfigParser()
		parser.read(self.credentials_file)

		if "client" not in parser:
			raise ValueError(
				f"Missing [client] section in credentials file: {self.credentials_file}"
			)

		client = parser["client"]

		required_keys = ["user", "password", "host", "database"]
		missing = [key for key in required_keys if key not in client]
		if missing:
			raise ValueError(
				f"Missing required keys in [client]: {', '.join(missing)}"
			)

		return {
			"user":     client["user"].strip().strip("'").strip('"'),
			"password": client["password"].strip().strip("'").strip('"'),
			"host":     client["host"].strip().strip("'").strip('"'),
			"database": client["database"].strip().strip("'").strip('"'),
		}

	def connect(self) -> None:
		"""
		Open the database connection.

		If the connection is already open, this method replaces it with a new one.
		"""
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
		"""
		Close the database connection if it is open.
		"""
		if self.connection is not None:
			self.connection.close()
			self.connection = None

	def query(
			self,
			sql: str,
			params: Sequence[Any] | None = None,
	) -> list[dict[str, Any]]:
		"""
		Execute a SELECT-style query and return all rows.

		Parameters
		----------
		sql:
			SQL query string. Use `%s` placeholders for parameters.
		params:
			Optional sequence of parameters to bind to the query.

		Returns
		-------
		list[dict[str, Any]]
			Query results as a list of dictionaries.
		"""
		if self.connection is None:
			self.connect()

		assert self.connection is not None

		with self.connection.cursor() as cursor:
			cursor.execute(sql, tuple(params or ()))
			return list(cursor.fetchall())

	def query_one(
			self,
			sql: str,
			params: Sequence[Any] | None = None,
	) -> dict[str, Any] | None:
		"""
		Execute a query and return the first row only.

		Parameters
		----------
		sql:
			SQL query string. Use `%s` placeholders for parameters.
		params:
			Optional sequence of parameters to bind to the query.

		Returns
		-------
		dict[str, Any] | None
			The first result row, or None if no rows are returned.
		"""
		rows = self.query(sql, params)
		return rows[0] if rows else None

	def execute(
			self,
			sql: str,
			params: Sequence[Any] | None = None,
	) -> int:
		"""
		Execute a non-SELECT SQL statement.

		Typical use cases include INSERT, UPDATE, DELETE, CREATE, or ALTER.

		Parameters
		----------
		sql:
			SQL statement. Use `%s` placeholders for parameters.
		params:
			Optional sequence of parameters to bind to the statement.

		Returns
		-------
		int
			Number of affected rows.
		"""
		if self.connection is None:
			self.connect()

		assert self.connection is not None

		with self.connection.cursor() as cursor:
			affected_rows = cursor.execute(sql, tuple(params or ()))
			if not self.autocommit:
				self.connection.commit()
			return affected_rows

	def get_submissions_with_status(
			self,
			days_past: int | None = None,
			client_time_format: str = "%Y-%m-%d %H:%i:%s",
	) -> list[dict[str, Any]]:
		"""
		Return submission user, id, client_time, and run_status from the `submissions` table.

		Parameters
		----------
		days_past:
			If provided, restrict results to rows whose `client_time` is within
			the last N days.
		client_time_format:
			MySQL STR_TO_DATE format string used to parse the `client_time` text
			column.

		Returns
		-------
		list[dict[str, Any]]
			Rows with keys: user, user_submission_id, client_time, run_status
		"""
		if days_past is None:
			sql = """
                SELECT user, user_submission_id, client_time, run_status
                FROM submissions
                ORDER BY user_submission_id
            """
			params: tuple[Any, ...] = ()
		else:
			sql = """
                SELECT user, user_submission_id, client_time, run_status
                FROM submissions
                WHERE STR_TO_DATE(client_time, %s) >= NOW() - INTERVAL %s DAY
                ORDER BY user_submission_id
            """
			params = (client_time_format, days_past)

		return self.query(sql, params)

	def get_submission_times(
			self,
			days_past: int | None = None,
			client_time_format: str = "%Y-%m-%d %H:%i:%s",
	) -> list[dict[str, Any]]:
		"""
		Return submission user, id, and client_time from the `submissions` table.

		Parameters
		----------
		days_past:
			If provided, restrict results to rows whose `client_time` is within
			the last N days.
		client_time_format:
			MySQL STR_TO_DATE format string used to parse the `client_time` text
			column. The default assumes values like:

				2026-03-03 14:25:00

		Returns
		-------
		list[dict[str, Any]]
			Rows with keys: user, user_submission_id, client_time

		Notes
		-----
		This method assumes `client_time` is stored as text and can be parsed by
		MySQL with STR_TO_DATE(). If `client_time` is already a DATETIME/TIMESTAMP
		column, the query can be simplified.
		"""
		if days_past is None:
			sql = """
                SELECT user, user_submission_id, client_time
                FROM submissions
                ORDER BY user_submission_id
            """
			params: tuple[Any, ...] = ()
		else:
			sql = """
                SELECT user, user_submission_id, client_time
                FROM submissions
                WHERE STR_TO_DATE(client_time, %s) >= NOW() - INTERVAL %s DAY
                ORDER BY user_submission_id
            """
			params = (client_time_format, days_past)

		return self.query(sql, params)

	def __enter__(self) -> "Database":
		"""
		Enter context-manager scope by opening the connection.
		"""
		self.connect()
		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		"""
		Exit context-manager scope by closing the connection.
		"""
		self.close()


def build_parser() -> argparse.ArgumentParser:
	"""
	Build and return the command-line argument parser.

	Returns
	-------
	argparse.ArgumentParser
		Configured parser for command-line use.
	"""
	parser = argparse.ArgumentParser(
		description="Run SQL queries against a MySQL database using a credential file."
	)

	parser.add_argument(
		"-c",
		"--credentials",
		required=True,
		help="Path to the credential file.",
	)

	parser.add_argument(
		"-q",
		"--query",
		required=True,
		help="SQL query or statement to execute.",
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
		help="Disable autocommit.",
	)

	parser.add_argument(
		"--one",
		action="store_true",
		help="Return only the first row for SELECT queries.",
	)

	parser.add_argument(
		"--execute",
		action="store_true",
		help="Treat the SQL as a non-SELECT statement and return affected row count.",
	)

	parser.add_argument(
		"--indent",
		type=int,
		default=2,
		help="JSON indentation for printed query results (default: 2).",
	)

	return parser


def main() -> int:
	"""
	Command-line entry point.

	Returns
	-------
	int
		Process exit code.
	"""
	parser = build_parser()
	args = parser.parse_args()

	try:
		with Database(
				credentials_file=args.credentials,
				autocommit=not args.no_autocommit,
		) as db:
			if args.execute:
				count = db.execute(args.query, args.params)
				print(json.dumps({"affected_rows": count}, indent=args.indent))
			elif args.one:
				row = db.query_one(args.query, args.params)
				print(json.dumps(row, indent=args.indent, default=str))
			else:
				rows = db.query(args.query, args.params)
				print(json.dumps(rows, indent=args.indent, default=str))

		return 0

	except Exception as exc:
		print(f"Error: {exc}", file=sys.stderr)
		return 1


if __name__ == "__main__":
	raise SystemExit(main())
