#!/usr/bin/env python3
"""
osg_submit.py

OSG submission pipeline:
  1. Check condor job capacity (running+idle vs max_submitted_jobs)
  2. Fetch first non-submitted job from DB          (-b to target a specific ID)
  3. Build condor submit file and execution script
  4. Submit to OSG
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from SConfiguration import SConfiguration
from statuses import NOTSUBMITTED, PROCESSING, SUBMITTED, SCRIPTS_GENERATED

DEFAULT_MAX_SUBMITTED_JOBS = 80000
DEFAULT_OWNER = "gemc"


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
	return parser


def main(argv=None):
	# type: (list) -> int
	if argv is None:
		argv = sys.argv[1:]

	args = build_parser().parse_args(argv)

	# Step 1: capacity check — requires htcondor2, only available on the submit node.
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
		print("htcondor2 not available — skipping capacity check.")

	# Step 2: fetch job from DB.
	try:
		from db_io.database import Database, print_job
	except ImportError:
		print("pymysql not available — cannot query database.")
		return 1

	with Database() as db:
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

	# Step 3: build SConfiguration from scard
	scard = SConfiguration.from_string(row['scard'])

	# Step 4: build condor submit file.
	from generators.condor.generate_condor_card import generate_condor_card
	condor_card = generate_condor_card(scard, user_submission_id=row['user_submission_id'],
	                                   target_site=args.target_site)
	if args.print_condor_card:
		print()
		print(condor_card)

	# TODO: step 5 — build bash node execution script (generators/bash/)
	# TODO: step 6 — submit to OSG

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
