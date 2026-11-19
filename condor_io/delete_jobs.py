#!/usr/bin/env python3
"""Remove TODELETE clusters on the submit node, then delete their MySQL rows."""

import argparse
import json
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
        ["condor_q", cluster, "-json", "-attributes", "Owner,JobStatus"],
        check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, universal_newlines=True, timeout=30,
    )
    ads = json.loads(result.stdout)
    if not isinstance(ads, list):
        raise RuntimeError("Unexpected condor_q response.")
    if any(ad.get("Owner") != "gemc" or ad.get("JobStatus") is None for ad in ads):
        raise RuntimeError("Cluster does not match the portal's Condor owner gemc.")
    if any(ad["JobStatus"] not in (3, 4) for ad in ads):
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
            if getattr(exc, "stderr", None):
                print(exc.stderr.strip(), file=sys.stderr)
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
