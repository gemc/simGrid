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
    local file

    # Resolve sources to absolute paths, including standalone calls with ./nodescript.sh.
    [[ "$nodescript" == /* ]] || nodescript="$PWD/$nodescript"
    [[ "$functions_file" == /* ]] || functions_file="$PWD/$functions_file"
    for file in "$nodescript" "$functions_file"; do
        if [[ ! -f "$file" || ! -r "$file" ]]; then
            printf 'Required script is not readable: %s\n' "$file" >&2
            return 2
        fi
    done

    # Stage the worker scripts into the working directory, exactly as HTCondor does on OSG, instead
    # of bind-mounting them: copy functions.sh and the node script next to the job's output. The
    # atomic temp+mv keeps concurrent array tasks from reading a half-written file. The working
    # directory lives on $SCRATCH, which podman-hpc mounts into the container automatically.
    local ns_base
    ns_base=$(basename "$nodescript")
    cp -f "$functions_file" "$PWD/.stage.$$.functions" \
        && mv -f "$PWD/.stage.$$.functions" "$PWD/functions.sh" \
        || { printf 'Failed to stage functions.sh into %s\n' "$PWD" >&2; return 2; }
    cp -f "$nodescript" "$PWD/.stage.$$.$ns_base" \
        && mv -f "$PWD/.stage.$$.$ns_base" "$PWD/$ns_base" \
        || { printf 'Failed to stage %s into %s\n' "$ns_base" "$PWD" >&2; return 2; }

    printf 'Compute host: %s\n' "$(hostname)"
    printf 'Container image: %s\n' "$image"
    printf 'Node script: %s\n' "$PWD/$ns_base"

    # podman-hpc auto-mounts the NERSC filesystems ($HOME, $SCRATCH, /global/cfs), so the only
    # explicit mounts are CVMFS and the ssh keys the token script expects at /sshkeys. Forward
    # scheduler/storage metadata and leave the image's software environment intact.
    local -a cmd=(
        podman-hpc run --rm --pull=never
        --workdir "$PWD"
        --env 'SLURM_*'
        --env SCRATCH
        --env SIMGRID_FUNCTIONS_FILE="${PWD}/functions.sh"
        --env SIMGRID_BACKEND=nersc
        --entrypoint /bin/bash
    )

    # Mount CVMFS at the same path when the JLab repository is available on the host, so the
    # container resolves /cvmfs/jlab.opensciencegrid.org (gemc config, geometry, fields, modules).
    if [[ -d /cvmfs/jlab.opensciencegrid.org ]]; then
        cmd+=(--volume /cvmfs:/cvmfs:ro)
    else
        printf 'Warning: /cvmfs/jlab.opensciencegrid.org not found on %s; /cvmfs not mounted\n' \
            "$(hostname)" >&2
    fi

    # Mount the host ssh keys so node scripts can renew an OSDF bearer token with token-renew.zsh.
    if [[ -d "$HOME/.ssh" ]]; then
        cmd+=(--volume "$HOME/.ssh:/sshkeys:ro")
    fi

    cmd+=("$image" -l "$PWD/$ns_base" "$@")
    "${cmd[@]}"
}
