"""
generate_nodescript.py

Assemble nodescript.sh — the bash simulation script executed on the OSG
worker node — by calling each section generator in order.

Section order:
  1. preamble                   — shebang, args, source functions.sh, define_exit_codes
  2. setup_container_environment
  3. setup_job_files
  4. setup_pelican
  5. setup_background_merging  (only when bkmerging is set)
  6. lund_or_generator         — pelican fetch (type-2) or generator announcement (type-1/gemc)
"""

import os

from generators.bash.create_preamble           import create_preamble
from generators.bash.create_lund_or_generator import create_lund_or_generator

NODESCRIPT     = "nodescript.sh"
FUNCTIONS_SH   = "functions.sh"
DENOISE_VERSION = "4.2.3"


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
    submission_type = "dev" if sconfiguration.submission == "devel" else "prod"

    sections = [
        create_preamble(sconfiguration, user_submission_id),
        'setup_container_environment "{username}" "{denoise_version}" "{gemcv}"\n'.format(
            username=sconfiguration.username or "unknown",
            denoise_version=DENOISE_VERSION,
            gemcv=sconfiguration.gemcv or "latest",
        ),
        'setup_job_files "{submission_type}" "{coatjavav}" "{gemcv}" "{configuration}"\n'.format(
            submission_type=submission_type,
            coatjavav=sconfiguration.coatjavav or "latest",
            gemcv=sconfiguration.gemcv or "latest",
            configuration=sconfiguration.configuration or "default",
        ),
        "setup_pelican\n",
        'run_timed setup_background_merging "{configuration}" "{fields}" "{bkmerging}"\n'.format(
            configuration=sconfiguration.configuration or "",
            fields=sconfiguration.fields or "",
            bkmerging=sconfiguration.bkmerging or "",
        ) if sconfiguration.bkmerging
            else 'echo "Background merging not requested — skipping."\n',
        create_lund_or_generator(sconfiguration),
        "\n\nprint_timing_summary\n",
    ]

    script = "".join(sections)

    with open(output_file, 'w') as f:
        f.write(script)
    os.chmod(output_file, 0o755)

    print("generate_nodescript: wrote {}".format(output_file))
    return output_file
