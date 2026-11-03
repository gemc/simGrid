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

report_environment() {
    echo "=== System ==="
    hostname
    date
    uname -srmo
    printf 'Directory: %s\n' "$PWD"
    printf 'Bash: %s\n' "$BASH_VERSION"

    echo "=== Slurm allocation ==="
    printf 'Job: %s\n' "${SLURM_JOB_ID:-none}"
    printf 'Account: %s\n' "${SLURM_JOB_ACCOUNT:-unset}"
    printf 'Partition: %s\n' "${SLURM_JOB_PARTITION:-unset}"
    printf 'Nodes: %s\n' "${SLURM_JOB_NODELIST:-unset}"
    printf 'CPUs per task: %s\n' "${SLURM_CPUS_PER_TASK:-unset}"
    printf 'Memory per node (MB): %s\n' "${SLURM_MEM_PER_NODE:-unset}"

    echo "=== Storage ==="
    printf 'SCRATCH: %s\n' "${SCRATCH:-unset}"
    df -h .

    echo "=== Available commands ==="
    for tool in podman-hpc shifter pelican gemc java python3; do
        if command -v "$tool"; then
            :
        else
            printf '%s: unavailable in this environment\n' "$tool"
        fi
    done

    echo "=== Loaded modules ==="
    if type module >/dev/null 2>&1; then
        (set +u; module -t list)
    else
        echo "Module command is not initialized."
    fi
}

report_environment
