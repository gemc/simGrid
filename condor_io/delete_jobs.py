#!/usr/bin/env python3
"""Remove TODELETE clusters on the submit node, then delete their MySQL rows."""

import argparse
import os
import subprocess
import sys

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from db_io.database import Database, DEFAULT_CREDENTIALS_FILE
from db_io.submission_deletion import cluster_id
from statuses import TODELETE


def remove_cluster(cluster):
    """Treat an empty queue as success; query/removal errors preserve the DB row."""
    cluster = str(cluster_id(cluster))
    result = subprocess.run(
        ["condor_q", cluster, "-autoformat:t", "ClusterId", "Owner", "JobStatus"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30,
    )
    statuses = []
    for line in result.stdout.splitlines():
        if not line.strip():
            continue
        fields = line.split()
        if (
            len(fields) != 3 or fields[0] != cluster
            or fields[2] not in {"0", "1", "2", "3", "4", "5", "6", "7"}
        ):
            raise RuntimeError("Unexpected condor_q output: {!r}; stderr: {!r}".format(
                line, result.stderr.strip(),
            ))
        if fields[1] != "gemc":
            raise RuntimeError("Cluster does not match the portal's Condor owner gemc.")
        statuses.append(int(fields[2]))
    if not statuses and result.stderr.strip():
        raise RuntimeError("Empty condor_q response with diagnostics: {}".format(result.stderr.strip()))
    if any(status not in (3, 4) for status in statuses):
        subprocess.run(
            ["condor_rm", cluster], check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
            universal_newlines=True, timeout=30,
        )


def process_deletions(db, apply=False):
    """Only the cron worker removes submitted rows; failed rows are retried next time."""
    rows = db.query(
        "SELECT user_submission_id, user, pool_node FROM submissions WHERE run_status = %s",
        [TODELETE],
    )
    failed = False
    for row in rows:
        submission_id = row["user_submission_id"]
        try:
            cluster = cluster_id(row["pool_node"])
            print("Delete submission {} (user={}, cluster={}){}".format(
                submission_id, row["user"], cluster, "" if apply else " [dry run]",
            ))
            if not apply:
                continue
            remove_cluster(cluster)
            deleted = db.execute(
                "DELETE FROM submissions WHERE user_submission_id = %s AND run_status = %s "
                "AND pool_node = %s",
                [submission_id, TODELETE, row["pool_node"]],
            )
            if deleted != 1:
                raise RuntimeError("Submission changed or was already deleted.")
        except Exception as exc:
            failed = True
            print("Submission {} retained for retry: {}".format(submission_id, exc), file=sys.stderr)
            for stream in ("stdout", "stderr"):
                output = getattr(exc, stream, None)
                if output:
                    print("{}: {}".format(stream, output.strip()), file=sys.stderr)
    return 1 if failed else 0


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--database", choices=["CLAS12OCR", "CLAS12TEST"], default="CLAS12OCR")
    parser.add_argument("-c", "--credentials", default=str(DEFAULT_CREDENTIALS_FILE))
    parser.add_argument(
        "--apply", action="store_true", help="Run condor_rm and delete rows; default is dry run."
    )
    args = parser.parse_args(argv)
    try:
        with Database(credentials_file=args.credentials, database_name=args.database) as db:
            return process_deletions(db, args.apply)
    except Exception as exc:
        print("Deletion worker failed: {}".format(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
