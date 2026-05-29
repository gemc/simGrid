def create_lund_or_generator(sconfiguration):
    """
    Generate the lund-file fetch or generator announcement section.

    For type-2 (lund-file) submissions: fetch the lund file from OSDF via
    pelican using the $lundFile argument passed to nodescript.sh.

    For type-1 (generator) submissions where the generator is 'gemc': print
    the internal-generator announcement with the genOptions embedded.

    Args:
        sconfiguration: SConfiguration instance.

    Returns:
        str: bash snippet for nodescript.sh.
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
        return (
            "\n"
            "echo 'GEMC internal generator — options passed to run_gemc'\n"
        )

    return (
        '\nrun_timed run_generator "{mcgenv}" "{generator}" "{genoptions}" "{nevents}"\n'
    ).format(
        generator=sconfiguration.generator or "",
        nevents=sconfiguration.nevents or "0",
        mcgenv=sconfiguration.mcgenv or "latest",
        genoptions=sconfiguration.genOptions or "",
    )
