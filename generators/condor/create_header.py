def create_header(scard):
	"""
	Generate the HTCondor submit file header block.

	Sets Universe to 'vanilla', which is required for OSG grid submissions
	(as opposed to 'grid' or 'docker' universes).

	SingularityImage points to the CVMFS-hosted Jefferson Lab CLAS12 software
	container. The image tag is taken from scard.softwarev (e.g.
	"gemc/5.13 coatjava/10.0.7"). If softwarev is not set, 'production' is
	used as a safe default that maps to the latest stable release.

	SingularityBindCVMFS = True instructs the pilot to bind-mount the full
	/cvmfs namespace inside the container, making all CVMFS repositories
	(oasis, jlab, etc.) available to the job without extra configuration.

	Rank is a ClassAd expression that tells HTCondor which sites to prefer
	when placing jobs:
	  - SGridGLA (Glasgow)  → priority 300  (historically fast for CLAS12)
	  - CNAF / Lamar        → priority 200  (reliable, good throughput)
	  - SU-ITS              → priority   0  (deprioritised, low throughput)
	  - all others          → priority 100  (neutral)

	Args:
		scard: SConfiguration instance. Uses scard.softwarev for the container
		       tag. Applies identically to type-1 (generator) and type-2
		       (lund-file) submissions — both run inside the same container.

	Returns:
		str: HTCondor header block ready to prepend to a submit file.
	"""
	image_tag = scard.softwarev if scard.softwarev else "production"

	return """# SimGrid HTCondor Submission Script
# --------------------------------------------------

Universe = vanilla

# Singularity container pulled from CVMFS.
# Image tag comes from scard.softwarev; defaults to 'production' if unset.
+SingularityImage     = "/cvmfs/singularity.opensciencegrid.org/jeffersonlab/clas12software:{0}"
+SingularityBindCVMFS = True

# Site ranking expression (higher = more preferred).
# SGridGLA=300, CNAF/Lamar=200, neutral=100, SU-ITS=0.
Rank = (GLIDEIN_SITE=?='SGridGLA') ? 300 : ( ( (GLIDEIN_SITE=?='CNAF') || (GLIDEIN_SITE=?='Lamar-Cluster') ) ? 200 : ( (GLIDEIN_SITE=?='SU-ITS') ? 0 : 100) )

""".format(image_tag)
