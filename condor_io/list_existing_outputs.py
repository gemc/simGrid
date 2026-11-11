#!/usr/bin/env python3
"""List Condor job IDs and JLab paths from Pelican 'already exists' failures.

Usage from a submission directory:
    python3 /path/to/simGrid/condor_io/list_existing_outputs.py ~/osgOutput > files-to-review.txt

Accepts log files or directories (searched recursively for *.out). Queries the
live Condor queue for owner gemc and reads logs only for ongoing jobs, including
held jobs. Completed and removed jobs are excluded. Output rows are
<cluster.process><TAB><JLab path>; job IDs come from job.<cluster>.<process>.out
filenames. These are review candidates, not confirmed corrupt files. No files
are deleted, and no jobs, database records, or remote storage are changed.
"""

import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
from urllib.parse import unquote, urlsplit


OUTPUT_URI = re.compile(r"osdf://[^\s\"'<>]+\.hipo")
JOB_LOG = re.compile(r"job\.([1-9]\d*)\.(\d+)\.out$")
OUTPUT_JOB = re.compile(r"-\d+-(\d+)\.hipo$")
REMOTE_PREFIX = "/jlab-osdf/clas12/volatile/osg/"
LOCAL_PREFIX = "/volatile/clas12/osg/"
ONGOING_STATUSES = {1, 2, 5, 6, 7}  # idle, running, held, transferring, suspended


def ongoing_job_ids(owner):
    """Query live jobs once; queue failures must not fall back to historical logs."""
    try:
        result = subprocess.run(
            ["condor_q", owner, "-json", "-attributes", "ClusterId,ProcId,JobStatus"],
            check=True, capture_output=True, text=True,
        )
    except subprocess.CalledProcessError as exc:
        raise ValueError("condor_q failed: {}".format((exc.stderr or str(exc)).strip())) from exc
    ads = json.loads(result.stdout)
    if not isinstance(ads, list):
        raise ValueError("condor_q did not return a JSON list of jobs")
    jobs = set()
    for ad in ads:
        if not isinstance(ad, dict) or any(
            not isinstance(ad.get(field), int) for field in ("ClusterId", "ProcId", "JobStatus")
        ):
            raise ValueError("condor_q returned a job without numeric ClusterId, ProcId, and JobStatus")
        if ad["ClusterId"] <= 0 or ad["ProcId"] < 0:
            raise ValueError("condor_q returned an invalid job ID")
        if ad["JobStatus"] in ONGOING_STATUSES:
            jobs.add("{}.{}".format(ad["ClusterId"], ad["ProcId"]))
    return jobs


def jlab_path(uri):
    """Map either OSDF URL form to a path in the JLab OSG output tree."""
    parsed = urlsplit(uri)
    if parsed.netloc not in ("", "jlab-osdf"):
        return None
    remote = unquote(parsed.path)
    if parsed.netloc == "jlab-osdf":
        remote = "/jlab-osdf" + remote
    if not remote.startswith(REMOTE_PREFIX):
        return None
    relative = remote[len(REMOTE_PREFIX):]
    if any(part in ("", ".", "..") for part in relative.split("/")):
        return None
    if any(ord(char) < 32 or ord(char) == 127 for char in relative):
        return None
    return LOCAL_PREFIX + relative


def collect_candidates(log_files):
    """Return unique (Condor job ID, path) pairs from collision messages."""
    candidates = set()
    for log_file in log_files:
        job = JOB_LOG.fullmatch(log_file.name)
        with log_file.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if "remote object already exists" not in line:
                    continue
                for match in OUTPUT_URI.finditer(line):
                    candidate = jlab_path(match.group())
                    if candidate is not None:
                        process = OUTPUT_JOB.search(Path(candidate).name)
                        if job is None or process is None or int(process[1]) != int(job[2]):
                            print("Skipping unverified job/file association in {}: {}".format(
                                log_file, candidate,
                            ), file=sys.stderr)
                            continue
                        job_id = "{}.{}".format(int(job[1]), int(job[2]))
                        candidates.add((job_id, candidate))
    return sorted(candidates)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="Log files or directories containing *.out logs.")
    parser.add_argument("--owner", default="gemc", help="Condor owner to query (default: %(default)s).")
    args = parser.parse_args(argv)
    log_files = set()
    try:
        for path in args.paths:
            path = path.expanduser()
            if path.is_dir():
                log_files.update(path.rglob("*.out"))
            elif path.is_file():
                log_files.add(path)
            else:
                raise FileNotFoundError("Log path does not exist: {}".format(path))
        ongoing = ongoing_job_ids(args.owner)
        selected_logs = []
        for log_file in sorted(log_files):
            job = JOB_LOG.fullmatch(log_file.name)
            if job is not None and "{}.{}".format(int(job[1]), int(job[2])) in ongoing:
                selected_logs.append(log_file)
        candidates = collect_candidates(selected_logs)
    except (OSError, ValueError) as exc:
        parser.exit(1, "Error: {}\n".format(exc))

    for job_id, candidate in candidates:
        print("{}\t{}".format(job_id, candidate))
    print(
        "Scanned {} ongoing job logs; {} unique review candidates. Existing files may be valid.".format(
            len(selected_logs), len(candidates),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
