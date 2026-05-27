"""
generate_nodescript.py

Assemble nodescript.sh — the bash simulation script executed on the OSG
worker node — by calling each section generator in order.

Section order:
  1. preamble                   — shebang, args, source functions.sh, define_exit_codes
  2. job_parameters             — setup_job_parameters with scard values
  3. setup_container_environment
  4. setup_job_files
  5. setup_pelican
  6. setup_background_merging  (only when bkmerging is set)
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
        "setup_container_environment\n",
        "setup_job_files\n",
        "setup_pelican\n",
        (
            '\necho "setup_background_merging: /{configuration}/{fields}/{bkmerging}"\n'
            "run_timed setup_background_merging\n"
        ).format(
            configuration=sconfiguration.configuration or "",
            fields=sconfiguration.fields or "",
            bkmerging=sconfiguration.bkmerging or "",
        ) if sconfiguration.bkmerging
            else 'echo "Background merging not requested — skipping."\n',
        "\n\nprint_timing_summary\n",
    ]

    script = "".join(sections)

    with open(output_file, 'w') as f:
        f.write(script)
    os.chmod(output_file, 0o755)

    print("generate_nodescript: wrote {}".format(output_file))
    return output_file
