#!/bin/bash
#SBATCH --account=m5464
#SBATCH --job-name=full-b
#SBATCH --constraint=cpu
#SBATCH --qos=regular
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=1
#SBATCH --cpus-per-task=256
#SBATCH --time=02:00:00
#SBATCH --output=full-b/full-b-%j.out
#SBATCH --error=full-b/full-b-%j.err
#SBATCH --signal=B:TERM@120

# B: TaskFarmer launches a separate container for each of 100 Lund + 100 clasdis tasks.
# Before submission: module load taskfarmer; mkdir -p full-b
set -euo pipefail
repo_dir="${SIMGRID_REPO_DIR:-$(cd "${SLURM_SUBMIT_DIR:-$PWD}/../.." && pwd)}"
exec bash "$repo_dir/tests/nersc/full-taskfarmer.sh" B "${1:-ghcr.io/gemc/simgrid:test}"
