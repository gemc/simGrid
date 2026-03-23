import argparse
import sys
from typing import Dict, Any, List, Tuple

from htcondor_utils import get_owner_batches, apply_priority_map

def _priority_from_ratio(run: int, run_avg: float) -> int:
	"""
	Map running jobs relative to the selected-group average into an integer
	priority in [-5, 5].

	Lower-than-average RUN gets positive priority.
	Higher-than-average RUN gets negative priority.
	Exactly average gets 0.

	The magnitude is proportional to run / run_avg.
	"""
	if run_avg <= 0:
		return 0

	value = round(5 * (1.0 - (run / run_avg)))

	if value > 5:
		value = 5
	if value < -5:
		value = -5

	return value


def build_priority_map(owner: str, max_running: int = 5) -> Dict[int, Dict[str, Any]]:
	"""
	Build an internal per-batch map for future priority calculations.

	Each entry contains:
	  - batch_name: current batch identifier
	  - run: number of running jobs
	  - priority: integer in [-5, 5]

	Priority rules:
	  - Only the `max_running` oldest submissions get non-zero/active priority.
	  - Priority is proportional to running jobs relative to the selected-group
	    running average.
	  - Batches below the average get positive priority.
	  - Batches above the average get negative priority.
	  - The goal is to drive the selected oldest batches toward the same number
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

	# Select the oldest submissions only
	selected_batches: List[Tuple[int, Dict[str, Any]]] = sorted(
		priority_map.items(),
		key=lambda item: (
			item[1]["submitted_epoch"] if item[1]["submitted_epoch"] is not None else 2**63 - 1,
			item[0],
		),
	)[:max_running]

	# Compute average RUN across the selected oldest batches, then assign
	# priority proportional to each batch running count relative to that average.
	if selected_batches:
		run_avg = sum(entry["run"] for _, entry in selected_batches) / len(selected_batches)
		for cluster_id, entry in selected_batches:
			priority_map[cluster_id]["priority"] = _priority_from_ratio(entry["run"], run_avg)

	return priority_map


def print_priority_map(owner: str, max_running: int, apply: bool = False) -> None:
	"""
	Print the current internal priority map as a table.

	If apply=True, also write non-zero priorities to HTCondor JobPrio.
	"""
	priority_map = build_priority_map(owner, max_running=max_running)

	if apply and priority_map:
		apply_priority_map(priority_map, skip_zero=True)

	header = (
		f"{'OWNER':<6}  {'BATCH_NAME':<10}  {'RUN':>6}  {'PRIORITY':>8}"
	)
	print(header)

	if not priority_map:
		print(f"(no jobs found for owner={owner})")
		return

	# Show ordered by batch ID
	for _, entry in sorted(priority_map.items(), key=lambda item: item[0]):
		print(
			f"{owner:<6}  {entry['batch_name']:<10}  "
			f"{entry['run']:>6}  {entry['priority']:>8}"
		)


def main(argv=None):
	"""
	Command-line entrypoint.

	Usage:
	  -p / --priority-map prints the internal priority table for an owner.
	  -m / --max-running sets how many oldest submissions get active priority.
	  -a / --apply writes non-zero priorities to HTCondor JobPrio.
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
		help="Number of oldest submissions to assign non-zero priority to (default: 5)",
	)

	parser.add_argument(
		"--owner",
		type=str,
		default="gemc",
		help="Condor owner to query (default: gemc)",
	)

	parser.add_argument(
		"-a", "--apply",
		action="store_true",
		help="Apply non-zero priorities to HTCondor JobPrio",
	)

	# Print help when run with no arguments
	if not argv:
		parser.print_help()
		return 0

	args = parser.parse_args(argv)

	if args.max_running < 1:
		parser.error("--max-running must be >= 1")

	if args.priority_map:
		print_priority_map(args.owner, args.max_running, apply=args.apply)

	return 0


if __name__ == "__main__":
	raise SystemExit(main())