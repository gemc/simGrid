#!/bin/bash
# functions.sh — bash functions sourced by nodeScript.sh on OSG worker nodes.

# Execute a named function with printed start/end epoch timestamps.
# Usage: run_timed <function_name> [args...]
#   START <name>: <epoch>   printed before the call
#   END   <name>: <epoch>   printed after, regardless of exit code
# The return code of the wrapped function is preserved.
run_timed() {
    local fn="$1"; shift
    echo "START ${fn}: $(date +%s)"
    "${fn}" "$@"
    local rc=$?
    echo "END ${fn}: $(date +%s)"
    return $rc
}

# Print job header, clear LMOD environment, initialise the module system.
# Called first in nodeScript.sh to establish a clean, reproducible environment
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
