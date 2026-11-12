#!/bin/bash
# Read-only diagnostics executed inside the environment probe's container.
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
report_environment "${SIMGRID_BACKEND:-nersc}"
