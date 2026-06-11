def create_lund_or_generator(sconfiguration):
    """
    Generate the lund-file fetch or generator command section.

    For type-2 (lund-file) submissions: fetch the lund file from OSDF via pelican.
    For type-1 with gemc internal generator: options are embedded in the run_gemc cmd.
    For type-1 with external generator: emit module load, seed setup, cmd array,
    echo, and run_timed so the exact command is visible and reproducible.
    """
    if sconfiguration.type == '2':
        return (
            "\n"
            'echo\n'
            'echo "Running pelican object get $lundFile lund.dat"\n'
            "pelican object get $lundFile lund.dat\n"
            'echo\n'
        )

    if sconfiguration.generator == 'gemc':
        return "\necho 'GEMC internal generator — options embedded in run_gemc cmd'\n"

    generator  = sconfiguration.generator or ""
    nevents    = sconfiguration.nevents or "0"
    genoptions = (sconfiguration.genOptions or "").replace('"', "'").strip()

    cmd_args = [generator, '--trig', nevents, '--docker']
    if genoptions:
        cmd_args.append(genoptions)
    cmd_args += ['--seed', '"$seed"']

    cmd_line = 'cmd=(' + ' '.join(cmd_args) + ')'

    return (
        '\n# Running Generator\n'
        'run_timed load_module "mcgen/{mcgenv}"\n'
        'generate-seeds.py generate\n'
        'seed=$(generate-seeds.py read --row 1)\n'
    ).format(mcgenv=sconfiguration.mcgenv or "latest") + (
        cmd_line + '\n'
        'echo "Running Generator: ${cmd[@]}"\n'
        'run_timed run_generator "${cmd[@]}"\n'
    )
