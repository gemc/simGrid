def create_requirements(scard):
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

	The commented-out Microarch block can be re-enabled to restrict jobs
	to x86_64-v2/v3/v4 micro-architecture levels for AVX-dependent code.

	Args:
		scard: SConfiguration instance (not used directly; included for
		       consistency with all other generator signatures). Slot
		       requirements are identical for type-1 and type-2 submissions.

	Returns:
		str: HTCondor Requirements line.
	"""
	return """# OSG slot requirements.
# To restrict to a specific x86_64 micro-architecture level uncomment:
# Requirements = (TARGET.Microarch =!= UNDEFINED) &&
#   (TARGET.Microarch =?= "x86_64-v2" || TARGET.Microarch =?= "x86_64-v3" || TARGET.Microarch =?= "x86_64-v4") &&
#   (HAS_SINGULARITY =?= TRUE) && ...
Requirements = (HAS_SINGULARITY =?= TRUE) && \\
               (HAS_CVMFS_oasis_opensciencegrid_org =?= True) && \\
               (OSG_HOST_KERNEL_VERSION >= 21700) && \\
               (CVMFS_oasis_opensciencegrid_org_REVISION >= 16688) && \\
               (OSG_GLIDEIN_VERSION >= 534)

"""
