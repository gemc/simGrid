#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=nersc-workflow
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=nersc-workflow-%j.out

set -eu

# Global home is available regardless of the submission directory.
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"

# Usage: sbatch nersc-test-workflow.sbatch [gcard] [nevents] [image]
if [[ $# -gt 3 ]]; then
    printf 'Usage: sbatch nersc-test-workflow.sbatch [gcard] [nevents] [image]\n' >&2
    exit 2
fi
# An empty argument lets the nodescript select its default gcard.
gcard="${1:-}"
if [[ -n "$gcard" ]]; then
    gcard="${gcard:A}"
fi
nevents="${2:-100}"
image="${3:-docker.io/jeffersonlab/gemc:dev-almalinux94}"

# Expose project CFS at the same absolute path; the launcher mounts this directory read-only.
export SIMGRID_CONFIG_DIR=/global/cfs/cdirs/m5464
work_dir="$SCRATCH/simgrid/gemc-tests"
mkdir -p "$work_dir"
cd "$work_dir"
run_nersc_container "$image" "$repo_dir/tests/nersc_submission/nodescript.sh" "$gcard" "$nevents"
