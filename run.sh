#!/bin/bash
# SimGrid: container entry point, executed by HTCondor on each worker node.
#
# Arguments:
#   1. FarmSubmissionID  — DB user_submission_id for this batch
#   2. sjob              — subjob index (HTCondor $(Process), 0-based)
#   3. lundFile          — (optional) lund file path for type-2 submissions

set -euo pipefail

if [[ $# -lt 2 ]]; then
    echo "Usage: $0 <FarmSubmissionID> <sjob> [lundFile]"
    exit 1
fi

FarmSubmissionID=$1
sjob=$2
lundFile=${3:-}

nodeScript="nodeScript.sh"
outDir="output"

mkdir -p "$outDir"
cp -- * "$outDir/"
cd "$outDir"

echo
echo "Running inside $(pwd)"
echo "Directory content at start:"
ls -l
echo

chmod +x "$nodeScript"

if [[ -n "$lundFile" ]]; then
    echo "Running nodeScript: FarmSubmissionID=$FarmSubmissionID lundFile=$lundFile sjob=$sjob"
    ./"$nodeScript" "$FarmSubmissionID" "$lundFile" "$sjob"
else
    echo "Running nodeScript: FarmSubmissionID=$FarmSubmissionID sjob=$sjob"
    ./"$nodeScript" "$FarmSubmissionID" "$sjob"
fi
