#!/usr/bin/env python3
"""JSON bridge for authenticated portal submission details and deletion requests."""

import json
import logging
import os
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db_io.database import Database
from db_io.submission_deletion import get_submission, request_deletion
from statuses import PROCESSING, TODELETE


def submission_details(row, username):
    """Use live DB metadata and support both plain and legacy prefixed cards."""
    if row is None:
        raise LookupError("Submission was not found.")
    scard = str(row.get("scard") or "")
    parts = scard.split("\t", 3)
    details_text = parts[3] if len(parts) == 4 and parts[1].strip().isdigit() else scard
    details = []
    for line in details_text.splitlines():
        if not line.strip():
            continue
        key, separator, value = line.partition(":")
        details.append({
            "key": key.strip() if separator else "info",
            "value": value.strip() if separator else line.strip(),
        })
    return {
        "requested_id": row["user_submission_id"],
        "user_submission_id": row["user_submission_id"],
        "user": row["user"],
        "status": row["run_status"],
        "osg_id": row["pool_node"],
        "submitted_at": str(row["client_time"] or ""),
        "raw_scard": scard,
        "details": details,
        "can_delete": bool(username) and username == row["user"]
        and row["run_status"] not in {PROCESSING, TODELETE},
    }


def handle_request(request):
    database = request.get("database")
    if database not in {"CLAS12OCR", "CLAS12TEST"}:
        raise ValueError("Invalid database.")
    submission_id = str(request.get("id", ""))
    if not submission_id.isascii() or not submission_id.isdigit() or int(submission_id) <= 0:
        raise ValueError("Invalid submission ID.")
    username = request.get("user")
    if not isinstance(username, str) or not username:
        raise PermissionError("Authentication is required.")
    with Database(database_name=database) as db:
        if request.get("action") == "details":
            return submission_details(get_submission(db, int(submission_id)), username)
        if request.get("action") == "delete":
            return request_deletion(db, int(submission_id), username)
        raise ValueError("Invalid action.")


def main():
    try:
        response = handle_request(json.load(sys.stdin))
    except (PermissionError, LookupError, ValueError, RuntimeError) as exc:
        status = 403 if isinstance(exc, PermissionError) else 404 if isinstance(exc, LookupError) else 409
        response = {"error": str(exc), "http_status": status}
    except Exception:
        logging.exception("Portal submission request failed")
        response = {"error": "Unable to access submissions. Please try again later.", "http_status": 500}
    print(json.dumps(response))


if __name__ == "__main__":
    main()
