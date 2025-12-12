import argparse

from htcondor_utils import get_owner_batches, format_submitted_time


def print_owner_batches(owner: str) -> None:
    """
    Print a per-batch table (grouped by ClusterId) for the given owner,
    followed by a summary row with totals across all batches.

    The per-batch TOTAL is taken from TotalSubmitProcs (original submitted size),
    while RUN/IDLE/HOLD/OTHER are counted from jobs still present in the queue.
    DONE is derived as:
        DONE = TotalSubmitProcs - RUN - IDLE - HOLD - OTHER
    """
    batches = get_owner_batches(owner)

    header = (
        f"{'OWNER':<6}  {'BATCH_NAME':<10}  {'SUBMITTED':<12}  "
        f"{'DONE':>6}  {'RUN':>6}  {'IDLE':>6}  {'HOLD':>6}  {'TOTAL':>7}  {'JOB_IDS'}"
    )
    print(header)

    if not batches:
        print(f"(no jobs found for owner={owner})")
        return

    # Totals across all batches
    total_done = 0
    total_run = 0
    total_idle = 0
    total_hold = 0
    total_jobs = 0

    # Sort by submit time, then ClusterId
    def sort_key(item):
        cluster_id, b = item
        submitted = b["submitted_epoch"]
        return (submitted if submitted is not None else 2**63 - 1, cluster_id)

    for cluster_id, b in sorted(batches.items(), key=sort_key):
        submitted = format_submitted_time(b["submitted_epoch"])

        minp = b["min_proc"]
        maxp = b["max_proc"]
        if minp is None or maxp is None:
            job_ids = f"{cluster_id}.-"
        elif minp == maxp:
            job_ids = f"{cluster_id}.{minp}"
        else:
            job_ids = f"{cluster_id}.{minp}-{maxp}"

        run = b["counts"]["RUN"]
        idle = b["counts"]["IDLE"]
        hold = b["counts"]["HOLD"]
        other = b["counts"]["OTHER"]

        # Use original submitted total, not "jobs still in queue"
        total = b["total_submit_procs"]
        if total is None:
            # Fallback: if TotalSubmitProcs is missing, we can only report current-in-queue totals
            total = run + idle + hold + other

        # DONE is whatever is not currently RUN/IDLE/HOLD/OTHER in the queue
        done = total - run - idle - hold - other
        if done < 0:
            done = 0  # defensive; should never happen

        # accumulate totals
        total_done += done
        total_run += run
        total_idle += idle
        total_hold += hold
        total_jobs += total

        print(
            f"{owner:<6}  {('ID: ' + str(cluster_id)):<10}  {submitted:<12}  "
            f"{done:>6}  {run:>6}  {idle:>6}  {hold:>6}  {total:>7}  {job_ids}"
        )

    # Print summary row
    print("-" * len(header))
    print(
        f"{owner:<6}  {'TOTAL':<10}  {'-':<12}  "
        f"{total_done:>6}  {total_run:>6}  {total_idle:>6}  "
        f"{total_hold:>6}  {total_jobs:>7}"
    )


def main(argv=None):
    """
    Command-line entrypoint.

    Usage:
      -q / --query prints the per-batch table for the requested owner.
      --owner defaults to 'gemc'.
    """
    parser = argparse.ArgumentParser(description="condor queries")

    parser.add_argument(
        "-q", "--query",
        action="store_true",
        help="Print per-batch (ClusterId) summary for an owner",
    )

    parser.add_argument(
        "--owner",
        type=str,
        default="gemc",
        help="Condor owner to query (default: gemc)",
    )

    args = parser.parse_args(argv)

    if args.query:
        print_owner_batches(args.owner)


if __name__ == "__main__":
    main()
