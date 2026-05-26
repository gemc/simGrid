def create_authentication(scard):
	"""
	Generate the OAuth token configuration block for Pelican/OSDF access.

	use_oauth_services = jlab_clas12
	    Instructs the HTCondor starter to obtain an OAuth2 bearer token for
	    the 'jlab_clas12' service before the job runs. The token is injected
	    into the job environment as BEARER_TOKEN_FILE, which Pelican and
	    the OSDF client use to authenticate against the JLab data federation
	    for reading input lund files and writing output hipo files.

	    The token credential itself is managed by the submit-node's
	    CredMon daemon; the job only sees the short-lived token file.
	    No passwords or long-lived secrets are transferred to the node.

	Args:
		scard: SConfiguration instance (not used directly; included for
		       consistency with all other generator signatures). OAuth token
		       provisioning is required for both types: type-1 jobs write
		       output hipo files via Pelican; type-2 jobs additionally read
		       lund files from OSDF via Pelican on the worker node.

	Returns:
		str: HTCondor OAuth services block.
	"""
	return """# Pelican / OSDF authentication token.
# The CredMon on the submit node provisions a short-lived OAuth2 token
# for jlab_clas12 and injects it via BEARER_TOKEN_FILE into the job.
use_oauth_services = jlab_clas12

"""
