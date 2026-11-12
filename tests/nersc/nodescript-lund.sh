#!/bin/bash
# GEMC NERSC trial with a Lund file input. Uses the shared setup_test_environment so OSG and NERSC
# exercise the same module/config stack. Usage: nodescript-lund.sh <nevents> <lund_file_url>
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

if [[ $# -ne 2 ]]; then
    printf 'Usage: nodescript-lund.sh <nevents> <lund_file_url>\n' >&2
    exit 2
fi
nevents="$1"
lund_url="$2"
if [[ ! "$nevents" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Event count must be a positive integer: %s\n' "$nevents" >&2
    exit 2
fi

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

# Read-only diagnostics, then the shared module/config environment (CLAS12_CONFIG, module checks,
# gcard/yaml verification). GEMC comes from CVMFS modules, so /cvmfs must be mounted.
report_environment "${SIMGRID_BACKEND:-}"
setup_test_environment "ungaro"

# input: Lund file lund.dat, output: gemc.hipo
run_timed load_module "$CLAS12_GEMC_MODULE"
run_timed load_module "$CLAS12_SQLITE_MODULE"
run_timed require_executable gemc
gcard="${CLAS12_CONFIG}/gemc/${CLAS12_CONFIG_TAG}/${CLAS12_RECON_CONFIG}.gcard"
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
