#!/bin/bash
# functions.sh — bash functions sourced by nodescript.sh on OSG worker nodes.

# Execute a named function with emphasized start/end timestamp banners.
# Usage: run_timed <function_name> [args...]
# Each banner prints the unix epoch followed by the human-readable date,
# surrounded by blank lines so sections are visually separated in logs.
# The return code of the wrapped function is preserved.
run_timed() {
    local fn="$1"; shift
    echo
    echo "==================================================================="
    echo ">>> START ${fn}: $(date +%s)  $(date)"
    echo "==================================================================="
    echo
    "${fn}" "$@"
    local rc=$?
    echo
    echo "==================================================================="
    echo ">>> END ${fn}: $(date +%s)  $(date)"
    echo "==================================================================="
    echo
    return $rc
}

# Print job header, clear LMOD environment, initialise the module system.
# Called first in nodescript.sh to establish a clean, reproducible environment
# before any module load or software invocation.
container_environment() {
    printf 'Job running on node: '; /bin/hostname
    printf 'Job submitted by: %s\n' "${USER:-unknown}"
    echo "Running directory: $(pwd)"

    echo "Directory $(pwd) content:"
    ls -l || { echo "ls failure"; exit 211; }

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
    if [[ -f /etc/profile.d/modules.sh ]]; then
        # shellcheck source=/dev/null
        source /etc/profile.d/modules.sh
    else
        echo "WARNING: /etc/profile.d/modules.sh not found — module command unavailable"
    fi
}

# Define and print all exit codes used by the simulation pipeline.
# HTCondor's periodic_release expression uses these codes to distinguish
# transient infrastructure failures (worth retrying) from job bugs (hold).
# Variables are exported so downstream functions can reference them by name.
define_exit_codes() {
    export EC_INFRASTRUCTURE=202   # generic infrastructure failure
    export EC_GENERATOR=203        # event generator failure
    export EC_GEMC=204             # gemc simulation failure
    export EC_EVIO2HIPO=205        # evio → hipo conversion failure
    export EC_BG_MERGE=206         # background merge failure
    export EC_RECON=207            # recon-util reconstruction failure
    export EC_HIPO_UTILS=208       # hipo-utils / DST creation failure
    export EC_BG_MISSING=210       # background hipo file not found
    export EC_LS_STAT=211          # ls / stat / df command failure
    export EC_BG_FETCH=212         # background file fetch failure
    export EC_DISK=213             # disk space check failure
    export EC_HIPO_INTEGRITY=214   # hipo file integrity check failure
    export EC_HIPO_SIZE=215        # hipo file below minimum size
    export EC_DENOISE=230          # denoiser failure

    echo "Exit codes:"
    printf "  %3d  %-20s %s\n"  202  "EC_INFRASTRUCTURE"  "generic infrastructure failure"
    printf "  %3d  %-20s %s\n"  203  "EC_GENERATOR"       "event generator failure"
    printf "  %3d  %-20s %s\n"  204  "EC_GEMC"            "gemc simulation failure"
    printf "  %3d  %-20s %s\n"  205  "EC_EVIO2HIPO"       "evio → hipo conversion failure"
    printf "  %3d  %-20s %s\n"  206  "EC_BG_MERGE"        "background merge failure"
    printf "  %3d  %-20s %s\n"  207  "EC_RECON"           "recon-util reconstruction failure"
    printf "  %3d  %-20s %s\n"  208  "EC_HIPO_UTILS"      "hipo-utils / DST creation failure"
    printf "  %3d  %-20s %s\n"  210  "EC_BG_MISSING"      "background hipo file not found"
    printf "  %3d  %-20s %s\n"  211  "EC_LS_STAT"         "ls / stat / df command failure"
    printf "  %3d  %-20s %s\n"  212  "EC_BG_FETCH"        "background file fetch failure"
    printf "  %3d  %-20s %s\n"  213  "EC_DISK"            "disk space check failure"
    printf "  %3d  %-20s %s\n"  214  "EC_HIPO_INTEGRITY"  "hipo file integrity check failure"
    printf "  %3d  %-20s %s\n"  215  "EC_HIPO_SIZE"       "hipo file below minimum size"
    printf "  %3d  %-20s %s\n"  230  "EC_DENOISE"         "denoiser failure"
}
