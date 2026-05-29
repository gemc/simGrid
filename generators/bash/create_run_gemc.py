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
    """Generate the run_timed run_gemc call for nodescript.sh.

    Args:
        sconfiguration: SConfiguration instance.

    Returns:
        str: bash snippet.
    """
    # Type-2 (lund-file) jobs often omit nevents; default to 5000.
    nevents       = sconfiguration.nevents or "5000"
    generator     = sconfiguration.generator or ""
    vertex_choice = sconfiguration.vertex_choice or "0"
    gcard = "gemc/{}/{}.gcard".format(
        sconfiguration.gemcv or "latest",
        sconfiguration.configuration or "default",
    )

    # Determine -INPUT_GEN_FILE value
    if sconfiguration.type == '2':
        input_gen_file = "lund, lund.dat"
    elif generator == 'gemc':
        input_gen_file = ""
    else:
        dat_file = generator + ".dat"
        input_gen_file = "lund, {}".format(dat_file)

    # Additional GEMC options for gemc-internal generator
    genoptions = ""
    if generator == 'gemc':
        raw = (sconfiguration.genOptions or "").strip()
        # Remove inter-option commas left by the old generator format, e.g.
        # -BEAM_P="...", -SPREAD_P  →  -BEAM_P="..." -SPREAD_P
        raw = _INTER_OPT_COMMA_RE.sub(r'\1 \2', raw)
        # Ensure double quotes are balanced (the DB value sometimes omits the
        # closing quote on the last option).
        if raw.count('"') % 2 != 0:
            raw += '"'
        # Normalise to single quotes so they can be safely embedded inside a
        # bash double-quoted argument without breaking shell quoting.
        genoptions = raw.replace('"', "'")

    zposition  = _vertex_value(sconfiguration.zposition, vertex_choice)
    beam_spot  = _vertex_value(sconfiguration.beam,      vertex_choice)
    raster     = _vertex_value(sconfiguration.raster,    vertex_choice)
    torus_scale    = sconfiguration.torus    or "1.00"
    solenoid_scale = sconfiguration.solenoid or "1.00"

    gemcv = sconfiguration.gemcv or "latest"

    return (
        '\nrun_timed run_gemc'
        ' "{gemcv}"'
        ' "{gcard}"'
        ' "{nevents}"'
        ' "{input_gen_file}"'
        ' "{genoptions}"'
        ' "{zposition}"'
        ' "{beam_spot}"'
        ' "{raster}"'
        ' "{torus_scale}"'
        ' "{solenoid_scale}"\n'
    ).format(
        gemcv=gemcv,
        gcard=gcard,
        nevents=nevents,
        input_gen_file=input_gen_file,
        genoptions=genoptions,
        zposition=zposition,
        beam_spot=beam_spot,
        raster=raster,
        torus_scale=torus_scale,
        solenoid_scale=solenoid_scale,
    )
