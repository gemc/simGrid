def create_requirements(scard, target_site=None):
	"""
	Generate the HTCondor Requirements expression for OSG execution slots.

	Each term guards against a class of known infrastructure failures:

	HAS_SINGULARITY =?= true
	    The slot must support Singularity containers. Without this the
	    CLAS12 container cannot be launched at all.

	HAS_CVMFS_jlab_opensciencegrid_org =?= true
	    The slot must have the JLab CVMFS repository mounted.

	OSG_HOST_KERNEL_VERSION >= 21700
	    Requires kernel 2.17+ (encoded as integer major*10000+minor*100).
	    Older kernels lack the namespace features needed by user-space
	    Singularity.

	OSG_GLIDEIN_VERSION >= 534
	    Minimum OSG pilot (glidein) version. Earlier pilots have known
	    bugs affecting file transfer and environment setup.

	TARGET attributes
	    Require an X86_64 Linux slot with sufficient disk and memory and
	    file-transfer support.

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
Requirements = ((HAS_SINGULARITY =?= true) && \\
               (HAS_CVMFS_jlab_opensciencegrid_org =?= true) && \\
               (OSG_HOST_KERNEL_VERSION >= 21700) && \\
               (OSG_GLIDEIN_VERSION >= 534)) && \\
               (TARGET.Arch == "X86_64") && \\
               (TARGET.OpSys == "LINUX") && \\
               (TARGET.Disk >= RequestDisk) && \\
               (TARGET.Memory >= RequestMemory) && \\
               (TARGET.HasFileTransfer){0}

""".format(site_clause)
