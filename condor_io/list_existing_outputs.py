#!/usr/bin/env python3
"""List JLab output paths mentioned in Pelican 'already exists' failures.

Usage from a submission directory:
    ~/venv/pymysql/bin/python3 /path/to/simGrid/condor_io/list_existing_outputs.py log > files-to-review.txt

Accepts log files or directories (searched recursively for *.out). Reads local
logs only. These are review candidates, not confirmed corrupt files. No files
are deleted, and no jobs, database records, or remote storage are changed.
"""

import argparse
from pathlib import Path
import re
import sys
from urllib.parse import unquote, urlsplit


OUTPUT_URI = re.compile(r"osdf://[^\s\"'<>]+\.hipo")
REMOTE_PREFIX = "/jlab-osdf/clas12/volatile/osg/"
LOCAL_PREFIX = "/volatile/clas12/osg/"


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
    """Return unique paths from collision messages; do not infer corruption."""
    candidates = set()
    for log_file in log_files:
        with log_file.open(encoding="utf-8", errors="replace") as stream:
            for line in stream:
                if "remote object already exists" not in line:
                    continue
                for match in OUTPUT_URI.finditer(line):
                    candidate = jlab_path(match.group())
                    if candidate is not None:
                        candidates.add(candidate)
    return sorted(candidates)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("paths", nargs="+", type=Path, help="Log files or directories containing *.out logs.")
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
        candidates = collect_candidates(sorted(log_files))
    except (OSError, ValueError) as exc:
        parser.exit(1, "Error: {}\n".format(exc))

    for candidate in candidates:
        print(candidate)
    print(
        "Scanned {} logs; {} unique review candidates. Existing files may be valid.".format(
            len(log_files), len(candidates),
        ),
        file=sys.stderr,
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
