"""
generate_nodescript.py

Assemble nodescript.sh — the bash simulation script executed on the OSG
worker node — by calling each section generator in order.

Section order:
  1. preamble          — shebang, args, source functions.sh,
                         define_exit_codes, container_environment
  2. job_parameters    — run_timed setup_job_parameters with scard values
  3. job_files         — run_timed setup_job_files (reads parameters above)
"""

import os

from generators.bash.create_preamble        import create_preamble
from generators.bash.create_job_parameters  import create_job_parameters

NODESCRIPT   = "nodescript.sh"
FUNCTIONS_SH = "functions.sh"


def generate_nodescript(sconfiguration, user_submission_id, test=False,
                        output_file=NODESCRIPT):
    """Write nodescript.sh and return the file path.

    Args:
        sconfiguration:      SConfiguration instance populated from the DB.
        user_submission_id:  int, DB user_submission_id for this batch.
        test:                bool, test mode flag passed from osg_submit.py.
        output_file:         str, destination path. Defaults to 'nodescript.sh'.

    Returns:
        str: path of the written file.
    """
    sections = [
        create_preamble(sconfiguration, user_submission_id),
        create_job_parameters(sconfiguration),
        "run_timed setup_container_environment\n",
        "run_timed setup_job_files\n",
        # print_timing_summary is always the last call — it summarises all
        # run_timed invocations that preceded it in the script.
        "\n\nprint_timing_summary\n",
    ]

    script = "".join(sections)

    with open(output_file, 'w') as f:
        f.write(script)
    os.chmod(output_file, 0o755)

    print("generate_nodescript: wrote {}".format(output_file))
    return output_file
