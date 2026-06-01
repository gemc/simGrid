#!/usr/bin/env python3
"""
osg_submit.py

OSG submission pipeline:
  1. Check condor job capacity (running+idle vs max_submitted_jobs)
  2. Fetch first non-submitted job from DB          (-b to target a specific ID)
  3. Parse scard; mark job as Processing in DB
  4. Create staging directory ~/osgOutput/<username>/job_<id>/
  5. For type-2: validate lund location and write lund_files via pelican object ls
  6. Generate and stage clas12.condor, nodescript.sh, functions.sh, bg_merge_bk_file.sh
  7. Submit to OSG
"""

import argparse
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from SConfiguration import SConfiguration
from statuses import NOTSUBMITTED, PROCESSING, SUBMITTED, SCRIPTS_GENERATED

DEFAULT_MAX_SUBMITTED_JOBS = 80000
DEFAULT_OWNER = "gemc"

_REPO_ROOT   = os.path.dirname(os.path.abspath(__file__))
_OUTPUT_ROOT = os.path.join(os.path.expanduser("~"), "osgOutput")


def _job_dir(username, user_submission_id):
    """Return the staging directory path for one submission."""
    return os.path.join(_OUTPUT_ROOT, username, "job_{}".format(user_submission_id))


def _print_test_warning(lines):
    border = "=" * 64
    print(border)
    for line in lines:
        print("  {}".format(line))
    print(border)


def build_parser():
    # type: () -> argparse.ArgumentParser
    parser = argparse.ArgumentParser(
        description="Submit the next pending OSG job from the database."
    )
    parser.add_argument(
        "--max-submitted-jobs",
        type=int,
        default=DEFAULT_MAX_SUBMITTED_JOBS,
        help="Maximum running+idle jobs allowed before submission is blocked (default: {}).".format(
            DEFAULT_MAX_SUBMITTED_JOBS
        ),
    )
    parser.add_argument(
        "-b", "--user-submission-id",
        type=int,
        default=None,
        metavar="ID",
        help="Process a specific UserSubmissionID instead of the next pending job.",
    )
    parser.add_argument(
        "--test",
        action="store_true",
        default=False,
        help="Test mode: skip htcondor2 capacity check and use a pelican mockup "
             "for type-2 lund files. Without this flag, missing dependencies fail.",
    )
    parser.add_argument(
        "--target-site",
        default=None,
        metavar="SITE",
        help="Pin all jobs to a single GLIDEIN_Site (e.g. CNAF). "
             "Adds (GLIDEIN_Site == \"SITE\") to Requirements.",
    )
    parser.add_argument(
        "--print-condor-card",
        action="store_true",
        default=False,
        help="Print the generated HTCondor submit file to stdout.",
    )
    parser.add_argument(
        "--print-nodescript",
        action="store_true",
        default=False,
        help="Print the generated nodescript.sh to stdout.",
    )
    parser.add_argument(
        "--devel",
        action="store_true",
        default=False,
        help="Use the CLAS12TEST database and the devel singularity image instead of production.",
    )
    return parser


