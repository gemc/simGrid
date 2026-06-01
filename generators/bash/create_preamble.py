def create_preamble(sconfiguration, user_submission_id):
    """
    Generate the nodescript.sh opening block.

    Includes shebang, argument documentation, set -euo pipefail,
    argument parsing, and the source + initial run_timed calls.
    The lundFile argument line is only emitted for type-2 submissions.

    Args:
        sconfiguration:      SConfiguration instance.
        user_submission_id:  int, DB user_submission_id for this batch.

    Returns:
        str: opening block of nodescript.sh.
    """
    if sconfiguration.type == '2':
        arg_invocation = "./nodescript.sh <sjob> <lundFile>"
        arg_doc        = (
            "#   1. sjob             — subjob index (HTCondor $(Process), 0-based)\n"
            "#   2. lundFile         — OSDF URI of the lund input file\n"
        )
        arg_parse = (
            'sjob=$1\n'
            'lundFile=$2\n'
            'lund_base="${lundFile##*/}"\n'
            'lund_base="${lund_base%.*}"\n'
            '# lund_base is the lund filename without path or extension (e.g. lund1 from osdf://.../lund1.dat)\n'
        )
    else:
        arg_invocation = "./nodescript.sh <sjob>"
        arg_doc        = "#   1. sjob             — subjob index (HTCondor $(Process), 0-based)\n"
        arg_parse      = "sjob=$1\n"

    return """\
#!/bin/bash
# nodescript.sh — CLAS12 simulation script executed on the OSG worker node.
# Submission ID: {uid}
#
# Invoked directly by HTCondor:
#   {arg_invocation}
#
# Arguments:
{arg_doc}
set -euo pipefail

{arg_parse}
# Create the output directory, copy all staged files into it, and run there
# so every output file lands where HTCondor's transfer_output_files expects it.
mkdir -p output
{{ cp -- * output/ 2>/dev/null; }} || true
cd output

# Source shared bash functions (run_timed, container_environment, define_exit_codes).
# shellcheck source=functions.sh
source functions.sh

define_exit_codes
""".format(uid=user_submission_id, arg_invocation=arg_invocation,
           arg_doc=arg_doc, arg_parse=arg_parse)
