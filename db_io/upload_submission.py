#!/usr/bin/env python3
"""
upload_submission.py

Upload a gcard text file into the MySQL submissions database.

Purpose:
1. upload submission parameters to the database, including time
2. set the submission status to 'Not Submitted'
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path
from typing import Optional

from database import Database, current_timestamp, debug


DEFAULT_POOL = "all_osg"
DEFAULT_RUN_STATUS = "Not Submitted"


def build_parser() -> argparse.ArgumentParser:
    """Build the CLI parser."""
    parser = argparse.ArgumentParser(
        prog="upload_submission.py",
        description="Upload a gcard text file to the MySQL submissions table.",
    )
    parser.add_argument("-f", "--file", dest="gcard_file", help="Path to the gcard text file.")
    parser.add_argument("-u", "--user", dest="username", help="Submission username.")
    parser.add_argument("-c", "--credentials", required=True, help="Path to the MySQL credentials file.")
    parser.add_argument("--pool", default=DEFAULT_POOL, help=f"Pool name stored in pool_node (default: {DEFAULT_POOL}).")
    parser.add_argument("-d", "--debug", action="store_true", help="Print debug messages.")
    parser.add_argument("--database", help="Override the database name from the MySQL credentials file.")
    return parser



def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments and print help when no flags are given."""
    parser = build_parser()

    if argv is None:
        argv = sys.argv[1:]

    if not argv:
        parser.print_help(sys.stdout)
        raise SystemExit(0)

    args = parser.parse_args(argv)

    if not args.gcard_file:
        parser.error("the following argument is required: -f/--file")
    if not args.username:
        parser.error("the following argument is required: -u/--user")

    return args



def read_gcard_file(path_str: str) -> str:
    """Read the full gcard file and reject missing or empty input."""
    path = Path(path_str)
    if not path.is_file():
        raise FileNotFoundError(f"Gcard file not found: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise ValueError(f"Gcard file is empty: {path}")

    return text



def extract_key_value(text: str, candidate_keys: list[str]) -> Optional[str]:
    """Extract the first matching key from simple key=value or key: value lines."""
    normalized = {key.lower() for key in candidate_keys}

    for raw_line in text.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue

        separator = "=" if "=" in line else ":" if ":" in line else None
        if separator is None:
            continue

        left, right = line.split(separator, 1)
        if left.strip().lower() in normalized:
            value = right.strip()
            return value or None

    return None



def extract_client_ip(gcard_text: str) -> Optional[str]:
    """Extract client IP metadata from the gcard when present."""
    return extract_key_value(gcard_text, ["client_ip", "ip", "client ip"])



def upload_submission(args: argparse.Namespace) -> int:
    """Perform the upload workflow and return the new submission id."""
    gcard_text = read_gcard_file(args.gcard_file)
    client_ip = extract_client_ip(gcard_text)
    client_time = current_timestamp()

    debug(args.debug, f"Reading gcard from {args.gcard_file}")
    debug(args.debug, f"Using user '{args.username}'")
    debug(args.debug, f"Using pool '{args.pool}'")
    debug(args.debug, f"Using client_time '{client_time}'")


    with Database(args.credentials, database_name=args.database) as db:
        user_id = db.ensure_user(args.username, debug_enabled=args.debug)
        submission_id = db.insert_submission(
            username=args.username,
            user_id=user_id,
            client_time=client_time,
            pool_node=args.pool,
            scard=gcard_text,
            run_status=DEFAULT_RUN_STATUS,
            client_ip=client_ip,
            debug_enabled=args.debug,
        )

    return submission_id



def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    try:
        args = parse_args(argv)
        submission_id = upload_submission(args)
        print(submission_id)
        return 0
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
