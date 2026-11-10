#!/bin/bash
# Pelican transfer trial executed inside the NERSC container: list the test area, fetch the
# template dis.dat, then upload a copy under the first unused dis<N>.dat slot.
#
# Requires a valid bearer token for osdf://jlab-osdf (e.g. obtained with nersc_io/token-renew.zsh);
# without it the get and put operations fail authorization.
set -euo pipefail

source "${SIMGRID_FUNCTIONS_FILE:-functions.sh}"
define_exit_codes

base="osdf://jlab-osdf/clas12/volatile/osg/ungaro/test"

run_timed require_executable pelican

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
