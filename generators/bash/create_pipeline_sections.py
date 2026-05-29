"""
create_pipeline_sections.py

Generators for the post-gemc simulation pipeline steps:
  merge_background, run_denoiser, run_reconstruction,
  test_hipo_file, create_dst, write_to_jlab.
"""


def create_merge_background(sconfiguration):
    """Emit run_timed merge_background only when bkmerging is requested."""
    if not sconfiguration.bkmerging or sconfiguration.bkmerging == 'no':
        return 'echo "Background merging not requested — skipping."\n'
    return '\nrun_timed merge_background\n'


def create_denoiser(sconfiguration, denoise_version):
    """Emit run_timed run_denoiser with version and the correct input file.

    Input is gemc.merged.hipo when background was merged, else gemc.hipo.
    """
    if sconfiguration.bkmerging and sconfiguration.bkmerging != 'no':
        input_file = "gemc.merged.hipo"
    else:
        input_file = "gemc.hipo"
    return '\nrun_timed run_denoiser "{denoise_version}" "{input_file}"\n'.format(
        denoise_version=denoise_version,
        input_file=input_file,
    )


def create_reconstruction(sconfiguration):
    """Emit run_timed run_reconstruction passing coatjava version and short yaml path."""
    coatjavav = sconfiguration.coatjavav or "latest"
    yaml_rel = "coatjava/{}/{}.yaml".format(
        coatjavav,
        sconfiguration.configuration or "default",
    )
    return '\nrun_timed run_reconstruction "{coatjavav}" "{yaml_rel}"\n'.format(
        coatjavav=coatjavav,
        yaml_rel=yaml_rel,
    )


def create_test_hipo(sconfiguration):
    """Emit run_timed test_hipo_file."""
    return '\nrun_timed test_hipo_file\n'


def create_dst_section(sconfiguration, user_submission_id):
    """Emit run_timed create_dst with the output filename prefix and literal submission ID.

    If dstOUT is not 'yes', emit an informational echo and set OUTPUT_FILE
    to recon.hipo so that write_to_jlab still has a target.
    """
    dst_prefix = (sconfiguration.string_id or "output").strip('-')
    if sconfiguration.dstOUT == 'yes':
        return '\nrun_timed create_dst "{dst_prefix}" "{submission_id}"\n'.format(
            dst_prefix=dst_prefix,
            submission_id=user_submission_id,
        )
    return (
        '\necho "DST not requested (dstOUT={dstOUT})."\n'
        'OUTPUT_FILE="recon.hipo"\n'
    ).format(dstOUT=sconfiguration.dstOUT or "no")


def create_write_to_jlab(sconfiguration, user_submission_id):
    """Emit run_timed write_to_jlab with username and literal submission ID."""
    username = sconfiguration.username or "unknown"
    return (
        '\nrun_timed write_to_jlab "{username}" "{submission_id}"\n'
    ).format(username=username, submission_id=user_submission_id)
