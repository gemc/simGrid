#!/bin/bash
# functions.sh — bash functions sourced by nodescript.sh on OSG worker nodes.

# ── Exit codes ────────────────────────────────────────────────────────────────
# Defined at top level so every function in this file can reference them
# as soon as functions.sh is sourced, before define_exit_codes is called.
# HTCondor periodic_release retries jobs that exit with codes 202-215, 230.
EC_FILE_DOES_NOT_EXIST=242  # required file not found
EC_INFRASTRUCTURE=202   # generic infrastructure failure
EC_ENVIRONMENT=241      # environment / module system setup failure
EC_BG_MISSING=210       # background hipo file not found
EC_BG_FETCH=212         # background file fetch failure
EC_BG_MERGE=206         # background merge failure
EC_GENERATOR=203        # event generator failure
EC_GEMC=204             # gemc simulation failure
EC_EVIO2HIPO=205        # evio → hipo conversion failure
EC_RECON=207            # recon-util reconstruction failure
EC_HIPO_UTILS=208       # hipo-utils / DST creation failure
EC_HIPO_INTEGRITY=214   # hipo file integrity check failure
EC_LS_STAT=211          # ls / stat / df command failure
EC_HIPO_SIZE=215        # hipo file below minimum size
EC_DISK=213             # disk space check failure
EC_DENOISE=230          # denoiser failure

# ── Timing registry ───────────────────────────────────────────────────────────
# Parallel indexed arrays, compatible with bash 3+.
# Each run_timed call appends one entry; indices are kept in sync.
_TIMING_FUNCS=()
_TIMING_STARTS=()
_TIMING_ENDS=()
_TIMING_STATUS=()   # "ok" or "failed" per entry

_HR="======================================================================"

# ── run_timed ─────────────────────────────────────────────────────────────────
# Execute a named function and record its start/end epoch in the timing registry.
# Usage: run_timed <function_name> [args...]
# The return code of the wrapped function is preserved.
run_timed() {
    local fn="$1"; shift
    local t_start
    t_start=$(date +%s)
    _TIMING_FUNCS+=("$fn")
    _TIMING_STARTS+=("$t_start")
    echo
    echo "$_HR"
    echo "Starting ${fn} on $(date)"
    echo
    "${fn}" "$@"
    local rc=$?
    local t_end
    t_end=$(date +%s)
    _TIMING_ENDS+=("$t_end")
    if [[ $rc -ne 0 ]]; then
        _TIMING_STATUS+=("failed")
        echo
        echo "$_HR"
        echo "Completed ${fn} in $(( t_end - t_start ))s  ($(date))"
        echo "${fn} failed"
        exit $rc
    fi
    _TIMING_STATUS+=("ok")
    echo
    echo "$_HR"
    echo "Completed ${fn} in $(( t_end - t_start ))s  ($(date))"
    echo
    ls -l || {
        echo "ls failure"
        echo "removing data files and exiting"
        rm -f *.hipo *.evio *.sqlite
        exit $EC_LS_STAT
    }
}

