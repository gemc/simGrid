#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=nersc-transfer
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=nersc-transfer-%j.out

set -eu

# Global home is available on compute nodes, independently of the submission directory.
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"
image="docker.io/jeffersonlab/clas12software:production"

run_nersc_container "$image" "$repo_dir/tests/nersc_submission/environment.sh"
