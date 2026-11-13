#!/bin/bash
# Full NERSC trial (internal generator). Uses the shared setup_test_environment so OSG and
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
DST_BANKS='RUN::*,RAW::epics,RAW::scaler,HEL::flip,HEL::online,REC::*,RECFT::*'
DST_BANKS+=',MC::RecMatch,MC::GenMatch,MC::Particle,MC::User,MC::Header,MC::Lund,MC::Event'
DST_BANKS+=',RICH::Particle,RICH::Ring'
cmd=(hipo-utils -filter -b "$DST_BANKS" -merge -o dst.hipo recon.hipo)
echo "Running DST Filter: ${cmd[@]}"
run_timed create_dst clasdis "${SLURM_JOB_ID:-manual}" "${SIMGRID_TASK_ID:-0}" "${cmd[@]}"
printf 'DST output: %s/%s\n' "$output_dir" "$OUTPUT_FILE"
print_timing_summary
