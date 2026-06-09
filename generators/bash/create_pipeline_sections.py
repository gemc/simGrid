"""
create_pipeline_sections.py

Generators for the post-gemc simulation pipeline steps:
  merge_background, run_denoiser, run_reconstruction,
  test_hipo_file, create_dst, write_to_jlab.

Each step emits its full command as a bash cmd=(...) array so the exact
invocation is visible and reproducible directly in nodescript.sh.
"""

_BG_MERGER_DETECTORS = 'DC,FTOF,ECAL,HTCC,LTCC,BST,BMT,CND,CTOF,FTCAL,FTHODO'


def _coatjava_at_least(version_str, threshold="16.0.0"):
    try:
        v = tuple(int(x) for x in str(version_str).split('.'))
        t = tuple(int(x) for x in threshold.split('.'))
        return v >= t
    except (ValueError, AttributeError):
        return False

_DST_BANKS = (
    'RUN::*,RAW::epics,RAW::scaler,HEL::flip,HEL::online,'
    'REC::*,RECFT::*,'
    'MC::RecMatch,MC::GenMatch,MC::Particle,MC::User,MC::Header,'
    'MC::Lund,MC::Event,'
    'RICH::Particle,RICH::Ring'
)


def create_merge_background(sconfiguration):
    """Emit the bg-merger cmd array and run_timed merge_background."""
    if not sconfiguration.bkmerging or sconfiguration.bkmerging == 'no':
        return 'echo "Background merging not requested — skipping."\n'
    coatjavav = sconfiguration.coatjavav or "latest"
    return (
        '\n# Background Merging\n'
        'echo "input: gemc.hipo + $BG_FILE, output: gemc.merged.hipo"\n'
        'module load coatjava/{coatjavav}'
        ' || {{ echo "ERROR: failed to load coatjava/{coatjavav}"; exit $EC_ENVIRONMENT; }}\n'
        'cmd=(bg-merger\n'
        '    -b "$BG_FILE"\n'
        '    -i gemc.hipo\n'
        '    -o gemc.merged.hipo\n'
        "    -d '{detectors}')\n"
        'echo "Running Background Merger: ${{cmd[@]}}"\n'
        'run_timed merge_background "${{cmd[@]}}"\n'
    ).format(coatjavav=coatjavav, detectors=_BG_MERGER_DETECTORS)


def create_denoiser(sconfiguration, denoise_version):
    """Emit the denoise2.exe cmd array and run_timed run_denoiser.

    Input is gemc.merged.hipo when background was merged, else gemc.hipo.
    The input file is removed after the denoiser runs.
    """
    if sconfiguration.bkmerging and sconfiguration.bkmerging != 'no':
        input_file = "gemc.merged.hipo"
    else:
        input_file = "gemc.hipo"
    return (
        '\n# Running Denoiser\n'
        'echo "input: {input_file}, output: gemc_denoised.hipo"\n'
        'module load denoise/{denoise_version}'
        ' || {{ echo "ERROR: failed to load denoise/{denoise_version}"; exit $EC_ENVIRONMENT; }}\n'
        'cmd=(denoise2.exe -i {input_file} -o gemc_denoised.hipo -t 1 -l 0.01)\n'
        'echo "Running Denoiser: ${{cmd[@]}}"\n'
        'run_timed run_denoiser "${{cmd[@]}}"\n'
        'rm -f {input_file}\n'
    ).format(denoise_version=denoise_version, input_file=input_file)


