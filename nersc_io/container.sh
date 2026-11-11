#!/bin/bash
# Host-side container launcher for NERSC batch jobs and login-node diagnostics.
# Source this file, then call run_nersc_container <image> <nodescript> [args...].

run_nersc_container() {
    if [[ $# -lt 2 ]]; then
        printf 'Usage: run_nersc_container <image> <nodescript> [args...]\n' >&2
        return 2
    fi

    local image="$1"
    local nodescript="$2"
    shift 2
    local functions_file="${SIMGRID_FUNCTIONS_FILE:-$HOME/software/simgrid/main/generators/bash/functions.sh}"
    local config_dir="${SIMGRID_CONFIG_DIR:-}"
    local file

    # Bind sources must be absolute, including for standalone calls with ./nodescript.sh.
    [[ "$nodescript" == /* ]] || nodescript="$PWD/$nodescript"
    [[ "$functions_file" == /* ]] || functions_file="$PWD/$functions_file"
    for file in "$nodescript" "$functions_file"; do
        if [[ ! -f "$file" || ! -r "$file" ]]; then
            printf 'Required script is not readable: %s\n' "$file" >&2
            return 2
        fi
    done

    printf 'Compute host: %s\n' "$(hostname)"
    printf 'Container image: %s\n' "$image"
    printf 'Node script: %s\n' "$nodescript"

    # Images must already be pulled/migrated. Keep job commands in the mounted nodescript.
    # Forward only scheduler/storage metadata, leaving the image's software environment intact.
    local -a cmd=(
        podman-hpc run --rm --pull=never
        --volume "${PWD}:${PWD}"
        --volume "${functions_file}:/opt/simgrid/functions.sh:ro"
        --volume "${nodescript}:/opt/simgrid/nodescript.sh:ro"
        --workdir "$PWD"
        --env 'SLURM_*'
        --env SCRATCH
        --env SIMGRID_FUNCTIONS_FILE=/opt/simgrid/functions.sh
        --env SIMGRID_BACKEND=nersc
        --entrypoint /bin/bash
    )

    # Mount the host ssh keys so node scripts can renew an OSDF bearer token with token-renew.zsh.
    if [[ -d "$HOME/.ssh" ]]; then
        cmd+=(--volume "$HOME/.ssh:/sshkeys:ro")
    fi

    if [[ -n "$config_dir" ]]; then
        [[ "$config_dir" == /* ]] || config_dir="$PWD/$config_dir"
        if [[ ! -d "$config_dir" || ! -r "$config_dir" || ! -x "$config_dir" ]]; then
            printf 'Configuration directory is not accessible: %s\n' "$config_dir" >&2
            return 2
        fi
        cmd+=(--group-add keep-groups --volume "${config_dir}:${config_dir}:ro")
    fi
    cmd+=("$image" -l /opt/simgrid/nodescript.sh "$@")
    "${cmd[@]}"
}
