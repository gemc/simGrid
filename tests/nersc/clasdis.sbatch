#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=clasdis
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=clasdis/clasdis-%j.out
#SBATCH --error=clasdis/clasdis-%j.err

# Logs are written under clasdis/ (named for this test); create it before submitting:
#   mkdir -p clasdis
set -eu

# Resolve the checkout the job was submitted from; fall back to the installed main checkout.
repo_dir="${SIMGRID_REPO_DIR:-$(cd "${SLURM_SUBMIT_DIR:-$PWD}/../.." 2>/dev/null && pwd)}"
[[ -n "$repo_dir" && -f "$repo_dir/nersc_io/container.sh" ]] || repo_dir="$HOME/software/simgrid/main"
export SIMGRID_FUNCTIONS_FILE="$repo_dir/generators/bash/functions.sh"
source "$repo_dir/nersc_io/container.sh"

# Usage: sbatch clasdis.sbatch [nevents] [image]
if [[ $# -gt 2 ]]; then
    printf 'Usage: sbatch clasdis.sbatch [nevents] [image]\n' >&2
    exit 2
fi

# The node script derives the gcard from CLAS12_CONFIG (CVMFS); gemc is loaded from CVMFS modules.
nevents="${1:-100}"
image="${2:-ghcr.io/gemc/simgrid:test}"

work_dir="$SCRATCH/simgrid/clasdis"
mkdir -p "$work_dir"
cd "$work_dir"

run_nersc_container "$image" "$repo_dir/tests/nersc/nodescript-clasdis.sh" "$nevents"
