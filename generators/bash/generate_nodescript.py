"""
generate_nodescript.py

Assemble nodescript.sh — the bash simulation script executed on the OSG
worker node — by calling each section generator in order.

Full pipeline (output_type != 1):
  1.  preamble                  — shebang, args, source functions.sh, define_exit_codes
  2.  setup_container_environment
  3.  setup_job_files
  4.  setup_pelican
  5.  fetch_background_file  (only when bkmerging is set)
  6.  lund_or_generator         — pelican fetch (type-2), gemc announcement, or run_generator
  7.  run_gemc
  8.  merge_background          (only when bkmerging is set)
  9.  run_denoiser
  10. run_reconstruction
  11. test_hipo_file
  12. create_dst                 (creates DST or sets OUTPUT_FILE=recon.hipo)
  13. write_to_jlab
  14. print_timing_summary

GEMC-only pipeline (output_type == 1):
  Steps 1–8 are identical; steps 9–12 are replaced by a single rename of the
  gemc output file (gemc.merged.hipo or gemc.hipo) to the output filename, then
  write_to_jlab uploads it directly — no denoising or reconstruction.
"""

import os

from generators.bash.create_preamble           import create_preamble
from generators.bash.create_lund_or_generator  import create_lund_or_generator
from generators.bash.create_run_gemc           import create_run_gemc
from generators.bash.create_pipeline_sections  import (
    create_merge_background,
    create_denoiser,
    create_reconstruction,
    create_test_hipo,
    create_dst_section,
    create_write_to_jlab,
    create_gemc_only_section,
)

NODESCRIPT      = "nodescript.sh"
FUNCTIONS_SH    = "functions.sh"
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
    gemc_only = str(sconfiguration.output_type or '').strip() == '1'

    sections = [
        create_preamble(sconfiguration, user_submission_id),

        'run_timed setup_container_environment "{username}" "{gemcv}" "{submission_type}"\n'.format(
            username=sconfiguration.username or "unknown",
            gemcv=sconfiguration.gemcv or "latest",
            submission_type=submission_type,
        ),

        'run_timed setup_job_files "{coatjavav}" "{gemcv}" "{configuration}"\n'.format(
            coatjavav=sconfiguration.coatjavav or "latest",
            gemcv=sconfiguration.gemcv or "latest",
            configuration=sconfiguration.configuration or "default",
        ),

        "run_timed setup_pelican\n",

        (
            '\n# $BG_FILE is a randomly selected background file, e.g. 00042.hipo\n'
            '# input: osdf:///jlab-osdf/clas12/osgpool/backgroundfiles'
            '/{configuration}/{fields}/{bkmerging}/10k/$BG_FILE, output: $BG_FILE\n'
            'run_timed fetch_background_file "{configuration}" "{fields}" "{bkmerging}"\n'
        ).format(
            configuration=sconfiguration.configuration or "",
            fields=sconfiguration.fields or "",
            bkmerging=sconfiguration.bkmerging or "",
        ) if sconfiguration.bkmerging and sconfiguration.bkmerging != 'no'
            else 'echo "Background merging not requested — skipping fetch."\n',

        create_lund_or_generator(sconfiguration),

        create_run_gemc(sconfiguration),

        create_merge_background(sconfiguration),
    ]

    if gemc_only:
        sections += [
            create_gemc_only_section(sconfiguration, user_submission_id),
            create_write_to_jlab(sconfiguration, user_submission_id),
        ]
    else:
        sections += [
            create_denoiser(sconfiguration, DENOISE_VERSION),
            create_reconstruction(sconfiguration),
            create_test_hipo(sconfiguration),
            create_dst_section(sconfiguration, user_submission_id),
            create_write_to_jlab(sconfiguration, user_submission_id),
        ]

    sections.append("\n\nprint_timing_summary\n")

    script = "".join(sections)

    with open(output_file, 'w') as f:
        f.write(script)
    os.chmod(output_file, 0o755)

    print("generate_nodescript: wrote {}".format(output_file))
    return output_file
