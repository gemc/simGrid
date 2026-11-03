#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=nersc-probe
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=nersc-probe-%j.out

set -eu

# Global home is available on compute nodes, independently of the submission directory.
functions_file="$HOME/software/simgrid/main/generators/bash/functions.sh"

source "$functions_file"
report_environment nersc
