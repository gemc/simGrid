#!/usr/bin/env python3
"""
select_run.py — run-by-run weighted run picker (runs on the OSG worker node).

Reads the per-run luminosity weights from runs.json and the submitted run list
from run_list.txt, validates that every requested run has a weight, normalizes
the weights of the requested runs to sum to 1, and prints ONE run number chosen
at random in proportion to those weights.

Usage:  select_run.py <runs.json> <run_list.txt>

Only the chosen run number is written to stdout (so the caller can capture it).
Any error — a run absent from runs.json, an empty list, or non-positive
weights — is written to stderr with a non-zero exit so the job fails clearly.
"""

import json
import random
import sys


def load_weights(path):
    """Return a flat {run_number(str): weight(float)} map merged across all groups."""
    with open(path) as f:
        data = json.load(f)
    weights = {}
    for group in data.values():
        if isinstance(group, dict):
            for run_no, weight in group.items():
                weights[str(run_no)] = float(weight)
    return weights


def load_run_list(path):
    """Return the list of run-number strings from a run_list file.

    Accepts one run per line and/or comma- or space-separated values.
    """
    runs = []
    with open(path) as f:
        for line in f:
            for token in line.replace(',', ' ').split():
                if token:
                    runs.append(token)
    return runs


def main(argv):
    if len(argv) != 3:
        sys.stderr.write("usage: select_run.py <runs.json> <run_list.txt>\n")
        return 2

    runs_json, run_list_file = argv[1], argv[2]

    weights_map = load_weights(runs_json)
    runs = load_run_list(run_list_file)

    if not runs:
        sys.stderr.write("select_run: run list {} is empty\n".format(run_list_file))
        return 1

    missing = [r for r in runs if r not in weights_map]
    if missing:
        sys.stderr.write(
            "select_run: run(s) not present in {}: {}\n".format(
                runs_json, ", ".join(missing)
            )
        )
        return 1

    weights = [weights_map[r] for r in runs]
    total = sum(weights)
    if total <= 0:
        sys.stderr.write(
            "select_run: weights must sum to a positive value (got {})\n".format(total)
        )
        return 1

    # Normalize the requested runs' weights to sum to 1, then draw one run.
    normalized = [w / total for w in weights]
    chosen = random.choices(runs, weights=normalized, k=1)[0]
    sys.stdout.write(chosen + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
