#!/bin/bash
# Submit the Lund workflow as a Slurm job array sized to the current lund_files line count,
# one array task per row. This is the NERSC analog of the OSG "queue lundFile from lund_files"
# fan-out: #SBATCH --array cannot size itself, so compute it here and pass it on the command line.
# Usage: ./submit-lund-workflow.sh [gcard] [nevents] [image]
set -euo pipefail

repo_dir="${SIMGRID_REPO_DIR:-$HOME/software/simgrid/main}"
sbatch_file="$repo_dir/tests/nersc/nersc-test-lund-workflow.sbatch"
lund_list="$repo_dir/tests/nersc/lund_files"

n=$(grep -c . "$lund_list")
if [[ "$n" -lt 1 ]]; then
    printf 'No Lund files listed in %s\n' "$lund_list" >&2
    exit 2
fi

echo "Submitting $n array tasks (one per row) from $lund_list"
exec sbatch --array=1-"$n" "$sbatch_file" "$@"
