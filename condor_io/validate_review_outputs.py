#!/usr/bin/env python3
"""Validate local HIPO results and generate a script to remove their Condor jobs.

Run where the files in the input list are accessible and hipo-utils is available:
    python3 validate_review_outputs.py files-to-review.txt -o remove-verified-jobs.sh

Lists from list_existing_outputs.py contain <cluster.process><TAB><local path>
and may span submissions. Legacy path-only lists require --cluster-id and must
belong to one portal submission. Validation uses the hipo-utils exit code.
The output contains only one condor_rm command per line and is never executed here.
With --remove-failed, local files whose tests return nonzero are deleted.
"""

import argparse
from pathlib import Path
import re
import shutil
import subprocess
import sys


JOB_SUFFIX = re.compile(r"-(\d+)-(\d+)\.hipo$")
CONDOR_JOB = re.compile(r"([1-9]\d*)\.(\d+)")


def read_candidates(list_path, cluster_id=None):
    """Associate each unique path with its job IDs before validating or deleting files."""
    candidates = {}
    submissions = set()
    has_legacy_rows = False
    for number, line in enumerate(list_path.read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        job_text, separator, path_text = line.strip().partition("\t")
        job = None
        if separator:
            match = CONDOR_JOB.fullmatch(job_text)
            if match is None:
                raise ValueError("Line {}: invalid Condor job ID: {}".format(number, job_text))
            job = tuple(map(int, match.groups()))
            if cluster_id is not None and job[0] != cluster_id:
                raise ValueError("Line {}: job ID conflicts with --cluster-id.".format(number))
        else:
            has_legacy_rows = True
            path_text = job_text
            if cluster_id is None:
                raise ValueError(
                    "Path-only lists require --cluster-id; regenerate the list to include job IDs."
                )
        path = Path(path_text.strip()).expanduser()
        match = JOB_SUFFIX.search(path.name)
        if match is None:
            raise ValueError("Line {}: filename must end in -<submission_id>-<jobid>.hipo".format(number))
        submission, process = map(int, match.groups())
        if job is None:
            job = (cluster_id, process)
        elif job[1] != process:
            raise ValueError(
                "Line {}: Condor process number does not match the output filename.".format(number)
            )
        submissions.add(submission)
        candidates.setdefault(path, set()).add(job)
    if has_legacy_rows and len(submissions) > 1:
        raise ValueError(
            "The list contains multiple portal submissions; use a separate list and cluster for each."
        )
    return candidates


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("list_file", type=Path, help="Job ID and local HIPO path per line, separated by a tab.")
    parser.add_argument("--cluster-id", type=int, help="Actual HTCondor cluster ID for legacy path-only lists.")
    parser.add_argument("-o", "--output", type=Path, default=Path("remove-verified-jobs.sh"))
    parser.add_argument(
        "--remove-failed", action="store_true",
        help="Delete local HIPO files whose hipo-utils test returns nonzero.",
    )
    args = parser.parse_args(argv)
    if args.cluster_id is not None and args.cluster_id <= 0:
        parser.error("--cluster-id must be positive")
    output = args.output.expanduser()
    try:
        if output.exists():
            raise ValueError("Output already exists: {}. Choose a new output filename.".format(output))
        candidates = read_candidates(args.list_file.expanduser(), args.cluster_id)
        validator = shutil.which("hipo-utils")
        if validator is None:
            raise ValueError(
                "hipo-utils was not found in PATH; load its environment before running this script."
            )

        good_jobs = set()
        good_files = 0
        removed_files = 0
        removal_errors = 0
        for path, jobs in candidates.items():
            print("Checking: {}".format(path), file=sys.stderr, flush=True)
            if not path.is_file():
                print("Skipping missing or non-regular file: {}".format(path), file=sys.stderr)
                continue
            result = subprocess.run([validator, "-test", str(path)], stdout=sys.stderr, stderr=sys.stderr)
            if result.returncode == 0:
                good_files += 1
                good_jobs.update(jobs)
            else:
                print(
                    "Skipping failed HIPO test (exit {}): {}".format(result.returncode, path), file=sys.stderr,
                )
                if args.remove_failed:
                    try:
                        path.unlink()
                        removed_files += 1
                        print("Removed failed HIPO file: {}".format(path), file=sys.stderr)
                    except OSError as exc:
                        removal_errors += 1
                        print("Could not remove {}: {}".format(path, exc), file=sys.stderr)

        # Exclusive creation protects an existing script or input file from being overwritten.
        with output.open("x", encoding="utf-8") as stream:
            for cluster, process in sorted(good_jobs):
                stream.write("condor_rm {}.{}\n".format(cluster, process))
    except (OSError, ValueError) as exc:
        parser.exit(1, "Error: {}\n".format(exc))

    print(
        "Checked {} unique paths; {} passed; wrote {} job removal commands to {}.".format(
            len(candidates), good_files, len(good_jobs), output,
        ),
        file=sys.stderr,
    )
    print(
        "Removed {} failed HIPO files; {} removal errors. No Condor jobs were removed.".format(
            removed_files, removal_errors,
        ),
        file=sys.stderr,
    )
    return 1 if removal_errors else 0


if __name__ == "__main__":
    sys.exit(main())
