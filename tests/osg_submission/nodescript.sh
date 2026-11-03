#!/bin/bash
# nodescript.sh — CLAS12 simulation script executed on the OSG worker node.
#
# Invoked directly by HTCondor:
#   ./nodescript.sh <sjob> <lundFile>
#
# Arguments:
#   1. sjob             — subjob index (HTCondor $(Process), 0-based)
#   2. lundFile         — OSDF URI of the lund input file

set -euo pipefail

sjob=$1
lundFile=$2
lund_base="${lundFile##*/}"
lund_base="${lund_base%.*}"
# lund_base is the lund filename without path or extension (e.g. lund1 from osdf://.../lund1.dat)
runno=""

# Create the output directory, copy all staged files into it, and run there
# so every output file lands where HTCondor's transfer_output_files expects it.
# Use *.* to match only files with an extension, excluding HTCondor's own
# _condor_stderr and _condor_stdout capture files created before the job starts.
mkdir -p output
{ cp -- *.* output/ 2>/dev/null; } || true
cd output

# Source shared bash functions (run_timed, container_environment, define_exit_codes).
# shellcheck source=functions.sh
source functions.sh

define_exit_codes

# Module environment setup
export CLAS12_CONFIG="/cvmfs/jlab.opensciencegrid.org/hallb/clas12/sw/noarch/clas12-config/dev"
echo "CLAS12_CONFIG: $CLAS12_CONFIG"
export OSRELEASE="almalinux9-gcc11"
echo "OSRELEASE: $OSRELEASE"
run_timed clean_and_check_environment "ungaro" \
    "gemc/dev" \
    "sqlite/dev" \
    "jdk/21.0.2" \
    "coatjava/14.1.2"
export RCDB_CONNECTION=mysql://null
echo "SQLITE Version: dev"
run_timed setup_job_files "14.1.2" "dev" "highlumi_stage2" "mc-ai"

# Pelican environment setup
echo "Setting Pelican env variables"
echo "_CONDOR_CREDS: $_CONDOR_CREDS"
export BEARER_TOKEN_FILE="$_CONDOR_CREDS/jlab_clas12.use"
echo "BEARER_TOKEN_FILE: $BEARER_TOKEN_FILE"
echo "pelican: $(which pelican)"
echo "Background merging not requested — skipping fetch."

echo
echo "Running pelican object get $lundFile lund.dat"
pelican object get $lundFile lund.dat
echo

# Running GEMC
echo "input: lund.dat, output: gemc.hipo"
run_timed load_module "gemc/dev"
run_timed load_module "sqlite/dev"
run_timed require_executable "gemc"
gcard="${CLAS12_CONFIG}/gemc/dev/highlumi_stage2.gcard"
cmd=(
    gemc
    -USE_GUI=0
    -NGENP=100
    -N=5000
    "$gcard"
    "-INPUT_GEN_FILE=lund, lund.dat"
    "-RANDOMIZE_LUND_VZ=0.0*cm, 2.5*cm, reset "
    "-BEAM_SPOT=0.0*mm, 0.0*mm, 0.0*mm, 0.0*mm, 0*deg, reset "
    "-RASTER_VERTEX=0.0*cm, 0.0*cm, reset "
    "-SCALE_FIELD=binary_torus,    -1.00"
    "-SCALE_FIELD=binary_solenoid, -1.00"
    "-OUTPUT=hipo, gemc.hipo"
    "-INTEGRATEDRAW=*"
)
echo "Running GEMC: ${cmd[@]}"
run_timed run_gemc "${cmd[@]}"
echo "Background merging not requested — skipping."

# Running Reconstruction
echo "input: gemc.hipo, output: recon.hipo"
unload_module_if_loaded gemc
run_timed load_module "jdk/21.0.2"
run_timed load_module "coatjava/14.1.2"
yaml="${CLAS12_CONFIG}/coatjava/14.1.2/mc-ai.yaml"
recon_util="/cvmfs/jlab.opensciencegrid.org/hallb/clas12/sw/noarch/coatjava/bin/recon-util"
run_timed require_executable "$recon_util"
cmd=("$recon_util"
    -y "$yaml"
    -i gemc.hipo
    -o recon.hipo
    -- -Xmx1920m)
echo "Running Reconstruction: ${cmd[@]}"
run_timed run_reconstruction "${cmd[@]}"
rm -f gemc.hipo

echo "input: recon.hipo"
run_timed require_executable "hipo-utils"
cmd=(hipo-utils -test recon.hipo)
echo "Running HIPO Integrity Test: ${cmd[@]}"
run_timed test_hipo_file "${cmd[@]}"

echo "input: recon.hipo, output: inelastic-$lund_base-test-$sjob.hipo"
DST_BANKS='RUN::*,RAW::epics,RAW::scaler,HEL::flip,HEL::online,REC::*,RECFT::*,MC::RecMatch,MC::GenMatch,MC::Particle,MC::User,MC::Header,MC::Lund,MC::Event,RICH::Particle,RICH::Ring'
cmd=(hipo-utils -filter -b "$DST_BANKS" -merge -o dst.hipo recon.hipo)
echo "Running DST Filter: ${cmd[@]}"
run_timed create_dst "inelastic" "test" "$sjob" "${cmd[@]}"

echo "input: inelastic-$lund_base-test-$sjob.hipo, output: osdf:///jlab-osdf/clas12/volatile/osg/ungaro/test/inelastic-$lund_base-test-$sjob.hipo"
run_timed write_to_jlab "ungaro" "inelastic" "test" "$sjob"


print_timing_summary
