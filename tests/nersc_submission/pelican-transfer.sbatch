#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=pelican-transfer
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=pelican-transfer/pelican-transfer-%j.out

# Logs are written under pelican-transfer/ (named for this test); create it before submitting:
#   mkdir -p pelican-transfer
set -eu

# Global home is available on compute nodes, independently of the submission directory.
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"
image="docker.io/jeffersonlab/clas12software:production"

# Keep the downloaded template and any retries isolated in a directory named for this test.
work_dir="$SCRATCH/simgrid/pelican-transfer"
mkdir -p "$work_dir"
cd "$work_dir"

# The node script renews an osdf://jlab-osdf token with token-renew.zsh; the launcher mounts the
# host .ssh (key + script) at /sshkeys.
run_nersc_container "$image" "$repo_dir/tests/nersc_submission/pelican_transfer.sh"
