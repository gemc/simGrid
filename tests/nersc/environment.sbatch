#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=environment
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=environment/environment-%j.out

# Logs are written under environment/ (named for this test); create it before submitting:
#   mkdir -p environment
set -eu

# Global home is available on compute nodes, independently of the submission directory.
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"
image="ghcr.io/gemc/simgrid:test"

# Stage and run in a dedicated scratch directory (podman-hpc mounts $SCRATCH automatically).
work_dir="$SCRATCH/simgrid/environment"
mkdir -p "$work_dir"
cd "$work_dir"

run_nersc_container "$image" "$repo_dir/tests/nersc/environment.sh"
