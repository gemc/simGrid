#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=generators
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:10:00
#SBATCH --output=generators/generators-%A_%a.out
#SBATCH --array=1-17

# Logs are written under generators/ (named for this test); create it before submitting:
#   mkdir -p generators
set -eu

# Resolve the checkout the job was submitted from; fall back to the installed main checkout.
repo_dir="${SIMGRID_REPO_DIR:-$(cd "${SLURM_SUBMIT_DIR:-$PWD}/../.." 2>/dev/null && pwd)}"
[[ -n "$repo_dir" && -f "$repo_dir/nersc_io/container.sh" ]] || repo_dir="$HOME/software/simgrid/main"
export SIMGRID_FUNCTIONS_FILE="$repo_dir/generators/bash/functions.sh"
source "$repo_dir/nersc_io/container.sh"

# One array task runs per row in generators_list: the array index is the row number. The default
# --array above matches the rows currently in generators_list; override it to match the file's line
# count, for example:
#   sbatch --array=1-$(grep -c . generators_list) generators.sbatch
# Usage: sbatch generators.sbatch [ntrig] [image]
if [[ $# -gt 2 ]]; then
    printf 'Usage: sbatch generators.sbatch [ntrig] [image]\n' >&2
    exit 2
fi

ntrig="${1:-100}"
image="${2:-ghcr.io/gemc/simgrid:test}"
gen_list="$repo_dir/tests/nersc/generators_list"

# The array index is the row position in generators_list: task N runs the generator on line N.
task_id="${SLURM_ARRAY_TASK_ID:-1}"
generator=$(sed -n "${task_id}p" "$gen_list")
if [[ -z "$generator" ]]; then
    printf 'No generator on line %s of %s\n' "$task_id" "$gen_list" >&2
    exit 2
fi
printf 'Array task %s -> %s\n' "$task_id" "$generator"

work_dir="$SCRATCH/simgrid/generators"
mkdir -p "$work_dir"
cd "$work_dir"

run_nersc_container "$image" "$repo_dir/tests/nersc/nodescript-generators.sh" \
    "$generator" "$ntrig"
