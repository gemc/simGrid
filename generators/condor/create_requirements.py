def create_requirements(scard, target_site=None):
	"""
	Generate the HTCondor Requirements expression for OSG execution slots.

	Each term guards against a class of known infrastructure failures:

	HAS_SINGULARITY =?= TRUE
	    The slot must support Singularity containers. Without this the
	    CLAS12 container cannot be launched at all.

	HAS_CVMFS_oasis_opensciencegrid_org =?= True
	    The slot must have the OSG CVMFS oasis repository mounted. This is
	    where the Singularity image catalogue lives.

	OSG_HOST_KERNEL_VERSION >= 21700
	    Requires kernel 2.17+ (encoded as integer major*10000+minor*100).
	    Older kernels lack the namespace features needed by user-space
	    Singularity.

	CVMFS_oasis_opensciencegrid_org_REVISION >= 16688
	    Ensures the CVMFS oasis repository is sufficiently up to date so
	    that the requested clas12software image tag exists on the site.

	OSG_GLIDEIN_VERSION >= 534
	    Minimum OSG pilot (glidein) version. Earlier pilots have known
	    bugs affecting file transfer and environment setup.

	Args:
		scard:       SConfiguration instance (not used directly; included for
		             consistency with all other generator signatures). Slot
		             requirements are identical for type-1 and type-2 submissions.
		target_site: str, GLIDEIN_Site name to pin jobs to a single site
		             (e.g. "CNAF"). None means no site restriction.

	Returns:
		str: HTCondor Requirements line.
	"""
	site_clause = (
		' && \\\n               (GLIDEIN_Site == "{}")'.format(target_site)
		if target_site else ""
	)

	return """# OSG slot requirements.
Requirements = (HAS_SINGULARITY =?= TRUE) && \\
               (HAS_CVMFS_oasis_opensciencegrid_org =?= True) && \\
               (OSG_HOST_KERNEL_VERSION >= 21700) && \\
               (CVMFS_oasis_opensciencegrid_org_REVISION >= 16688) && \\
               (OSG_GLIDEIN_VERSION >= 534){0}

""".format(site_clause)
