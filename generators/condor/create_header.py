# Site preference weights for the HTCondor Rank expression.
# Higher value = more preferred. Sites not listed get DEFAULT_SITE_RANK.
# To find which site a running job landed on:
#   condor_q -af ClusterId GLIDEIN_Site
#   condor_history <jobid> -af GLIDEIN_Site
SITE_RANKS = {
    'SGridGLA': 300,   # Glasgow — historically fast for CLAS12
    'CNAF':     200,   # INFN Tier-1 — reliable, good throughput
    'SU-ITS':   0,     # Syracuse — deprioritised, low throughput
}
DEFAULT_SITE_RANK = 100


def _build_rank_expression(site_ranks, default_rank):
    """Build a nested ClassAd ternary Rank expression from a site→rank dict."""
    expr = str(default_rank)
    for i, (site, rank) in enumerate(reversed(list(site_ranks.items()))):
        if i == 0:
            expr = "(GLIDEIN_SITE=?='{}') ? {} : {}".format(site, rank, expr)
        else:
            expr = "(GLIDEIN_SITE=?='{}') ? {} : ( {} )".format(site, rank, expr)
    return expr


def create_header(scard):
    """
    Generate the HTCondor submit file header block.

    Universe = vanilla is required for OSG pilot-based submissions.
    Other universes (grid, docker, parallel) are not used on the OSG.

    SingularityImage points to the CVMFS-hosted Jefferson Lab CLAS12 software
    container. The image tag is taken from scard.softwarev (e.g.
    "gemc/5.13 coatjava/10.0.7"). If softwarev is not set, 'production' is
    used as a safe default that maps to the latest stable release.

    SingularityBindCVMFS = True instructs the pilot to bind-mount the full
    /cvmfs namespace inside the container, making all CVMFS repositories
    (oasis, jlab, etc.) available to the job without extra configuration.

    Rank is a ClassAd expression built from SITE_RANKS (module-level dict).
    Edit SITE_RANKS to add, remove, or reprioritise sites without touching
    the submit-file template. Sites not in the dict get DEFAULT_SITE_RANK.

    Args:
        scard: SConfiguration instance. Uses scard.softwarev for the container
               tag. Applies identically to type-1 (generator) and type-2
               (lund-file) submissions — both run inside the same container.

    Returns:
        str: HTCondor header block ready to prepend to a submit file.
    """
    image_tag = scard.softwarev if scard.softwarev else "production"
    rank_expr = _build_rank_expression(SITE_RANKS, DEFAULT_SITE_RANK)

    return """# SimGrid HTCondor Submission Script
# --------------------------------------------------

# vanilla is the only universe supported for OSG pilot-based jobs.
Universe = vanilla

+SingularityImage     = "/cvmfs/singularity.opensciencegrid.org/jeffersonlab/clas12software:{0}"
+SingularityBindCVMFS = True

# Site ranking (higher = more preferred).
Rank = {1}

""".format(image_tag, rank_expr)
