#!/bin/bash
# GEMC-only NERSC trial, following the command-array structure of the OSG nodescript.
# Usage: nodescript.sh [gcard] [nevents]
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

if [[ $# -gt 2 ]]; then
    printf 'Usage: nodescript.sh [gcard] [nevents]\n' >&2
    exit 2
fi
gcard="${1:-/global/cfs/cdirs/m5464/clas12-config/main/gemc/dev/rga_fall2018.gcard}"
nevents="${2:-100}"
[[ "$gcard" == /* ]] || gcard="$PWD/$gcard"
if [[ ! -f "$gcard" || ! -r "$gcard" ]]; then
    printf 'GEMC detector gcard is not readable: %s\n' "$gcard" >&2
    exit "$EC_FILE_DOES_NOT_EXIST"
fi
if [[ ! "$nevents" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Event count must be a positive integer: %s\n' "$nevents" >&2
    exit 2
fi

# Keep cleanup and generated files isolated from the shared configuration and other jobs.
output_dir=$(mktemp -d "$PWD/output-${SLURM_JOB_ID:-manual}-XXXXXX")
cd "$output_dir"
printf 'Output directory: %s\n' "$output_dir"

# Preserve the image's working software/module environment; no host CVMFS setup is required.
report_environment "${SIMGRID_BACKEND:-}"
export RCDB_CONNECTION=mysql://null
run_timed require_executable gemc

# input: GEMC internal electron generator, output: gemc.hipo
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
