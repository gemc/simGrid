import argparse
import sys
from typing import Dict, Any, List, Tuple

from htcondor_utils import get_owner_batches


def _priority_from_rank(rank: int, total: int) -> int:
	"""
	Map a rank in [0, total-1] to an integer priority in [-10, 10], excluding 0.

	Lower rank means fewer running jobs, so lower rank gets higher priority.
	Highest priority is +10, lowest is -10.

	Examples:
	  total=1 -> [10]
	  total=2 -> [10, -10]
	  total=3 -> [10, 1, -10]
	  total=5 -> [10, 5, 1, -5, -10]
	"""
	if total <= 0:
		return 0
	if total == 1:
		return 10

	# rank=0 => +10, rank=total-1 => -10
	value = 10 - round((20 * rank) / (total - 1))

	# Avoid 0 for selected batches so they all get an active signal
	if value == 0:
		value = 1 if rank < total / 2 else -1

	# Clamp defensively
	if value > 10:
		value = 10
	if value < -10:
		value = -10

	return value


def build_priority_map(owner: str, max_running: int = 5) -> Dict[int, Dict[str, Any]]:
	"""
	Build an internal per-batch map for future priority calculations.

	Each entry contains:
	  - batch_name: current batch identifier
	  - hours_in_queue: hours from submitted time until now
	  - run: number of running jobs
	  - priority: integer in [-10, 10]

	Priority rules:
	  - Only the `max_running` most recent submissions get non-zero priority.
	  - Within those recent submissions, batches with fewer running jobs get
	    higher priority, and batches with more running jobs get lower priority.
	  - The goal is to drive the selected recent batches toward the same number
	    of running jobs.
	"""
	batches = get_owner_batches(owner)

	priority_map: Dict[int, Dict[str, Any]] = {}

	for cluster_id, b in batches.items():
		run = b["counts"]["RUN"]
		submitted_epoch = b.get("submitted_epoch")

		priority_map[cluster_id] = {
			"batch_name": f"ID: {cluster_id}",
			"submitted_epoch": submitted_epoch,
			"run": run,
			"priority": 0,
		}

	# Select the most recent submissions only
	recent_batches: List[Tuple[int, Dict[str, Any]]] = sorted(
		priority_map.items(),
		key=lambda item: (
			item[1]["submitted_epoch"] if item[1]["submitted_epoch"] is not None else -1,
			item[0],
		),
		reverse=True,
	)[:max_running]

	# Among selected batches, rank by running jobs:
	# fewer RUN jobs => higher priority
	ranked_recent = sorted(
		recent_batches,
		key=lambda item: (
			item[1]["run"],                                  # fewer running jobs first
			-(item[1]["submitted_epoch"] or -1),            # newer first among ties
			item[0],                                        # stable tie-break
		),
	)

	total_ranked = len(ranked_recent)
	for rank, (cluster_id, entry) in enumerate(ranked_recent):
		priority_map[cluster_id]["priority"] = _priority_from_rank(rank, total_ranked)

	return priority_map


def print_priority_map(owner: str, max_running: int) -> None:
	"""
	Print the current internal priority map as a table.
	"""
	priority_map = build_priority_map(owner, max_running=max_running)

	header = (
		f"{'OWNER':<6}  {'BATCH_NAME':<10}  {'RUN':>6}  {'PRIORITY':>8}"
	)
	print(header)

	if not priority_map:
		print(f"(no jobs found for owner={owner})")
		return

	# Show most recent submissions first
	def sort_key(item):
		cluster_id, entry = item
		submitted_epoch = entry["submitted_epoch"]
		return (
			-(submitted_epoch if submitted_epoch is not None else -1),
			cluster_id,
		)

	for _, entry in sorted(priority_map.items(), key=sort_key):
		print(
			f"{owner:<6}  {entry['batch_name']:<10}  "
			f"{entry['run']:>6}  {entry['priority']:>8}"
		)


def main(argv=None):
	"""
	Command-line entrypoint.

	Usage:
	  -p / --priority-map prints the internal priority table for an owner.
	  -m / --max-running sets how many most-recent submissions get non-zero priority.
	  --owner defaults to 'gemc'.
	"""
	if argv is None:
		argv = sys.argv[1:]

	parser = argparse.ArgumentParser(description="condor priority map")

	parser.add_argument(
		"-p", "--priority-map",
		action="store_true",
		help="Print internal per-batch priority table for an owner",
	)

	parser.add_argument(
		"-m", "--max-running",
		type=int,
		default=5,
		help="Number of most-recent submissions to assign non-zero priority to (default: 5)",
	)

	parser.add_argument(
		"--owner",
		type=str,
		default="gemc",
		help="Condor owner to query (default: gemc)",
	)

	# Print help when run with no arguments
	if not argv:
		parser.print_help()
		return 0

	args = parser.parse_args(argv)

	if args.max_running < 1:
		parser.error("--max-running must be >= 1")

	if args.priority_map:
		print_priority_map(args.owner, args.max_running)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())