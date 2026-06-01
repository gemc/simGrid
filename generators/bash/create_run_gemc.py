import re

# Match a closing quote (single or double) followed by a comma that separates
# two GEMC options — an artifact of the old generator format.
_INTER_OPT_COMMA_RE = re.compile(r'(["\'])\s*,\s*(-)')


def _vertex_value(raw, vertex_choice):
    """Append ', reset ' when vertex_choice is '0' (default)."""
    if not raw or raw == 'n/a':
        return 'n/a'
    if (vertex_choice or '0') == '0':
        return raw + ', reset '
    return raw


def create_run_gemc(sconfiguration):
    """Generate the run_gemc section for nodescript.sh.

    Emits: module load, gcard env var, the full cmd array with every gemc
    argument, an echo of the command, and run_timed run_gemc "${cmd[@]}".
    This makes the exact command visible and reproducible in the nodescript.
    """
    nevents       = sconfiguration.nevents or "5000"
    generator     = sconfiguration.generator or ""
    vertex_choice = sconfiguration.vertex_choice or "0"
    configuration = sconfiguration.configuration or "default"
    gemcv         = sconfiguration.gemcv or "latest"

    # Determine input file and its label for the comment
    if sconfiguration.type == '2':
        input_gen_file = "lund, lund.dat"
        input_label    = "lund.dat"
    elif generator == 'gemc':
        input_gen_file = ""
        input_label    = "internal generator"
    else:
        dat_file       = generator + ".dat"
        input_gen_file = "lund, {}".format(dat_file)
        input_label    = dat_file

    # Additional GEMC options for gemc-internal generator
    genopts_args = []
    if generator == 'gemc':
        raw = (sconfiguration.genOptions or "").strip()
        raw = _INTER_OPT_COMMA_RE.sub(r'\1 \2', raw)
        if raw.count('"') % 2 != 0:
            raw += '"'
        raw = raw.replace('"', "'")
        if raw:
            import shlex
            for opt in shlex.split(raw):
                # Re-quote opts that contain spaces or commas
                if any(c in opt for c in ' ,'):
                    genopts_args.append('"{}"'.format(opt))
                else:
                    genopts_args.append(opt)

    zposition      = _vertex_value(sconfiguration.zposition, vertex_choice)
    beam_spot      = _vertex_value(sconfiguration.beam,      vertex_choice)
    raster         = _vertex_value(sconfiguration.raster,    vertex_choice)
    torus_scale    = sconfiguration.torus    or "1.00"
    solenoid_scale = sconfiguration.solenoid or "1.00"

    # Build the cmd array elements
    args = [
        'gemc',
        '-USE_GUI=0',
        '-NGENP=100',
        '-N={}'.format(nevents),
        '"$gcard"',
    ]

    if input_gen_file:
        args.append('"-INPUT_GEN_FILE={}"'.format(input_gen_file))

    args.extend(genopts_args)

    if zposition  != 'n/a':
        args.append('"-RANDOMIZE_LUND_VZ={}"'.format(zposition))
    if beam_spot  != 'n/a':
        args.append('"-BEAM_SPOT={}"'.format(beam_spot))
    if raster     != 'n/a':
        args.append('"-RASTER_VERTEX={}"'.format(raster))

    args.extend([
        '"-SCALE_FIELD=binary_torus,    {}"'.format(torus_scale),
        '"-SCALE_FIELD=binary_solenoid, {}"'.format(solenoid_scale),
        '"-OUTPUT=hipo, gemc.hipo"',
        '"-INTEGRATEDRAW=*"',
    ])

    cmd_body = ''.join('    {}\n'.format(a) for a in args)

    return (
        '\n# Running GEMC\n'
        '# input: {input_label}, output: gemc.hipo\n'
        'module load gemc/{gemcv}\n'
        'gcard="${{CLAS12_CONFIG}}/gemc/{gemcv}/{configuration}.gcard"\n'
    ).format(input_label=input_label, gemcv=gemcv, configuration=configuration) + (
        'cmd=(\n' + cmd_body + ')\n'
        'echo "Running GEMC: ${cmd[@]}"\n'
        'run_timed run_gemc "${cmd[@]}"\n'
    )
