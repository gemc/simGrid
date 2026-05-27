def create_job_parameters(sconfiguration):
    """
    Generate the run_timed call for setup_job_parameters.

    Embeds submission type, software versions, and detector configuration
    from the sconfiguration as positional arguments so setup_job_parameters
    (defined in functions.sh) can export them for downstream functions.

    Args:
        sconfiguration: SConfiguration instance.

    Returns:
        str: run_timed line for nodescript.sh.
    """
    submission_type = "dev" if sconfiguration.submission == "devel" else "prod"

    return 'run_timed setup_job_parameters "{submission_type}" "{coatjavav}" "{gemcv}" "{configuration}"\n'.format(
        submission_type=submission_type,
        coatjavav=sconfiguration.coatjavav or "latest",
        gemcv=sconfiguration.gemcv or "latest",
        configuration=sconfiguration.configuration or "default",
    )
