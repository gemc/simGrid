#!/bin/bash
#SBATCH --account=m5464
#SBATCH --job-name=full-c
#SBATCH --constraint=cpu
#SBATCH --qos=regular
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=256
#SBATCH --time=02:00:00
#SBATCH --output=full-c/full-c-%j.out
#SBATCH --error=full-c/full-c-%j.err
#SBATCH --signal=B:TERM@120

# C: TaskFarmer executes 100 Lund + 100 clasdis tasks in one shared container per worker node.
# Before submission: module load taskfarmer; mkdir -p full-c
set -euo pipefail
repo_dir="${SIMGRID_REPO_DIR:-$(cd "${SLURM_SUBMIT_DIR:-$PWD}/../.." && pwd)}"
exec bash "$repo_dir/tests/nersc/full-taskfarmer.sh" C "${1:-ghcr.io/gemc/simgrid:test}"
