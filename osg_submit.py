#!/usr/bin/env python3
"""
osg_submit.py

OSG submission pipeline:
  1. Check condor job capacity (running+idle vs max_submitted_jobs)
  2. Fetch first non-submitted job from DB
  3. Build condor submit file and execution script
  4. Submit to OSG
"""

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

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
	return parser


def main(argv=None):
	# type: (list) -> int
	if argv is None:
		argv = sys.argv[1:]

	args = build_parser().parse_args(argv)

	from condor_io.htcondor_utils import is_under_job_limit
	if not is_under_job_limit(DEFAULT_OWNER, max_jobs=args.max_submitted_jobs):
		print("Job limit reached: '{}' has >= {} running+idle jobs. Skipping submission.".format(
			DEFAULT_OWNER, args.max_submitted_jobs
		))
		return 1

	print("Capacity check passed: under {} jobs for owner '{}'.".format(
		args.max_submitted_jobs, DEFAULT_OWNER
	))

	# TODO: fetch first non-submitted job from DB
	# TODO: build condor submit file and execution script
	# TODO: submit to OSG

	return 0


if __name__ == "__main__":
	raise SystemExit(main())
