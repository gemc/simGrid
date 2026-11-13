#!/bin/bash
# Full NERSC trial with a Lund file input. Uses the shared setup_test_environment so OSG and NERSC
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
export XDG_RUNTIME_DIR="${XDG_RUNTIME_DIR:-/run/user/$uid}"
export BEARER_TOKEN_FILE="${BEARER_TOKEN_FILE:-/var/run/user/$uid/bt_u$uid}"
if [[ "${SIMGRID_TOKEN_READY:-0}" != 1 ]]; then
    echo "Running token-renew: zsh /sshkeys/token-renew.zsh"
    run_timed zsh /sshkeys/token-renew.zsh
fi
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
if [[ -n "${SIMGRID_TASK_SEED:-}" ]]; then
    cmd+=("-RANDOM=$SIMGRID_TASK_SEED")
fi
echo "Running GEMC: ${cmd[@]}"
run_timed run_gemc "${cmd[@]}"

if [[ ! -s gemc.hipo ]]; then
    echo "GEMC did not produce a nonempty gemc.hipo." >&2
    exit "$EC_HIPO_SIZE"
fi
printf 'GEMC output: %s/gemc.hipo\n' "$output_dir"

# input: gemc.hipo, output: recon.hipo
unload_module_if_loaded gemc
run_timed load_module "$CLAS12_JDK_MODULE"
run_timed load_module "$CLAS12_COATJAVA_MODULE"
yaml="${CLAS12_CONFIG}/coatjava/${CLAS12_COATJAVA_VERSION}/${CLAS12_RECON_YAML}.yaml"
recon_util="/cvmfs/jlab.opensciencegrid.org/hallb/clas12/sw/noarch/coatjava/bin/recon-util"
run_timed require_executable "$recon_util"
cmd=("$recon_util" -y "$yaml" -i gemc.hipo -o recon.hipo -- -Xmx1920m)
echo "Running Reconstruction: ${cmd[@]}"
run_timed run_reconstruction "${cmd[@]}"
rm -f gemc.hipo

# input: recon.hipo, output: integrity status
run_timed require_executable hipo-utils
cmd=(hipo-utils -test recon.hipo)
echo "Running HIPO Integrity Test: ${cmd[@]}"
run_timed test_hipo_file "${cmd[@]}"

# input: recon.hipo, output: named DST HIPO file retained on scratch
lundFile="$lund_url"
DST_BANKS='RUN::*,RAW::epics,RAW::scaler,HEL::flip,HEL::online,REC::*,RECFT::*'
DST_BANKS+=',MC::RecMatch,MC::GenMatch,MC::Particle,MC::User,MC::Header,MC::Lund,MC::Event'
DST_BANKS+=',RICH::Particle,RICH::Ring'
cmd=(hipo-utils -filter -b "$DST_BANKS" -merge -o dst.hipo recon.hipo)
echo "Running DST Filter: ${cmd[@]}"
run_timed create_dst lund "${SLURM_JOB_ID:-manual}" "${SIMGRID_TASK_ID:-${SLURM_ARRAY_TASK_ID:-0}}" "${cmd[@]}"
printf 'DST output: %s/%s\n' "$output_dir" "$OUTPUT_FILE"
print_timing_summary
