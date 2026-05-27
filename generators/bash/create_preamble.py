def create_preamble(scard, user_submission_id):
    """
    Generate the nodescript.sh opening block.

    Includes shebang, argument documentation, set -euo pipefail,
    argument parsing, and the source + run_timed calls that every
    node script begins with.  The lundFile argument line is only
    emitted for type-2 (lund-file-based) submissions.

    Args:
        scard:               SConfiguration instance.
        user_submission_id:  int, DB user_submission_id for this batch.

    Returns:
        str: opening block of nodescript.sh.
    """
    lund_arg_doc = (
        "#   3. lundFile         — OSDF URI of the lund input file\n"
        if scard.type == '2' else ""
    )

    return """\
#!/bin/bash
# nodescript.sh — CLAS12 simulation script executed on the OSG worker node.
#
# Invoked by run.sh with:
#   ./nodescript.sh <FarmSubmissionID> <sjob> [lundFile]
#
# Arguments:
#   1. FarmSubmissionID — DB user_submission_id for this batch ({uid})
#   2. sjob             — subjob index (HTCondor $(Process), 0-based)
{lund_arg_doc}
set -euo pipefail

FarmSubmissionID=$1
sjob=$2
lundFile=${{3:-}}

# Source shared bash functions (run_timed, container_environment, define_exit_codes).
# shellcheck source=functions.sh
source functions.sh

run_timed define_exit_codes
run_timed container_environment
""".format(uid=user_submission_id, lund_arg_doc=lund_arg_doc)
