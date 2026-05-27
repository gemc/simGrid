#!/bin/bash
# Returns a random background hipo file for the selected configuration
# and downloads it to the current directory via Pelican.
#
# Usage: bg_merge_bk_file.sh <configuration> <fields> <bkmerging> get
# Example: bg_merge_bk_file.sh rga_fall2018 tor+1.00_sol-1.00 40nA_10604MeV get
#
# Exit codes:
#   221  pelican ls failed or returned no files
#   223  random number out of range

set -euo pipefail

if [[ $# -lt 3 ]]; then
    echo "Usage: $0 <configuration> <fields> <bkmerging> [get]"
    exit 1
fi

configuration=$1
fields=$2
bkmerging=$3
getit=${4:-}

echo "Setting Pelican env variables"
echo "_CONDOR_CREDS: $_CONDOR_CREDS"
export BEARER_TOKEN_FILE="$_CONDOR_CREDS/jlab_clas12.use"
echo "BEARER_TOKEN_FILE: $BEARER_TOKEN_FILE"
echo "pelican: $(which pelican)"

xdir="osdf:///jlab-osdf/clas12/osgpool/backgroundfiles/${configuration}/${fields}/${bkmerging}/10k"

echo "Executing: pelican object ls $xdir"
ls_output=$(pelican object ls "$xdir") || {
    echo "pelican object ls failed for $xdir"
    exit 221
}

NFILES=$(echo "$ls_output" | wc -l)
if [[ $NFILES -eq 0 ]]; then
    echo "No files found at $xdir — exiting"
    exit 221
fi

R=$(( RANDOM % NFILES + 1 ))
if [[ $R -lt 1 || $R -gt $NFILES ]]; then
    echo "Random index out of range: $R (NFILES=$NFILES)"
    exit 223
fi

bgfile="${xdir}/$(printf '%05d' "$R").hipo"
echo "Selected background file: $bgfile"

if [[ "$getit" == "get" ]]; then
    echo "Executing: pelican object get $bgfile ."
    pelican object get "$bgfile" .
fi
