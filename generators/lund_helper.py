"""lund_helper.py — utilities for locating and counting lund input files.

Lund files are pre-generated event files used by type-2 submissions.
They live in a /volatile/clas12/... directory on JLab storage and are
accessed on OSG worker nodes via the Pelican data federation client.
"""

import os
import subprocess

# Short-lived OAuth2 bearer token injected by the HTCondor CredMon.
# The job environment provides BEARER_TOKEN_FILE; this default is the
# submit-node value used when running outside a condor job.
_DEFAULT_BEARER_TOKEN_FILE = "/var/run/user/6635/bt_u6635"

_ALLOWED_EXTENSIONS = {".dat", ".txt", ".lund"}


def to_pelican_path(lund_location):
    """Convert a /volatile/clas12/... local path to its OSDF pelican URI.

    JLab volatile storage is exposed through the OSDF federation at:
      osdf:///jlab-osdf/clas12/volatile/<rest>

    The path segment swap (/volatile/clas12/ → /clas12/volatile/) reflects
    the OSDF namespace convention for JLab storage.

    Raises ValueError if lund_location does not contain /volatile/clas12/.
    """
    if "/volatile/clas12/" not in lund_location:
        raise ValueError(
            "lund_location must contain /volatile/clas12/ — got: {}".format(
                lund_location
            )
        )
    swapped = lund_location.replace("/volatile/clas12/", "/clas12/volatile/", 1)
    return "osdf:///jlab-osdf" + swapped


def count_files(lund_location):
    """Return the number of lund files at lund_location via pelican object ls.

    Calls `pelican object ls <osdf_path>` and counts entries whose extension
    is one of .dat, .txt, or .lund.  This determines the Queue N value for
    type-2 HTCondor submissions — one subjob per lund file.

    Args:
        lund_location: str, /volatile/clas12/... path from scard.generator.

    Returns:
        int: count of lund files found.

    Raises:
        subprocess.CalledProcessError: if pelican fails or the path is absent.
        ValueError: if lund_location cannot be converted to a pelican URI.
    """
    pelican_path = to_pelican_path(lund_location)

    env = os.environ.copy()
    if "BEARER_TOKEN_FILE" not in env:
        env["BEARER_TOKEN_FILE"] = _DEFAULT_BEARER_TOKEN_FILE

    result = subprocess.run(
        ["pelican", "object", "ls", pelican_path],
        stdout=subprocess.PIPE,
        universal_newlines=True,
        check=True,
        env=env,
    )

    lines = [line.strip() for line in result.stdout.splitlines() if line.strip()]
    return sum(
        1 for line in lines if os.path.splitext(line)[1] in _ALLOWED_EXTENSIONS
    )
