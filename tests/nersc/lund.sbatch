#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=lund
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=lund/lund-%A_%a.out
#SBATCH --array=1-4

# Logs are written under lund/ (named for this test); create it before submitting:
#   mkdir -p lund
set -eu

# Resolve the checkout the job was submitted from; fall back to the installed main checkout.
repo_dir="${SIMGRID_REPO_DIR:-$(cd "${SLURM_SUBMIT_DIR:-$PWD}/../.." 2>/dev/null && pwd)}"
[[ -n "$repo_dir" && -f "$repo_dir/nersc_io/container.sh" ]] || repo_dir="$HOME/software/simgrid/main"
export SIMGRID_FUNCTIONS_FILE="$repo_dir/generators/bash/functions.sh"
source "$repo_dir/nersc_io/container.sh"

# One array task runs per row in lund_files: the array index is the row number. The default
# --array above matches the four rows currently in lund_files; override it to match the file's
# line count, for example:
#   sbatch --array=1-$(grep -c . lund_files) lund.sbatch
# Usage: sbatch lund.sbatch [nevents] [image]
if [[ $# -gt 2 ]]; then
    printf 'Usage: sbatch lund.sbatch [nevents] [image]\n' >&2
    exit 2
fi

# The node script derives the gcard from CLAS12_CONFIG (CVMFS); gemc is loaded from CVMFS modules.
nevents="${1:-100}"
image="${2:-ghcr.io/gemc/simgrid:test}"
lund_list="$repo_dir/tests/nersc/lund_files"

# The array index is the row position in lund_files: task N fetches the Lund file on line N.
task_id="${SLURM_ARRAY_TASK_ID:-1}"
lund_file=$(sed -n "${task_id}p" "$lund_list")
if [[ -z "$lund_file" ]]; then
    printf 'No Lund file on line %s of %s\n' "$task_id" "$lund_list" >&2
    exit 2
fi
printf 'Array task %s -> %s\n' "$task_id" "$lund_file"

work_dir="$SCRATCH/simgrid/lund"
mkdir -p "$work_dir"
cd "$work_dir"

# Each task renews an osdf://jlab-osdf token with token-renew.zsh; the launcher mounts the
# host .ssh (key + script) at /sshkeys.
run_nersc_container "$image" "$repo_dir/tests/nersc/nodescript-lund.sh" "$nevents" "$lund_file"