# ── print_timing_summary ──────────────────────────────────────────────────────
# Print a human-readable summary followed by a JSON timing block.
# Failed steps are highlighted. JSON is parseable with:
#   python3 -c "import json, sys; print(json.load(sys.stdin))"
print_timing_summary() {
    local n=${#_TIMING_FUNCS[@]}
    local i
    echo
    echo "$_HR"
    echo "Summary:"
    for (( i=0; i<n; i++ )); do
        local fn=${_TIMING_FUNCS[$i]}
        local start=${_TIMING_STARTS[$i]}
        local end=${_TIMING_ENDS[$i]:-$start}
        local duration=$(( end - start ))
        if [[ "${_TIMING_STATUS[$i]}" == "failed" ]]; then
            printf "  %-30s FAILED in %ds\n" "$fn" "$duration"
        else
            printf "  %-30s completed in %ds\n" "$fn" "$duration"
        fi
    done
    echo "$_HR"
    echo
    echo "{"
    echo '  "timing": ['
    for (( i=0; i<n; i++ )); do
        local fn=${_TIMING_FUNCS[$i]}
        local start=${_TIMING_STARTS[$i]}
        local end=${_TIMING_ENDS[$i]:-$start}
        local duration=$(( end - start ))
        local status=${_TIMING_STATUS[$i]:-ok}
        local comma=","
        (( i + 1 == n )) && comma=""
        printf '    {"function": "%s", "start": %d, "end": %d, "duration_s": %d, "status": "%s"}%s\n' \
            "$fn" "$start" "$end" "$duration" "$status" "$comma"
    done
    echo '  ]'
    echo "}"
}

# ── setup_container_environment ──────────────────────────────────────────────
# Print job header, clear LMOD environment, initialise the module system,
# add CLAS12/Geant4 module paths, unload conflicting modules, and load
# the versioned software required by this job.
setup_container_environment() {
    local submitted_by="$1"
    local denoise_version="$2"
    local gemc_version="$3"

    printf 'Job running on node: '; /bin/hostname
    printf 'Job submitted by: %s\n' "$submitted_by"
    echo "Running directory: $(pwd)"
    echo "Bash version: $BASH_VERSION"

    echo "Directory $(pwd) content:"
    ls -l

    # Clear LMOD state — recommended by OSG to prevent conflicts with pilot env.
    unset ENABLE_LMOD \
          _LMFILES_ \
          LMOD_ANCIENT_TIME \
          LMOD_arch \
          LMOD_CMD \
          LMOD_COLORIZE \
          LMOD_DEFAULT_MODULEPATH \
          LMOD_DIR \
          LMOD_FULL_SETTARG_SUPPORT \
          LMOD_PACKAGE_PATH \
          LMOD_PKG \
          LMOD_PREPEND_BLOCK \
          LMOD_SETTARG_CMD \
          LMOD_SETTARG_FULL_SUPPORT \
          LMOD_sys \
          LMOD_SYSTEM_DEFAULT_MODULES \
          LMOD_VERSION \
          LOADEDMODULES \
          MODULEPATH \
          MODULEPATH_ROOT \
          MODULESHOME

    # Initialise the environment module system.
    # shellcheck source=/dev/null
    source /etc/profile.d/modules.sh || { echo "ERROR: failed to source /etc/profile.d/modules.sh"; exit $EC_ENVIRONMENT; }

    # Add CLAS12 software and Geant4 module paths.
    module use /cvmfs/oasis.opensciencegrid.org/jlab/hallb/clas12/sw/modulefiles
    module use /cvmfs/oasis.opensciencegrid.org/jlab/geant4/modules

    # Unload any modules that may have been pre-loaded by the pilot environment.
    module unload gemc
    module unload coatjava
    module unload jdk
    module unload root
    module unload mcgen

    module load denoise/"$denoise_version"
    module load sqlite/"$gemc_version"
}

# ── define_exit_codes ────────────────────────────────────────────────────────
# Confirm exit codes are loaded. Constants are defined at the top of this file
# and are available as soon as functions.sh is sourced.
define_exit_codes() {
    echo "Exit codes loaded."
}

# ── setup_job_files ───────────────────────────────────────────────────────────
# Build and verify paths to required CVMFS configuration files.
# Args: <submission_type> <coatjava_version> <gemc_version> <configuration>
# Sets and exports: coatjava_yaml, gemc_gcard.
# Exits with EC_FILE_DOES_NOT_EXIST if either file is absent.
setup_job_files() {
    local submission_type="$1"
    local coatjava_version="$2"
    local gemc_version="$3"
    local configuration="$4"
    local c12f_home="/cvmfs/oasis.opensciencegrid.org/jlab/hallb/clas12/sw/noarch/clas12-config/${submission_type}"

    coatjava_yaml="${c12f_home}/coatjava/${coatjava_version}/${configuration}.yaml"
    gemc_gcard="${c12f_home}/gemc/${gemc_version}/${configuration}.gcard"

    export coatjava_yaml gemc_gcard

    echo "coatjava_yaml : $coatjava_yaml"
    echo "gemc_gcard    : $gemc_gcard"

    check_file_exists "$coatjava_yaml"
    check_file_exists "$gemc_gcard"
}

# ── use_generator ────────────────────────────────────────────────────────────
# Load the mcgen module, generate a seed, run the external event generator,
# and remove any stray ROOT files it produces.
# Reads globals: MCGEN_VERSION, GENERATOR, GEN_OPTIONS, NEVENTS.
# Exits with EC_GENERATOR on generator failure.
use_generator() {
    local mcgen_version="$1"
    local generator="$2"
    local gen_options="$3"
    local nevents="$4"

    module load mcgen/"$mcgen_version"

    echo "GENERATOR START: $(date +%s)"

    generate-seeds.py generate
    local seed
    seed=$(generate-seeds.py read --row 1)
    echo "Generator seed from generate-seeds, row 1: $seed"

    echo
    echo "Running $nevents events with generator $generator with options: $gen_options"
    echo "Generator:"
    which "$generator"
    echo

    "$generator" --trig "$nevents" --docker $gen_options --seed "$seed" || {
        echo "GENERATOR ERROR >$generator< failed."
        exit $EC_GENERATOR
    }

    rm -f *.root
}

# ── setup_background_merging ──────────────────────────────────────────────────
# Fetch a random background hipo file from OSDF for background merging.
# Reads globals: CONFIGURATION, FIELDS, BKMERGING (exported by setup_job_parameters).
# Exits with EC_BG_MISSING if ls fails or no files found, EC_BG_FETCH if download fails.
setup_background_merging() {
    local configuration="$1"
    local fields="$2"
    local bkmerging="$3"
    local xdir="osdf:///jlab-osdf/clas12/osgpool/backgroundfiles/${configuration}/${fields}/${bkmerging}/10k"

    echo "Executing: pelican object ls $xdir"
    local ls_output
    ls_output=$(pelican object ls "$xdir") || {
        echo "pelican object ls failed for $xdir"
        exit $EC_BG_MISSING
    }

    local NFILES
    NFILES=$(echo "$ls_output" | wc -l)
    if [[ $NFILES -eq 0 ]]; then
        echo "No background files found at $xdir"
        exit $EC_BG_FETCH
    fi

    local R=$(( RANDOM % NFILES + 1 ))
    local bgfile="${xdir}/$(printf '%05d' "$R").hipo"
    echo "Selected background file: $bgfile"

    echo "Executing: pelican object get $bgfile ."
    pelican object get "$bgfile" . || exit $EC_BG_FETCH
}

# ── setup_pelican ─────────────────────────────────────────────────────────────
# Configure Pelican/OSDF authentication using the HTCondor credential directory.
# _CONDOR_CREDS is set by HTCondor before the job starts.
setup_pelican() {
    echo "Setting Pelican environment variables"
    echo "_CONDOR_CREDS: $_CONDOR_CREDS"
    export BEARER_TOKEN_FILE="$_CONDOR_CREDS/jlab_clas12.use"
    echo " BEARER_TOKEN_FILE: $BEARER_TOKEN_FILE"
    echo " pelican: $(which pelican)"
}

# ── check_file_exists ─────────────────────────────────────────────────────────
# Verify that a required file exists; exit with EC_FILE_DOES_NOT_EXIST if not.
# Usage: check_file_exists <path>
check_file_exists() {
    local file="$1"
    if [[ ! -f "$file" ]]; then
        echo "ERROR: required file not found: $file"
        exit $EC_FILE_DOES_NOT_EXIST
    fi
    echo "Found: $file"
}
