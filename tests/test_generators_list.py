"""Keep the NERSC generator test list in sync with the portal's generator dropdown.

The OSG portal submits whatever is selected in the generator `<select>` of
web_portal/type1.php. The NERSC generators smoke test iterates
tests/nersc/generators_list. This test fails if the two drift, so a generator added
to or removed from the portal forces the same change to the NERSC test list (and vice
versa). The internal `gemc` generator is excluded: it is not an mcgen executable.
"""

import re
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).parents[1]
TYPE1_PHP = REPO_ROOT / "web_portal" / "type1.php"
GENERATORS_LIST = REPO_ROOT / "tests" / "nersc" / "generators_list"

# Options in the generator dropdown that are not mcgen executables.
NON_MCGEN = {"gemc"}


def portal_generators():
    text = TYPE1_PHP.read_text()
    block = re.search(r'<select[^>]*\bname="generator"[^>]*>(.*?)</select>', text, re.DOTALL)
    if not block:
        raise AssertionError("generator <select> not found in web_portal/type1.php")
    options = re.findall(r'<option\s+value="([^"]+)"', block.group(1))
    return [opt for opt in options if opt not in NON_MCGEN]


def listed_generators():
    return [line.strip() for line in GENERATORS_LIST.read_text().splitlines() if line.strip()]


class GeneratorsListSyncTests(unittest.TestCase):
    def test_matches_portal_dropdown(self):
        portal = portal_generators()
        listed = listed_generators()
        self.assertEqual(
            sorted(listed),
            sorted(portal),
            "tests/nersc/generators_list is out of sync with the generator dropdown in "
            "web_portal/type1.php (excluding the internal 'gemc' generator)."
            f"\n  only in generators_list: {sorted(set(listed) - set(portal))}"
            f"\n  only in type1.php:       {sorted(set(portal) - set(listed))}",
        )

    def test_no_duplicate_entries(self):
        listed = listed_generators()
        self.assertEqual(len(listed), len(set(listed)), "generators_list has duplicate entries")


if __name__ == "__main__":
    unittest.main()
