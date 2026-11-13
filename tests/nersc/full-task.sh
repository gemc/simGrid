#!/bin/bash
# One TaskFarmer command; all physics runs in the existing NERSC node scripts.
set -euo pipefail
container_name="simgrid-full-${SLURM_JOB_ID:?}-$(hostname -s)"
if [[ "${1:-}" == --cleanup ]]; then
    if podman-hpc container exists "$container_name"; then
        podman-hpc stop --time 10 "$container_name"
    fi
    exit 0
fi
campaign="${1:?}"
layout="${2:?}"
task_id="${3:?}"
workflow="${4:?}"
image="${5:?}"
case "$layout" in B|C) ;; *) exit 2 ;; esac
case "$workflow" in lund|clasdis) ;; *) exit 2 ;; esac
[[ "$task_id" =~ ^[0-9]+$ ]] || exit 2
task_dir="$campaign/jobs/$task_id"
mkdir -p "$task_dir"
exec >> "$task_dir/task.out" 2>> "$task_dir/task.err"
cd "$task_dir"
started=$(date +%s)
record_result() {
    rc=$?
    printf '%s\n' "$rc" > exit-code
    printf 'Task %s: workflow=%s layout=%s exit=%s elapsed=%ss\n' \
        "$task_id" "$workflow" "$layout" "$rc" "$(( $(date +%s)-started ))"
}
trap record_result EXIT
export SIMGRID_TASK_ID="$task_id" SIMGRID_TASK_SEED="$((100000+task_id))"
export SIMGRID_FUNCTIONS_FILE="$campaign/scripts/functions.sh"
nodescript="$campaign/scripts/nodescript-$workflow.sh"
args=(500)
if [[ "$workflow" == lund ]]; then args+=("${6:?Expected Lund URI}"); fi

if [[ "$layout" == C ]]; then
    # Serialize startup and token renewal on each host, then release the lock before any physics.
    state="$campaign/containers/$(hostname -s)"
    mkdir -p "$state"
    exec 9> "${TMPDIR:-/tmp}/simgrid-full-${SLURM_JOB_ID}-${UID}.lock"
    flock 9
    if ! podman-hpc container exists "$container_name"; then
        cmd=(podman-hpc run --rm --pull=never --detach --name "$container_name"
            --volume "$campaign:$campaign" --volume /cvmfs:/cvmfs:ro
            --volume "$HOME/.ssh:/sshkeys:ro" --env 'SLURM_*' --env SCRATCH
            --env 'CLAS12_*' --env SIMGRID_BACKEND=nersc --entrypoint /bin/bash)
        "${cmd[@]}" "$image" -lc 'exec sleep infinity'
        # This marker belongs to this container instance, including after a campaign is resumed.
        rm -f "$state/token-ready"
    fi
    if [[ "$workflow" == lund && ! -f "$state/token-ready" ]]; then
        podman-hpc exec "$container_name" /bin/bash -lc '
            uid=$(id -u)
            export XDG_RUNTIME_DIR=/run/user/$uid BEARER_TOKEN_FILE=/var/run/user/$uid/bt_u$uid
            zsh /sshkeys/token-renew.zsh && test -s "$BEARER_TOKEN_FILE"
        '
        touch "$state/token-ready"
    fi
    flock -u 9
    exec 9>&-
    cmd=(podman-hpc exec --workdir "$task_dir"
        --env SIMGRID_FUNCTIONS_FILE="$SIMGRID_FUNCTIONS_FILE"
        --env SIMGRID_TASK_ID="$SIMGRID_TASK_ID" --env SIMGRID_TASK_SEED="$SIMGRID_TASK_SEED"
        --env SIMGRID_TOKEN_READY=1 "$container_name" /bin/bash -l "$nodescript" "${args[@]}")
else
    source "$campaign/scripts/container.sh"
    cmd=(run_nersc_container "$image" "$nodescript" "${args[@]}")
fi
rc=0
"${cmd[@]}" || rc=$?
exit "$rc"
