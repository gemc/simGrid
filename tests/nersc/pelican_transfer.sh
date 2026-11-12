#!/bin/bash
# Pelican transfer trial executed inside the NERSC container: list the test area, fetch the
# template dis.dat, then upload a copy under the first unused dis<N>.dat slot.
#
# It renews an osdf://jlab-osdf bearer token in-container with token-renew.zsh before transferring.
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

base="osdf://jlab-osdf/clas12/volatile/osg/ungaro/test"

run_timed require_executable pelican

# Obtain an OSDF bearer token before any transfer; token-renew.zsh (mounted from the host .ssh at
# /sshkeys) writes it to $BEARER_TOKEN_FILE using the gemc ssh key.
uid=$(id -u)
export XDG_RUNTIME_DIR="/run/user/$uid"
export BEARER_TOKEN_FILE="/var/run/user/$uid/bt_u$uid"
echo "Running token-renew: zsh /sshkeys/token-renew.zsh"
run_timed zsh /sshkeys/token-renew.zsh
if [[ ! -s "$BEARER_TOKEN_FILE" ]]; then
    echo "token-renew did not produce a bearer token at $BEARER_TOKEN_FILE" >&2
    exit "$EC_INFRASTRUCTURE"
fi

# input: remote test directory, output: listing captured for slot selection
cmd=(pelican object ls "$base")
echo "Running pelican ls: ${cmd[@]}"
listing=$("${cmd[@]}")
printf '%s\n' "$listing"

# input: remote dis.dat, output: ./dis.dat template to re-upload
cmd=(pelican object get "$base/dis.dat")
echo "Running pelican get: ${cmd[@]}"
run_timed "${cmd[@]}"
if [[ ! -s dis.dat ]]; then
    echo "pelican get did not produce a nonempty dis.dat" >&2
    exit "$EC_FILE_DOES_NOT_EXIST"
fi

# Count existing dis<N>.dat (tolerating an optional underscore) and pick the first unused number.
existing=$(printf '%s\n' "$listing" | grep -oE 'dis_?[0-9]+\.dat' | grep -oE '[0-9]+' | sort -n -u || true)
n=1
while printf '%s\n' "$existing" | grep -qx "$n"; do
    n=$((n + 1))
done
echo "Existing dis numbers: $(printf '%s ' ${existing:-none})"
echo "First available number: $n"

# input: ./dis.dat, output: remote dis<N>.dat
target="$base/dis${n}.dat"
cmd=(pelican object put dis.dat "$target")
echo "Running pelican put: ${cmd[@]}"
run_timed "${cmd[@]}"

echo "Uploaded dis.dat to $target"
print_timing_summary
