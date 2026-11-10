#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=nersc-lund-workflow
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=nersc-lund-workflow-%A_%a.out
#SBATCH --array=1-4

set -eu

# Global home is available regardless of the submission directory.
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"

# One array task runs per row in lund_files: the array index is the row number. The default
# --array above matches the four rows currently in lund_files; override it to match the file's
# line count, for example:
#   sbatch --array=1-$(grep -c . lund_files) nersc-test-lund-workflow.sbatch
# Usage: sbatch nersc-test-lund-workflow.sbatch [gcard] [nevents] [image]
if [[ $# -gt 3 ]]; then
    printf 'Usage: sbatch nersc-test-lund-workflow.sbatch [gcard] [nevents] [image]\n' >&2
    exit 2
fi

# An empty argument lets the nodescript select its default gcard.
gcard="${1:-/global/cfs/cdirs/m5464/clas12-config/main/gemc/dev/rga_fall2018.gcard}"
nevents="${2:-100}"
image="${3:-ghcr.io/gemc/simgrid:test}"
lund_list="$repo_dir/tests/nersc_submission/lund_files"

# The array index is the row position in lund_files: task N fetches the Lund file on line N.
task_id="${SLURM_ARRAY_TASK_ID:-1}"
lund_file=$(sed -n "${task_id}p" "$lund_list")
if [[ -z "$lund_file" ]]; then
    printf 'No Lund file on line %s of %s\n' "$task_id" "$lund_list" >&2
    exit 2
fi
printf 'Array task %s -> %s\n' "$task_id" "$lund_file"

# Expose project CFS at the same absolute path; the launcher mounts this directory read-only.
export SIMGRID_CONFIG_DIR=/global/cfs/cdirs/m5464
work_dir="$SCRATCH/simgrid/gemc-tests"
mkdir -p "$work_dir"
cd "$work_dir"

# Each task renews an osdf://jlab-osdf token with token-renew.zsh; the launcher mounts the
# host .ssh (key + script) at /sshkeys.
run_nersc_container "$image" "$repo_dir/tests/nersc_submission/nodescript-lund.sh"  "$gcard" "$nevents" "$lund_file"
