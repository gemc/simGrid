#!/bin/bash
# Submit the Lund workflow as a Slurm job array sized to the current lund_files line count,
# one array task per row. This is the NERSC analog of the OSG "queue lundFile from lund_files"
# fan-out: #SBATCH --array cannot size itself, so compute it here and pass it on the command line.
# Usage: ./submit-lund.sh [nevents] [image]
set -euo pipefail

repo_dir="${SIMGRID_REPO_DIR:-$(cd "$(dirname "$0")/.." && pwd)}"
sbatch_file="$repo_dir/tests/nersc/lund.sbatch"
lund_list="$repo_dir/tests/nersc/lund_files"

n=$(grep -c . "$lund_list")
if [[ "$n" -lt 1 ]]; then
    printf 'No Lund files listed in %s\n' "$lund_list" >&2
    exit 2
fi

echo "Submitting $n array tasks (one per row) from $lund_list"
# Pass the resolved checkout to the sbatch so it does not re-derive from $SLURM_SUBMIT_DIR.
export SIMGRID_REPO_DIR="$repo_dir"
exec sbatch --array=1-"$n" "$sbatch_file" "$@"
