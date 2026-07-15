# Default list of sites excluded from job placement.
# GLIDEIN_Site names are comma-separated with NO spaces (site names may
# contain spaces themselves, so the separator must be unambiguous).
#
# Sites end up on this list for reasons such as:
#   - Persistent job failures or holds not caused by our code
#   - File-transfer failures due to local firewall / network policy
#   - Incompatible kernel / CVMFS configuration not caught by Requirements
#   - Temporary exclusion during known site outages
#
# To add or remove sites, edit DEFAULT_UNDESIRED_SITES.
# To build a custom list at runtime, pass undesired_sites to create_undesired().

DEFAULT_UNDESIRED_SITES = [
	"NMSU_DISCOVERY",
	"Clemson-Palmetto",
]


def create_undesired(scard, undesired_sites=None):
	"""
	Generate the +UNDESIRED_Sites ClassAd for HTCondor.

	HTCondor uses this attribute to steer the matchmaker away from listed
	sites. It is based on GLIDEIN_Site (not GLIDEIN_ResourceName), so site
	names must match exactly what the glidein advertises.

	The value must be a double-quoted, comma-separated string with NO spaces
	between entries. Spaces inside a site name are allowed (e.g.
	"San Diego Supercomputer Center"), but the comma separator itself must
	have no surrounding whitespace.

	Args:
		scard: SConfiguration instance (not used directly; included for
		       consistency with all other generator signatures). Site
		       exclusion applies equally to type-1 and type-2 submissions.
		undesired_sites: list of str site names to exclude. Defaults to
		                 DEFAULT_UNDESIRED_SITES when None.

	Returns:
		str: HTCondor +UNDESIRED_Sites line.
	"""
	sites = undesired_sites if undesired_sites is not None else DEFAULT_UNDESIRED_SITES
	sites_value = ",".join(sites)

	return '# Comma-separated, no spaces between entries.\n+UNDESIRED_Sites = "{0}"\n\n'.format(sites_value)
