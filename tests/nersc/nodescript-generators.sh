#!/bin/bash
# mcgen generator smoke test for NERSC: run one generator with --trig <N> --docker and confirm it
# produces output. Usage: nodescript-generators.sh <generator> [ntrig]
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

if [[ $# -lt 1 || $# -gt 2 ]]; then
    printf 'Usage: nodescript-generators.sh <generator> [ntrig]\n' >&2
    exit 2
fi
generator="$1"
ntrig="${2:-100}"
if [[ ! "$ntrig" =~ ^[1-9][0-9]*$ ]]; then
    printf 'Trigger count must be a positive integer: %s\n' "$ntrig" >&2
    exit 2
fi

# Keep each generator's output isolated from the others and from the shared configuration.
output_dir=$(mktemp -d "$PWD/output-${SLURM_JOB_ID:-manual}-${generator}-XXXXXX")
cd "$output_dir"
printf 'Output directory: %s\n' "$output_dir"

# Read-only diagnostics, then load the mcgen module from CVMFS (so /cvmfs must be mounted).
report_environment "${SIMGRID_BACKEND:-}"
run_timed clean_and_check_environment "ungaro" "$CLAS12_MCGEN_MODULE"
run_timed load_module "$CLAS12_MCGEN_MODULE"
run_timed require_executable "$generator"

# input: none, output: <generator> Lund .dat file(s)
cmd=("$generator" --trig "$ntrig" --docker)
echo "Running Generator: ${cmd[@]}"
run_timed run_generator "${cmd[@]}"

# Confirm the generator produced at least one nonempty .dat output.
shopt -s nullglob
dats=(*.dat)
if (( ${#dats[@]} == 0 )); then
    printf 'Generator %s produced no .dat output.\n' "$generator" >&2
    exit "$EC_GENERATOR"
fi
printf 'Generator %s output: %s\n' "$generator" "${dats[*]}"
print_timing_summary