def main(argv=None):
    # type: (list) -> int
    if argv is None:
        argv = sys.argv[1:]

    args = build_parser().parse_args(argv)

    print("\nStep 1: Capacity check")
    # requires htcondor2, only available on the submit node.
    try:
        from condor_io.htcondor_utils import is_under_job_limit
        if not is_under_job_limit(DEFAULT_OWNER, max_jobs=args.max_submitted_jobs):
            print("Job limit reached: '{}' has >= {} running+idle jobs. Skipping.".format(
                DEFAULT_OWNER, args.max_submitted_jobs
            ))
            return 1
        print("Capacity check passed: under {} jobs for owner '{}'.".format(
            args.max_submitted_jobs, DEFAULT_OWNER
        ))
    except ImportError:
        if not args.test:
            print("htcondor2 not available. Use --test to skip the capacity check.")
            return 1
        _print_test_warning([
            "TEST MODE: htcondor2 not found.",
            "Skipping job capacity check.",
        ])

    print("\nStep 2: Fetch job from the database")
    try:
        from db_io.database import Database, print_job, current_timestamp
    except ImportError:
        print("pymysql not available — cannot query database.")
        return 1

    db_name = "CLAS12TEST" if args.devel else "CLAS12OCR"
    with Database(database_name=db_name) as db:
        row = db.return_unsubmitted_job(args.user_submission_id)

    if row is None:
        if args.user_submission_id is not None:
            print("No submission found with ID {}.".format(args.user_submission_id))
        else:
            print("No unsubmitted jobs found in the database.")
        return 0

    label = "Targeting specific submission:" if args.user_submission_id else "Next unsubmitted job:"
    print()
    print(label)
    print_job(row)

    print("\nStep 3: Parse submission card")
    # build SConfiguration from scard; backfill username from the DB row.
    scard = SConfiguration.from_string(row['scard'])
    scard.username = row['user']

    print("\nStep 3a: Mark job as Processing")
    # mark the job as Processing so it is not picked up by a concurrent run.
    if not args.test:
        with Database(database_name=db_name) as db:
            db.execute(
                "UPDATE submissions SET run_status = %s WHERE user_submission_id = %s",
                [PROCESSING, row['user_submission_id']],
            )
        print("Status → '{}'.".format(PROCESSING))
    else:
        print("TEST MODE: skipping status update to '{}'.".format(PROCESSING))

    print("\nStep 3b: Create staging directory")
    # create staging directory ~/osgOutput/<username>/job_<id>/
    username          = scard.username or "unknown"
    user_submission_id = row['user_submission_id']
    job_dir           = _job_dir(username, user_submission_id)
    os.makedirs(os.path.join(job_dir, "log"), exist_ok=True)
    print("Staging directory: {}".format(job_dir))

    print("\nStep 4: Stage lund files" if scard.type == '2' else "\nStep 4: Stage lund files — skipped (type-1 submission)")
    # for type-2 (lund) submissions, validate the lund location and write lund_files.
    if scard.type == '2':
        lund_location = scard.generator or ""
        if not lund_location.startswith('/volatile/clas12/'):
            print("Error: lund location must start with /volatile/clas12/ — got: {!r}".format(
                lund_location
            ))
            return 1
        from generators.lund_helper import write_lund_files, LUND_FILES
        lund_count = write_lund_files(
            lund_location,
            output_file=os.path.join(job_dir, LUND_FILES),
            test=args.test,
        )
        if lund_count == 0:
            print("Error: no lund files found at {!r}.".format(lund_location))
            return 1

    print("\nStep 5: Generate HTCondor submit file")
    from generators.condor.generate_condor_card import generate_condor_card
    condor_card = generate_condor_card(scard, user_submission_id=user_submission_id,
                                       target_site=args.target_site, devel=args.devel)
    if args.print_condor_card:
        print()
        print(condor_card)

    condor_path = os.path.join(job_dir, "clas12.condor")
    with open(condor_path, 'w') as f:
        f.write(condor_card)
    print("Wrote: {}".format(condor_path))

    print("\nStep 6: Generate nodescript.sh and stage scripts")
    from generators.bash.generate_nodescript import generate_nodescript
    nodescript_path = generate_nodescript(
        scard,
        user_submission_id=user_submission_id,
        test=args.test,
        output_file=os.path.join(job_dir, "nodescript.sh"),
    )
    if args.print_nodescript:
        with open(nodescript_path) as f:
            print()
            print(f.read())

    # Stage functions.sh alongside nodescript.sh (referenced as functions.sh in transfer_input_files).
    shutil.copy2(
        os.path.join(_REPO_ROOT, "generators", "bash", "functions.sh"),
        os.path.join(job_dir, "functions.sh"),
    )

    # Stage bg_merge_bk_file.sh — always copied; condor card includes it in
    # transfer_input_files only when bkmerging is requested.
    shutil.copy2(
        os.path.join(_REPO_ROOT, "bg_merge_bk_file.sh"),
        os.path.join(job_dir, "bg_merge_bk_file.sh"),
    )
    print("Staged scripts to {}.".format(job_dir))

    # Step 6a: save generated scripts to the DB for later inspection.
    if not args.test:
        with open(nodescript_path) as f:
            nodescript_text = f.read()
        with Database(database_name=db_name) as db:
            db.execute(
                "UPDATE submissions SET runscript_text = %s, clas12_condor_text = %s"
                " WHERE user_submission_id = %s",
                [nodescript_text, condor_card, user_submission_id],
            )
        print("Saved runscript_text and clas12_condor_text to DB.")
    else:
        print("TEST MODE: skipping DB script storage.")

    print("\nStep 7: Submit to HTCondor")
    if args.test:
        print("TEST MODE: skipping condor_submit.")
        return 0

    import subprocess
    import re
    result = subprocess.run(
        ["condor_submit", "clas12.condor"],
        cwd=job_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        universal_newlines=True,
    )
    if result.returncode != 0:
        error_path = os.path.join(job_dir, "htcondor_submission_error.txt")
        with open(error_path, 'w') as f:
            f.write(result.stdout)
        print("condor_submit failed (exit {}). Error written to {}.".format(
            result.returncode, error_path
        ))
        return 1

    print(result.stdout)

    cluster_id = None
    m = re.search(r"submitted to cluster\s+(\d+)", result.stdout, re.IGNORECASE)
    if m:
        cluster_id = int(m.group(1))
        print("HTCondor cluster ID: {}".format(cluster_id))
    else:
        print("Warning: could not parse cluster ID from condor_submit output.")

    with Database(database_name=db_name) as db:
        db.execute(
            "UPDATE submissions SET run_status = %s, server_time = %s, pool_node = %s"
            " WHERE user_submission_id = %s",
            [SUBMITTED, current_timestamp(), cluster_id, user_submission_id],
        )
    print("Status → '{}', server_time and pool_node recorded.".format(SUBMITTED))

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
