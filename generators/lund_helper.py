"""lund_helper.py — utilities for locating and staging lund input files.

Lund files are pre-generated event files used by type-2 submissions.
They live under /volatile/clas12/... on JLab storage and are accessed on
OSG worker nodes via the Pelican data-federation client.

Typical flow for a type-2 submission:
  1. write_lund_files(scard.generator) — query OSDF, write one pelican URI
     per line to a local 'lund_files' text file, return the file count.
  2. Stage 'lund_files' as an HTCondor input file.
  3. Use 'queue lundFile from lund_files' in the submit file — HTCondor
     creates one subjob per line, injecting $(lundFile) into Arguments.
"""

import os
import subprocess

# Short-lived OAuth2 bearer token injected by the HTCondor CredMon.
# The job environment provides BEARER_TOKEN_FILE; this default is the
# submit-node value used when running outside a condor job.
_DEFAULT_BEARER_TOKEN_FILE = "/var/run/user/6635/bt_u6635"

_ALLOWED_EXTENSIONS = {".dat", ".txt", ".lund"}

LUND_FILES = "lund_files"

_MOCK_FILENAMES = ["lund1.dat", "lund2.dat", "lund3.dat"]


def to_pelican_path(lund_location):
    """Convert a /volatile/clas12/... local path to its OSDF pelican URI.

    JLab volatile storage is exposed through the OSDF federation at:
      osdf:///jlab-osdf/clas12/volatile/<rest>

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


def _pelican_env():
    """Return an env dict with BEARER_TOKEN_FILE set."""
    env = os.environ.copy()
    if "BEARER_TOKEN_FILE" not in env:
        env["BEARER_TOKEN_FILE"] = _DEFAULT_BEARER_TOKEN_FILE
    return env


def _test_mode_warning(lines):
    """Print an emphasized block for test-mode fallback notices."""
    border = "=" * 64
    print(border)
    for line in lines:
        print("  {}".format(line))
    print(border)


def _list_lund_files(lund_location, test=False):
    """Return a list of full OSDF pelican URIs for lund files at lund_location.

    Calls `pelican object ls` and builds absolute osdf:/// paths for every
    entry whose extension is in _ALLOWED_EXTENSIONS.  Handles both forms of
    pelican output: full osdf:/// URIs and bare filenames.

    Args:
        lund_location: str, /volatile/clas12/... path from scard.generator.
        test:          bool, if True use a 3-file mockup when pelican is absent;
                       if False (default) raise an error instead.

    Raises:
        RuntimeError:  pelican not found and test=False.
        subprocess.CalledProcessError: pelican failed or path does not exist.
        ValueError: lund_location cannot be converted to a pelican URI.
    """
    pelican_path = to_pelican_path(lund_location)
    base = pelican_path.rstrip("/")

    try:
        result = subprocess.run(
            ["pelican", "object", "ls", pelican_path],
            stdout=subprocess.PIPE,
            universal_newlines=True,
            check=True,
            env=_pelican_env(),
        )
    except FileNotFoundError:
        if not test:
            raise RuntimeError(
                "pelican not found. Use --test to run with a lund-file mockup."
            )
        _test_mode_warning([
            "TEST MODE: pelican not found.",
            "Using mockup lund files: {}".format(", ".join(_MOCK_FILENAMES)),
            "These are NOT real files — for pipeline testing only.",
        ])
        return ["{}/{}".format(base, f) for f in _MOCK_FILENAMES]

    paths = []
    for line in result.stdout.splitlines():
        name = line.strip()
        if not name:
            continue
        path = name if name.startswith("osdf:///") else base + "/" + name.lstrip("/")
        if os.path.splitext(path)[1] in _ALLOWED_EXTENSIONS:
            paths.append(path)

    return paths


def write_lund_files(lund_location, output_file=LUND_FILES, test=False):
    """Write one OSDF pelican URI per line to output_file and return the count.

    This generates the file that HTCondor reads with
    'queue lundFile from lund_files' — one subjob is created per line.

    Args:
        lund_location: str, /volatile/clas12/... path from scard.generator.
        output_file:   str, path to write. Defaults to 'lund_files'.
        test:          bool, if True use a 3-file mockup when pelican is absent.

    Returns:
        int: number of lund file URIs written.

    Raises:
        RuntimeError:  pelican not found and test=False.
        subprocess.CalledProcessError: if pelican fails.
        ValueError: if lund_location cannot be converted to a pelican URI.
    """
    paths = _list_lund_files(lund_location, test=test)
    with open(output_file, "w") as f:
        for path in paths:
            f.write(path + "\n")
    print("lund_helper: wrote {} URI(s) to {}".format(len(paths), output_file))
    return len(paths)


def count_files(lund_location, test=False):
    """Return the number of lund files at lund_location via pelican object ls.

    Args:
        test: bool, if True use a 3-file mockup when pelican is absent.

    Raises:
        RuntimeError:  pelican not found and test=False.
        subprocess.CalledProcessError: if pelican fails or the path is absent.
        ValueError: if lund_location cannot be converted to a pelican URI.
    """
    return len(_list_lund_files(lund_location, test=test))
