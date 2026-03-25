#!/usr/bin/env python3

"""
Simple MySQL database helper built on top of pymysql.

This module provides a `Database` class that:

- reads connection credentials from a MySQL-style option file
- connects to a MySQL database using `pymysql`
- exposes methods to run queries and statements
- provides convenience methods for common submission queries

Expected credential file format:

    [client]
    user='user'
    password='pwd'
    host='address'
    database='dbname'
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


DEFAULT_RECENT_SUBMISSIONS_QUERY = (
    "select user, client_time, user_submission_id, pool_node, run_status, priority "
    "from submissions "
    "WHERE STR_TO_DATE(client_time, '%Y-%m-%d %H:%i:%s') > NOW() - INTERVAL 1 DAY ;"
)


class Database:
    """Simple MySQL database wrapper using pymysql."""

    def __init__(self, credentials_file: str | Path, autocommit: bool = True) -> None:
        self.credentials_file = Path(credentials_file)
        self.autocommit = autocommit
        self.connection: Optional[pymysql.connections.Connection] = None

    def _read_credentials(self) -> dict[str, str]:
        """Read and validate connection settings from the credential file.

        Returns
        -------
        dict[str, str]
            Dictionary containing the values required by `pymysql.connect()`.

        Raises
        ------
        FileNotFoundError
            If the credentials file does not exist.
        ValueError
            If the `[client]` section or a required key is missing.
        """
        if not self.credentials_file.is_file():
            raise FileNotFoundError(f"Credentials file not found: {self.credentials_file}")

        parser = configparser.ConfigParser()
        parser.read(self.credentials_file)

        if "client" not in parser:
            raise ValueError(f"Missing [client] section in credentials file: {self.credentials_file}")

        client = parser["client"]
        required_keys = ["user", "password", "host", "database"]
        missing = [key for key in required_keys if key not in client]
        if missing:
            raise ValueError(f"Missing required keys in [client]: {', '.join(missing)}")

        return {
            "user": client["user"].strip().strip("'").strip('"'),
            "password": client["password"].strip().strip("'").strip('"'),
            "host": client["host"].strip().strip("'").strip('"'),
            "database": client["database"].strip().strip("'").strip('"'),
        }

    def connect(self) -> None:
        """Open the MySQL connection if needed."""
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
        """Close the MySQL connection if it is open."""
        if self.connection is not None:
            self.connection.close()
            self.connection = None

    def query(self, sql: str, params: Sequence[Any] | None = None) -> list[dict[str, Any]]:
        """Execute a SELECT-style query and return all rows."""
        if self.connection is None:
            self.connect()

        assert self.connection is not None

        with self.connection.cursor() as cursor:
            if params:
                cursor.execute(sql, tuple(params))
            else:
                cursor.execute(sql)
            return list(cursor.fetchall())

    def query_one(self, sql: str, params: Sequence[Any] | None = None) -> dict[str, Any] | None:
        """Execute a query and return only the first row, if any."""
        rows = self.query(sql, params)
        return rows[0] if rows else None

    def execute(self, sql: str, params: Sequence[Any] | None = None) -> int:
        """Execute a non-SELECT SQL statement and return affected row count."""
        if self.connection is None:
            self.connect()

        assert self.connection is not None

        with self.connection.cursor() as cursor:
            if params:
                affected_rows = cursor.execute(sql, tuple(params))
            else:
                affected_rows = cursor.execute(sql)
            if not self.autocommit:
                self.connection.commit()
            return affected_rows

    def get_recent_submissions(self) -> list[dict[str, Any]]:
        """Return submissions from the last 24 hours using the default query.

        Returns
        -------
        list[dict[str, Any]]
            Rows containing user, client_time, user_submission_id, pool_node,
            run_status, and priority.
        """
        return self.query(DEFAULT_RECENT_SUBMISSIONS_QUERY)

    def update_priorities(self, prioritized_pending_rows: list[dict[str, Any]]) -> int:
        """Write computed priorities back to the `priority` column."""
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
        """Return submission user, id, client_time, and run_status."""
        if days_past is None:
            sql = """
                SELECT user, user_submission_id, client_time, run_status
                FROM submissions
                ORDER BY user_submission_id
            """
            return self.query(sql)

        sql = """
            SELECT user, user_submission_id, client_time, run_status
            FROM submissions
            WHERE client_time IS NOT NULL
              AND TRIM(client_time) != ''
              AND STR_TO_DATE(client_time, %s) IS NOT NULL
              AND STR_TO_DATE(client_time, %s) >= NOW() - INTERVAL %s DAY
            ORDER BY user_submission_id
        """
        return self.query(sql, [client_time_format, client_time_format, days_past])

    def get_submission_times(
        self,
        days_past: int | None = None,
        client_time_format: str = "%Y-%m-%d %H:%i:%s",
    ) -> list[dict[str, Any]]:
        """Return submission user, id, and client_time."""
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
        """Open the connection for context-manager use."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        """Close the connection at the end of a context-manager block."""
        self.close()


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser for ad hoc database queries."""
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
    """Run the command-line database utility and return a shell exit code."""
    parser = build_parser()
    args = parser.parse_args()

    try:
        with Database(args.credentials, autocommit=not args.no_autocommit) as db:
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
