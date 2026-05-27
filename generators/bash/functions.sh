#!/bin/bash
# functions.sh — bash functions sourced by nodescript.sh on OSG worker nodes.

# ── Exit codes ────────────────────────────────────────────────────────────────
# Defined at top level so every function in this file can reference them
# as soon as functions.sh is sourced, before define_exit_codes is called.
# HTCondor periodic_release retries jobs that exit with codes 202-215, 230.
EC_INFRASTRUCTURE=202   # generic infrastructure failure
EC_GENERATOR=203        # event generator failure
EC_GEMC=204             # gemc simulation failure
EC_EVIO2HIPO=205        # evio → hipo conversion failure
EC_BG_MERGE=206         # background merge failure
EC_RECON=207            # recon-util reconstruction failure
EC_HIPO_UTILS=208       # hipo-utils / DST creation failure
EC_BG_MISSING=210       # background hipo file not found
EC_LS_STAT=211          # ls / stat / df command failure
EC_BG_FETCH=212         # background file fetch failure
EC_DISK=213             # disk space check failure
EC_HIPO_INTEGRITY=214   # hipo file integrity check failure
EC_HIPO_SIZE=215        # hipo file below minimum size
EC_DENOISE=230          # denoiser failure
EC_ENVIRONMENT=241      # environment / module system setup failure
EC_FILE_DOES_NOT_EXIST=242  # required file not found

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
    printf 'Job running on node: '; /bin/hostname
    printf 'Job submitted by: %s\n' "${USER:-unknown}"
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

    module load denoise/"$DENOISE_VERSION"
    module load sqlite/"$GEMC_VERSION"
}

# ── define_exit_codes ────────────────────────────────────────────────────────
# Confirm exit codes are loaded. Constants are defined at the top of this file
# and are available as soon as functions.sh is sourced.
define_exit_codes() {
    echo "Exit codes loaded."
}

# ── setup_job_parameters ─────────────────────────────────────────────────────
# Set and export the job configuration variables used by downstream functions.
# Called via: run_timed setup_job_parameters <submission_type> <coatjava_version> <gemc_version> <configuration>
setup_job_parameters() {
    SUBMISSION_TYPE="$1"
    COATJAVA_VERSION="$2"
    GEMC_VERSION="$3"
    CONFIGURATION="$4"
    DENOISE_VERSION="4.2.3"
    export SUBMISSION_TYPE COATJAVA_VERSION GEMC_VERSION CONFIGURATION DENOISE_VERSION
    echo "SUBMISSION_TYPE  : $SUBMISSION_TYPE"
    echo "COATJAVA_VERSION : $COATJAVA_VERSION"
    echo "GEMC_VERSION     : $GEMC_VERSION"
    echo "CONFIGURATION    : $CONFIGURATION"
    echo "DENOISE_VERSION  : $DENOISE_VERSION"
}

# ── setup_job_files ───────────────────────────────────────────────────────────
# Build and verify paths to required CVMFS configuration files.
#
# Reads globals (set by the generated nodescript.sh):
#   SUBMISSION_TYPE   — "prod" or "dev"
#   COATJAVA_VERSION  — e.g. "10.0.7"
#   GEMC_VERSION      — e.g. "5.14"
#   CONFIGURATION     — detector config name, e.g. "rga_fall2018"
#
# Sets and exports:
#   coatjava_yaml   — full path to the coatjava YAML reconstruction config
#   gemc_gcard      — full path to the gemc geometry card
#
# Exits with EC_FILE_DOES_NOT_EXIST if either file is absent.
setup_job_files() {
    local c12f_home="/cvmfs/oasis.opensciencegrid.org/jlab/hallb/clas12/sw/noarch/clas12-config/${SUBMISSION_TYPE}"

    coatjava_yaml="${c12f_home}/coatjava/${COATJAVA_VERSION}/${CONFIGURATION}.yaml"
    gemc_gcard="${c12f_home}/gemc/${GEMC_VERSION}/${CONFIGURATION}.gcard"

    export coatjava_yaml gemc_gcard

    echo "coatjava_yaml : $coatjava_yaml"
    echo "gemc_gcard    : $gemc_gcard"

    check_file_exists "$coatjava_yaml"
    check_file_exists "$gemc_gcard"
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
