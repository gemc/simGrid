#!/bin/zsh

#SBATCH --account=m5464
#SBATCH --job-name=nersc-gemc-image
#SBATCH --constraint=cpu
#SBATCH --qos=shared
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=2
#SBATCH --mem=2G
#SBATCH --time=00:05:00
#SBATCH --output=nersc-gemc-image-%j.out

set -eu

# Global home is available on compute nodes, independently of the submission directory.
functions_file="$HOME/software/simgrid/main/generators/bash/functions.sh"
if [[ ! -r "$functions_file" ]]; then
    printf 'Shared functions are not readable: %s\n' "$functions_file" >&2
    exit 2
fi

image=docker.io/jeffersonlab/gemc:dev-almalinux94
image=docker.io/jeffersonlab/clas12software:production
printf 'Compute node: %s\n' "$(hostname)"
printf 'Container image: %s\n' "$image"

# Keep the report on stdin and use the image already pulled on the login node.
# Forward allocation metadata explicitly; the container has its own environment.
podman-hpc run --rm -i --pull=never \
    --volume "$PWD:$PWD" \
    --volume "$functions_file:/opt/simgrid/functions.sh:ro" \
    --workdir "$PWD" \
    --env 'SLURM_*' \
    --env SCRATCH \
    --entrypoint /bin/bash \
    "$image" -l -s <<'CONTAINER'
set -eu

source /opt/simgrid/functions.sh
report_environment nersc
CONTAINER
