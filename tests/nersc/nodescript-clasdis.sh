#!/bin/bash
# GEMC-only NERSC trial (internal generator). Uses the shared setup_test_environment so OSG and
# NERSC exercise the same module/config stack. Usage: nodescript-clasdis.sh [nevents]
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

if [[ $# -gt 1 ]]; then
    printf 'Usage: nodescript-clasdis.sh [nevents]\n' >&2
    exit 2
fi
nevents="${1:-100}"
if [[ ! "$nevents" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Event count must be a positive integer: %s\n' "$nevents" >&2
    exit 2
fi

# Keep cleanup and generated files isolated from the shared configuration and other jobs.
output_dir=$(mktemp -d "$PWD/output-${SLURM_JOB_ID:-manual}-XXXXXX")
cd "$output_dir"
printf 'Output directory: %s\n' "$output_dir"

# Read-only diagnostics, then the shared module/config environment (CLAS12_CONFIG, module checks,
# gcard/yaml verification). GEMC comes from CVMFS modules, so /cvmfs must be mounted.
report_environment "${SIMGRID_BACKEND:-}"
setup_test_environment "ungaro"

# input: GEMC internal electron generator, output: gemc.hipo
run_timed load_module "$CLAS12_GEMC_MODULE"
run_timed load_module "$CLAS12_SQLITE_MODULE"
run_timed require_executable gemc
gcard="${CLAS12_CONFIG}/gemc/${CLAS12_CONFIG_TAG}/${CLAS12_RECON_CONFIG}.gcard"
printf 'Detector gcard: %s\n' "$gcard"
cmd=(
    gemc
    -USE_GUI=0
    -NGENP=100
    "-N=$nevents"
    "$gcard"
    -INPUT_GEN_FILE=gemc_internal
    "-BEAM_P=e-, 4*GeV, 20*deg, 20*deg"
    "-BEAM_SPOT=0.0*mm, 0.0*mm, 0.0*mm, 0.0*mm, 0*deg, reset "
    "-RASTER_VERTEX=0.0*cm, 0.0*cm, reset "
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