def create_reconstruction(sconfiguration):
    """Emit the recon-util cmd array and run_timed run_reconstruction."""
    coatjavav = sconfiguration.coatjavav or "latest"
    if _coatjava_at_least(coatjavav):
        yaml_stem = "mc-ai"
    else:
        yaml_stem = sconfiguration.configuration or "default"
    return (
        '\n# Running Reconstruction\n'
        'echo "input: gemc_denoised.hipo, output: recon.hipo"\n'
        '# denoise auto-loads hipo; unload denoise first so hipo has no dependents,\n'
        '# then unload hipo and coatjava cleanly before reloading coatjava.\n'
        'module unload denoise\n'
        'module unload hipo\n'
        'module unload coatjava\n'
        'module load coatjava/{coatjavav}'
        ' || {{ echo "ERROR: failed to load coatjava/{coatjavav}"; exit $EC_ENVIRONMENT; }}\n'
        'yaml="${{CLAS12_CONFIG}}/coatjava/{coatjavav}/{yaml_stem}.yaml"\n'
        'cmd=(recon-util\n'
        '    -y "$yaml"\n'
        '    -i gemc_denoised.hipo\n'
        '    -o recon.hipo\n'
        '    -- -Xmx1920m)\n'
        'echo "Running Reconstruction: ${{cmd[@]}}"\n'
        'run_timed run_reconstruction "${{cmd[@]}}"\n'
        'rm -f gemc_denoised.hipo\n'
    ).format(coatjavav=coatjavav, yaml_stem=yaml_stem)


def create_test_hipo(sconfiguration):
    """Emit the hipo-utils integrity-test cmd array and run_timed test_hipo_file."""
    return (
        '\necho "input: recon.hipo"\n'
        'cmd=(hipo-utils -test recon.hipo)\n'
        'echo "Running HIPO Integrity Test: ${cmd[@]}"\n'
        'run_timed test_hipo_file "${cmd[@]}"\n'
    )


def _sanitize_runs(runs_str):
    """Convert a 'runs' scard value to a filename-safe segment. '18300, 18301' -> '18300-18301'"""
    if not runs_str:
        return ""
    return "-".join(r.strip() for r in runs_str.split(',') if r.strip())


def _output_filename_pattern(sconfiguration, user_submission_id):
    """Return the output filename pattern with bash-variable placeholders for runtime parts.

    Type-1 (generator):           <string_id>-<submission_id>-$sjob.hipo
    Type-1 with runs:             <string_id>-<runno>-<submission_id>-$sjob.hipo
    Type-2 (lund):                <string_id>-$lund_base-<submission_id>-$sjob.hipo
    Type-2 with runs:             <string_id>-$lund_base-<runno>-<submission_id>-$sjob.hipo
    """
    string_id = (sconfiguration.string_id or "output").strip('-')
    runno = _sanitize_runs(sconfiguration.runs)
    if sconfiguration.type == '2':
        if runno:
            return "{}-$lund_base-{}-{}-$sjob.hipo".format(string_id, runno, user_submission_id)
        return "{}-$lund_base-{}-$sjob.hipo".format(string_id, user_submission_id)
    if runno:
        return "{}-{}-{}-$sjob.hipo".format(string_id, runno, user_submission_id)
    return "{}-{}-$sjob.hipo".format(string_id, user_submission_id)


def create_dst_section(sconfiguration, user_submission_id):
    """Emit the hipo-utils filter cmd array and run_timed create_dst, or rename
    recon.hipo directly for the no-DST case.
    """
    string_id   = (sconfiguration.string_id or "output").strip('-')
    output_file = _output_filename_pattern(sconfiguration, user_submission_id)

    if sconfiguration.dstOUT == 'yes':
        return (
            '\necho "input: recon.hipo, output: {output_file}"\n'
            "DST_BANKS='{dst_banks}'\n"
            'cmd=(hipo-utils -filter -b "$DST_BANKS" -merge -o dst.hipo recon.hipo)\n'
            'echo "Running DST Filter: ${{cmd[@]}}"\n'
            'run_timed create_dst "{string_id}" "{submission_id}" "$sjob" "${{cmd[@]}}"\n'
        ).format(
            output_file=output_file,
            dst_banks=_DST_BANKS,
            string_id=string_id,
            submission_id=user_submission_id,
        )

    return (
        '\necho "input: recon.hipo, output: {output_file}"\n'
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
    username    = sconfiguration.username or "unknown"
    string_id   = (sconfiguration.string_id or "output").strip('-')
    output_file = _output_filename_pattern(sconfiguration, user_submission_id)
    destination = "osdf:///jlab-osdf/clas12/volatile/osg/{}/{}/{}".format(
        username, user_submission_id, output_file
    )
    return (
        '\necho "input: {output_file}, output: {destination}"\n'
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
