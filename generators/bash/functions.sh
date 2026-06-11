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
    local errexit_enabled=0
    [[ $- == *e* ]] && errexit_enabled=1 && set +e
    "${fn}" "$@"
    local rc=$?
    [[ $errexit_enabled -eq 1 ]] && set -e
    local t_end
    t_end=$(date +%s)
    _TIMING_ENDS+=("$t_end")
    if [[ $rc -ne 0 ]]; then
        _TIMING_STATUS+=("failed")
        echo
        echo "$_HR"
        echo "Completed ${fn} in $(( t_end - t_start ))s  ($(date))"
        echo "${fn} failed"
        cleanup_on_error
        exit $rc
    fi
    _TIMING_STATUS+=("ok")
    echo
    echo "$_HR"
    echo "Completed ${fn} in $(( t_end - t_start ))s  ($(date))"
    echo
    echo "Check Filesystem Integrity"
    ls -l > /dev/null || {
        echo "ls failure"
        echo "removing data files and exiting"
        rm -f *.hipo *.evio *.sqlite
        exit $EC_LS_STAT
    }
}

# ── cleanup_on_error ─────────────────────────────────────────────────────────
# Remove intermediate simulation files after any pipeline step failure.
# Called automatically by run_timed when a step exits non-zero.
cleanup_on_error() {
    echo "Cleaning up intermediate files after error"
    rm -f *.hipo *.evio *.sqlite *.dat
    rm -f random-seeds.txt RNDMSTATUS
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

# -- clean_environment --
# Print job header and clear inherited LMOD environment.
# Module system setup, CLAS12_CONFIG, pilot-module unloads, and versioned loads
# are emitted directly in nodescript.sh.
# Args: <submitted_by>
clean_environment() {
    local submitted_by="$1"

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

}

# ── define_exit_codes ────────────────────────────────────────────────────────
# Confirm exit codes are loaded. Constants are defined at the top of this file
# and are available as soon as functions.sh is sourced.
define_exit_codes() {
    echo "Exit codes loaded."
}

# -- module helpers --
# Load or unload environment modules through run_timed so module failures get
# the same timing and cleanup behavior as simulation pipeline failures.
load_module() {
    local module_name="$1"
    local nounset_enabled=0
    echo "Loading module: ${module_name}"
    [[ $- == *u* ]] && nounset_enabled=1 && set +u
    module load "$module_name"
    local rc=$?
    [[ $nounset_enabled -eq 1 ]] && set -u
    if [[ $rc -ne 0 ]]; then
        echo "ERROR: failed to load ${module_name}"
        return $EC_ENVIRONMENT
    fi
}

load_modules() {
    local module_name
    for module_name in "$@"; do
        load_module "$module_name" || return $?
    done
}

unload_module_if_loaded() {
    local module_name="$1"
    local nounset_enabled=0
    [[ $- == *u* ]] && nounset_enabled=1 && set +u
    module unload "$module_name" >/dev/null 2>&1 || true
    [[ $nounset_enabled -eq 1 ]] && set -u
}

# ── setup_job_files ───────────────────────────────────────────────────────────
# Verify that the gcard and yaml files required by this job exist under
# $CLAS12_CONFIG (exported by nodescript.sh).
# Args: <coatjava_version> <gemc_version> <configuration>
# Exits with EC_FILE_DOES_NOT_EXIST if either file is absent.
setup_job_files() {
    local coatjava_version="$1"
    local gemc_version="$2"
    local configuration="$3"

    local coatjava_yaml="${CLAS12_CONFIG}/coatjava/${coatjava_version}/${configuration}.yaml"
    local gemc_gcard="${CLAS12_CONFIG}/gemc/${gemc_version}/${configuration}.gcard"

    echo "coatjava_yaml : $coatjava_yaml"
    echo "gemc_gcard    : $gemc_gcard"

    check_file_exists "$coatjava_yaml"
    check_file_exists "$gemc_gcard"
}

# ── run_generator ────────────────────────────────────────────────────────────
# Run the pre-built generator command passed as "$@" from nodescript.sh.
# Removes stray ROOT files produced by some generators.
# Exits with EC_GENERATOR on failure.
run_generator() {
    echo "Generator path: $(which "$1")"
    "$@" || { echo "GENERATOR ERROR: $1 failed."; return $EC_GENERATOR; }
    rm -f *.root
}

# ── fetch_background_file ──────────────────────────────────────────────────
# Fetch a random background hipo file from OSDF for background merging.
# Reads globals: CONFIGURATION, FIELDS, BKMERGING (exported by setup_job_parameters).
# Exits with EC_BG_MISSING if ls fails or no files found, EC_BG_FETCH if download fails.
fetch_background_file() {
    local configuration="$1"
    local fields="$2"
    local bkmerging="$3"
    local xdir="osdf:///jlab-osdf/clas12/osgpool/backgroundfiles/${configuration}/${fields}/${bkmerging}/10k"

    echo "Executing: pelican object ls $xdir"
    local ls_output
    ls_output=$(pelican object ls "$xdir") || {
        echo "pelican object ls failed for $xdir"
        return $EC_BG_MISSING
    }

    local NFILES
    NFILES=$(echo "$ls_output" | wc -l)
    if [[ $NFILES -eq 0 ]]; then
        echo "No background files found at $xdir"
        return $EC_BG_FETCH
    fi

    local R=$(( RANDOM % NFILES + 1 ))
    local bgfile="${xdir}/$(printf '%05d' "$R").hipo"
    echo "Selected background file: $bgfile"

    echo "Executing: pelican object get $bgfile ."
    pelican object get "$bgfile" . || return $EC_BG_FETCH
    BG_FILE=$(basename "$bgfile")
    if [[ ! -s "$BG_FILE" ]]; then
        echo "ERROR: downloaded background file is empty: $BG_FILE"
        rm -f "$BG_FILE"
        return $EC_BG_FETCH
    fi
    echo "Background file downloaded: ${BG_FILE}"
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

# ── run_gemc ──────────────────────────────────────────────────────────────────
# Load gemc module and run the simulation.
# Args: <gemc_version> <gcard> <nevents> <input_gen_file> <genoptions>
#       <zposition> <beam_spot> <raster> <torus_scale> <solenoid_scale>
# input_gen_file: "lund, <file>.dat" for external/lund-file input; empty for gemc internal generator.
# genoptions:     additional gemc options (e.g. -BEAM_P=... -SPREAD_P=...) for gemc internal; empty otherwise.
# zposition/beam_spot/raster: pass "n/a" to omit the corresponding GEMC option.
run_gemc() {
    echo "GEMC path: $(which gemc)"
    "$@" | sed '/G4Exception-START/,/G4Exception-END/d' || { echo "GEMC failed."; return $EC_GEMC; }
    rm -f *.dat
}

# ── merge_background ──────────────────────────────────────────────────────────
# Merge background hipo file (fetched by fetch_background_file) with gemc output.
# Reads global: BG_FILE (set by fetch_background_file).
merge_background() {
    "$@" || { echo "bg-merger failed."; return $EC_BG_MERGE; }
    rm -f gemc.hipo "${BG_FILE}"
}

# ── run_denoiser ──────────────────────────────────────────────────────────────
# Load denoise module and run the ML denoiser on the gemc hipo output.
# Args: <denoise_version> <input_file>  (gemc.hipo when no bg merging; gemc.merged.hipo otherwise)
run_denoiser() {
    "$@" || { echo "denoiser failed."; return $EC_DENOISE; }
}

# ── run_reconstruction ────────────────────────────────────────────────────────
# Load coatjava module and run recon-util reconstruction.
# Args: <coatjava_version> <coatjava_yaml>
run_reconstruction() {
    df /cvmfs/oasis.opensciencegrid.org && df . && df /tmp || { echo "df failure"; return $EC_DISK; }
    "$@" || { echo "recon-util failed."; return $EC_RECON; }
    df /cvmfs/oasis.opensciencegrid.org && df . && df /tmp || { echo "df failure"; return $EC_DISK; }
}

# ── test_hipo_file ────────────────────────────────────────────────────────────
# Test integrity and minimum size of recon.hipo.
test_hipo_file() {
    "$@" || { echo "hipo-utils test failed."; return $EC_HIPO_INTEGRITY; }
    local fsize
    fsize=$(stat -L -c%s recon.hipo)
    if [[ $fsize -lt 100 ]]; then
        echo "recon.hipo too small: ${fsize} bytes"
        return $EC_HIPO_SIZE
    fi
    echo "recon.hipo integrity OK, size ${fsize} bytes"
}

# ── get_output_filename ───────────────────────────────────────────────────────
# Set OUTPUT_FILE from string_id, submission_id, and sjob.
# Script-level variables lundFile and runno (both set in preamble) are included
# when non-empty: lund_base between string_id and IDs; runno between lund_base and IDs.
# Args: <string_id> <submission_id> <sjob>
get_output_filename() {
    local string_id="$1"
    local submission_id="$2"
    local sjob="$3"
    local runno_part="${runno:-}"

    if [[ -n "${lundFile:-}" ]]; then
        local lund_base="${lundFile##*/}"
        lund_base="${lund_base%.*}"
        if [[ -n "$runno_part" ]]; then
            OUTPUT_FILE="${string_id}-${lund_base}-${runno_part}-${submission_id}-${sjob}.hipo"
        else
            OUTPUT_FILE="${string_id}-${lund_base}-${submission_id}-${sjob}.hipo"
        fi
    elif [[ -n "$runno_part" ]]; then
        OUTPUT_FILE="${string_id}-${runno_part}-${submission_id}-${sjob}.hipo"
    else
        OUTPUT_FILE="${string_id}-${submission_id}-${sjob}.hipo"
    fi
    echo "Output filename: ${OUTPUT_FILE}"
}

# ── create_dst ────────────────────────────────────────────────────────────────
# Filter recon.hipo into a DST hipo file.
# Args: <string_id> <submission_id> <sjob>
create_dst() {
    local string_id="$1" submission_id="$2" sjob="$3"; shift 3
    get_output_filename "$string_id" "$submission_id" "$sjob"
    "$@" || { echo "hipo-utils filter failed."; return $EC_HIPO_UTILS; }
    echo "Moving dst.hipo to ${OUTPUT_FILE}"
    mv dst.hipo "$OUTPUT_FILE" || { echo "mv failed."; return $EC_HIPO_UTILS; }
    hipo-utils -test "$OUTPUT_FILE" || { echo "hipo-utils test failed."; return $EC_HIPO_INTEGRITY; }
    rm -f recon.hipo
    echo "DST file created: ${OUTPUT_FILE}"
}

# ── write_to_jlab ─────────────────────────────────────────────────────────────
# Upload the output hipo file to OSDF via pelican and clean up working directory.
# Args: <username> <string_id> <submission_id> <sjob>
write_to_jlab() {
    local username="$1"
    get_output_filename "$2" "$3" "$4"
    local submission_id="$3"

    local -a cmd=(
        /usr/bin/pelican -d object put "${OUTPUT_FILE}"
        "osdf:///jlab-osdf/clas12/volatile/osg/${username}/${submission_id}/${OUTPUT_FILE}"
    )
    echo "Running: ${cmd[*]}"
    echo
    "${cmd[@]}" || { echo "pelican upload failed."; return $EC_INFRASTRUCTURE; }

    echo "Additional cleanup"
    rm -f core* *.gcard
    rm -f recon.hipo gemc.hipo gemc.merged.hipo gemc_denoised.hipo
    rm -f nodescript.sh condor_exec.exe
    rm -f RNDMSTATUS random-seeds.txt Null gemc.evio *.hipo
}
