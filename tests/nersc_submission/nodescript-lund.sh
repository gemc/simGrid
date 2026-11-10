#!/bin/bash
# GEMC NERSC trial with a Lund file input, following the command-array structure of the OSG nodescript.
# Usage: nodescript-lund.sh <gcard> <nevents> <lund_file_url>
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

if [[ $# -ne 3 ]]; then
    printf 'Usage: nodescript-lund.sh <gcard> <nevents> <lund_file_url>\n' >&2
    exit 2
fi
gcard="$1"
nevents="$2"
lund_url="$3"

# Keep cleanup and generated files isolated from the shared configuration and other jobs.
output_dir=$(mktemp -d "$PWD/output-${SLURM_JOB_ID:-manual}-XXXXXX")
cd "$output_dir"
printf 'Output directory: %s\n' "$output_dir"

run_timed require_executable pelican

# Obtain an OSDF bearer token before fetching the Lund file; token-renew.zsh (mounted from the host
# .ssh at /sshkeys) writes it to $BEARER_TOKEN_FILE using the gemc ssh key.
uid=$(id -u)
export XDG_RUNTIME_DIR="/run/user/$uid"
export BEARER_TOKEN_FILE="/var/run/user/$uid/bt_u$uid"
echo "Running token-renew: zsh /sshkeys/token-renew.zsh"
run_timed zsh /sshkeys/token-renew.zsh
if [[ ! -s "$BEARER_TOKEN_FILE" ]]; then
    echo "token-renew did not produce a bearer token at $BEARER_TOKEN_FILE" >&2
    exit "$EC_INFRASTRUCTURE"
fi

# input: Lund event file on OSDF, output: ./lund.dat consumed by GEMC
cmd=(pelican object get "$lund_url" lund.dat)
echo "Running pelican get: ${cmd[@]}"
run_timed "${cmd[@]}"
if [[ ! -s lund.dat ]]; then
    printf 'pelican get did not produce a nonempty lund.dat: %s\n' "$lund_url" >&2
    exit "$EC_FILE_DOES_NOT_EXIST"
fi

# Preserve the image's working software/module environment; no host CVMFS setup is required.
report_environment "${SIMGRID_BACKEND:-}"
export RCDB_CONNECTION=mysql://null
run_timed require_executable gemc

# input: Lund file lund.dat, output: gemc.hipo
printf 'Detector gcard: %s\n' "$gcard"
printf 'Lund input: %s\n' "$lund_url"
cmd=(
    gemc
    -USE_GUI=0
    -NGENP=100
    "-N=$nevents"
    "$gcard"
    "-INPUT_GEN_FILE=lund, lund.dat"
    "-SCALE_FIELD=binary_torus,    -1.00"
    "-SCALE_FIELD=binary_solenoid, -1.00"
    "-OUTPUT=hipo, gemc.hipo"
    "-INTEGRATEDRAW=*"
)
echo "Running GEMC: ${cmd[@]}"
run_timed run_gemc "${cmd[@]}"

if [[ ! -s gemc.hipo ]]; then
    echo "GEMC did not produce a nonempty gemc.hipo." >&2
    exit "$EC_HIPO_SIZE"
fi
printf 'GEMC output: %s/gemc.hipo\n' "$output_dir"
print_timing_summary
