#!/bin/bash
# Prepare and run the same 200-task, 500-event campaign for container layouts B and C.
set -euo pipefail
layout="${1:?Expected B or C}"
image="${2:?Expected container image}"
case "$layout" in B|C) ;; *) echo 'Layout must be B or C.' >&2; exit 2 ;; esac
repo_dir=$(cd "$(dirname "$0")/../.." && pwd)
export SIMGRID_REPO_DIR="$repo_dir"
export THREADS="${THREADS:-100}"
if [[ ! "$THREADS" =~ ^[1-9][0-9]*$ ]] || (( THREADS > 128 )); then
    echo 'THREADS must be between 1 and 128.' >&2
    exit 2
fi
: "${SLURM_JOB_ID:?Run this test inside a Slurm allocation}"
: "${SCRATCH:?SCRATCH must be set}"
test_name=full-b
[[ "$layout" != C ]] || test_name=full-c
campaign="${SIMGRID_FULL_CAMPAIGN:-$SCRATCH/simgrid/$test_name/$SLURM_JOB_ID}"
mkdir -p "$campaign/scripts" "$campaign/jobs" "$campaign/containers"
campaign=$(cd "$campaign" && pwd)

# Preserve the task list and TaskFarmer progress files when explicitly resuming a campaign.
if [[ ! -f "$campaign/tasks.txt" ]]; then
    cp "$repo_dir/generators/bash/functions.sh" "$campaign/scripts/functions.sh"
    cp "$repo_dir/tests/nersc/"nodescript-{lund,clasdis}.sh "$campaign/scripts/"
    cp "$repo_dir/tests/nersc/full-task.sh" "$campaign/scripts/full-task.sh"
    cp "$repo_dir/nersc_io/container.sh" "$campaign/scripts/container.sh"
    cp "$repo_dir/tests/nersc/lund_files" "$campaign/lund_files"
    inputs=()
    while IFS= read -r input; do inputs+=("$input"); done \
        < <(sed '/^[[:space:]]*$/d' "$campaign/lund_files")
    (( ${#inputs[@]} > 0 )) || { echo 'No Lund inputs listed.' >&2; exit 2; }
    printf '%s\n%s\n' "$layout" "$image" > "$campaign/config"
    for (( i=0; i<100; i++ )); do
        printf 'bash %q %q %q %s lund %q %q\n' \
            "$campaign/scripts/full-task.sh" "$campaign" "$layout" "$((2*i))" \
            "$image" "${inputs[i % ${#inputs[@]}]}"
        printf 'bash %q %q %q %s clasdis %q\n' \
            "$campaign/scripts/full-task.sh" "$campaign" "$layout" "$((2*i+1))" "$image"
    done > "$campaign/tasks.txt"
else
    expected=$(printf '%s\n%s' "$layout" "$image")
    [[ "$(cat "$campaign/config")" == "$expected" ]] || {
        echo 'Resume requires the original layout and image.' >&2; exit 2;
    }
fi
printf 'Campaign: %s\nLayout: %s; 100 Lund + 100 clasdis jobs; 500 events each; THREADS=%s\n' \
    "$campaign" "$layout" "$THREADS"
[[ "${SIMGRID_FULL_PREPARE_ONLY:-0}" != 1 ]] || exit 0
command -v runcommands.sh >/dev/null || {
    echo 'Load the taskfarmer module before submitting.' >&2; exit 2;
}

farmer_pid=''
cleanup() {
    if [[ "$layout" == C ]]; then
        srun --overlap --nodes="$SLURM_NNODES" --ntasks="$SLURM_NNODES" \
            --ntasks-per-node=1 --cpus-per-task=1 --cpu-bind=none \
            bash "$campaign/scripts/full-task.sh" --cleanup || true
    fi
}
interrupt() {
    [[ -z "$farmer_pid" ]] || kill -TERM "$farmer_pid" 2>/dev/null || true
    exit 143
}
trap cleanup EXIT
trap interrupt TERM INT
cd "$campaign"
started=$(date +%s)
runcommands.sh tasks.txt &
farmer_pid=$!
rc=0
wait "$farmer_pid" || rc=$?
finished=$(date +%s)
completed=0
for status in jobs/*/exit-code; do
    [[ -f "$status" ]] || continue
    if [[ "$(cat "$status")" == 0 ]]; then completed=$((completed+1)); fi
done
printf 'Completed: %s/200; elapsed: %ss; allocated nodes: %s\n' \
    "$completed" "$((finished-started))" "$SLURM_NNODES"
(( completed == 200 )) || rc=1
exit "$rc"
