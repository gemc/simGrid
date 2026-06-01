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
    return '\n# input: gemc.hipo + $BG_FILE, output: gemc.merged.hipo\nrun_timed merge_background\n'


def create_denoiser(sconfiguration, denoise_version):
    """Emit run_timed run_denoiser with version and the correct input file.

    Input is gemc.merged.hipo when background was merged, else gemc.hipo.
    """
    if sconfiguration.bkmerging and sconfiguration.bkmerging != 'no':
        input_file = "gemc.merged.hipo"
    else:
        input_file = "gemc.hipo"
    return (
        '\n# input: {input_file}, output: gemc_denoised.hipo\n'
        'run_timed run_denoiser "{denoise_version}" "{input_file}"\n'
    ).format(denoise_version=denoise_version, input_file=input_file)


def create_reconstruction(sconfiguration):
    """Emit run_timed run_reconstruction passing coatjava version and short yaml path."""
    coatjavav = sconfiguration.coatjavav or "latest"
    yaml_rel = "coatjava/{}/{}.yaml".format(
        coatjavav,
        sconfiguration.configuration or "default",
    )
    return (
        '\n# input: gemc_denoised.hipo, output: recon.hipo\n'
        'run_timed run_reconstruction "{coatjavav}" "{yaml_rel}"\n'
    ).format(coatjavav=coatjavav, yaml_rel=yaml_rel)


def create_test_hipo(sconfiguration):
    """Emit run_timed test_hipo_file."""
    return '\n# input: recon.hipo\nrun_timed test_hipo_file\n'


def _output_filename_pattern(sconfiguration, user_submission_id):
    """Return the output filename pattern with bash-variable placeholders for runtime parts.

    Type-1 (generator): <string_id>-<submission_id>-$sjob.hipo
    Type-2 (lund):      <string_id>-$lund_base-<submission_id>-$sjob.hipo
    """
    string_id = (sconfiguration.string_id or "output").strip('-')
    if sconfiguration.type == '2':
        return "{}-$lund_base-{}-$sjob.hipo".format(string_id, user_submission_id)
    return "{}-{}-$sjob.hipo".format(string_id, user_submission_id)


def create_dst_section(sconfiguration, user_submission_id):
    """Emit create_dst (which calls get_output_filename internally), or rename
    recon.hipo for the no-DST case.
    """
    string_id = (sconfiguration.string_id or "output").strip('-')
    output_file = _output_filename_pattern(sconfiguration, user_submission_id)
    if sconfiguration.dstOUT == 'yes':
        return (
            '\n# input: recon.hipo, output: {output_file}\n'
            'run_timed create_dst "{string_id}" "{submission_id}" "$sjob"\n'
        ).format(output_file=output_file, string_id=string_id, submission_id=user_submission_id)
    return (
        '\n# input: recon.hipo, output: {output_file}\n'
        'get_output_filename "{string_id}" "{submission_id}" "$sjob"\n'
        'echo "DST not requested (dstOUT={dstOUT}) — renaming recon.hipo to $OUTPUT_FILE"\n'
        'mv recon.hipo "$OUTPUT_FILE"\n'
    ).format(
        output_file=output_file,
        string_id=string_id,
        submission_id=user_submission_id,
        dstOUT=sconfiguration.dstOUT or "no",
    )


def create_write_to_jlab(sconfiguration, user_submission_id):
    """Emit run_timed write_to_jlab with username, string_id, submission_id, sjob."""
    username = sconfiguration.username or "unknown"
    string_id = (sconfiguration.string_id or "output").strip('-')
    output_file = _output_filename_pattern(sconfiguration, user_submission_id)
    destination = "osdf:///jlab-osdf/clas12/volatile/osg/{}/{}/{}".format(
        username, user_submission_id, output_file
    )
    return (
        '\n# input: {output_file}, output: {destination}\n'
        'run_timed write_to_jlab "{username}" "{string_id}" "{submission_id}" "$sjob"\n'
    ).format(
        output_file=output_file,
        destination=destination,
        username=username,
        string_id=string_id,
        submission_id=user_submission_id,
    )


def create_gemc_only_section(sconfiguration, user_submission_id):
    """For GEMC-only output (output_type=1): rename the gemc file to the output filename.

    With background merging the source is gemc.merged.hipo; without it is gemc.hipo.
    write_to_jlab will then upload $OUTPUT_FILE directly.
    """
    string_id = (sconfiguration.string_id or "output").strip('-')
    if sconfiguration.bkmerging and sconfiguration.bkmerging != 'no':
        gemc_file = "gemc.merged.hipo"
    else:
        gemc_file = "gemc.hipo"
    return (
        '\nget_output_filename "{string_id}" "{submission_id}" "$sjob"\n'
        'echo "GEMC-only output: renaming {gemc_file} to $OUTPUT_FILE"\n'
        'mv "{gemc_file}" "$OUTPUT_FILE" || {{ echo "mv failed."; exit $EC_HIPO_UTILS; }}\n'
    ).format(
        string_id=string_id,
        submission_id=user_submission_id,
        gemc_file=gemc_file,
    )
