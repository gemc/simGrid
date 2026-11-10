"""Check collision-log extraction without contacting Condor or remote storage."""

from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from condor_io.list_existing_outputs import collect_candidates, jlab_path


SCRIPT = Path(__file__).parents[1] / "condor_io" / "list_existing_outputs.py"
URI = "osdf:///jlab-osdf/clas12/volatile/osg/pilleux/12147/rgc_spring2023_dvcs_ND3-12147-7022.hipo"
LOCAL = "/volatile/clas12/osg/pilleux/12147/rgc_spring2023_dvcs_ND3-12147-7022.hipo"


def collision(uri):
    return 'level=error msg="Error transferring {}: remote object already exists, upload aborted"\n'.format(uri)


class ExistingOutputTests(unittest.TestCase):
    def test_both_osdf_url_forms_map_to_the_same_jlab_path(self):
        self.assertEqual(jlab_path(URI), LOCAL)
        self.assertEqual(jlab_path(URI.replace("osdf:///jlab-osdf/", "osdf://jlab-osdf/")), LOCAL)

    def test_other_namespaces_and_unsafe_paths_are_excluded(self):
        for uri in (
            URI.replace("/volatile/osg/", "/osgpool/backgroundfiles/"),
            URI.replace("/pilleux/", "/../"),
            URI.replace("/pilleux/", "/%2e%2e/"),
            URI.replace("/pilleux/", "/pilleux%0a/"),
            URI.replace("osdf:///jlab-osdf/", "osdf://other-origin/"),
        ):
            with self.subTest(uri=uri):
                self.assertIsNone(jlab_path(uri))

    def test_only_collision_messages_are_listed(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "job.9624.7022.out"
            log.write_text(
                'Uploading file to destination {}\n'.format(URI)
                + 'level=error msg="Permission denied for {}"\n'.format(URI)
                + collision(URI)
                + 'job.9624.7022.out-' + collision(URI),
            )
            self.assertEqual(collect_candidates([log]), [LOCAL])

    def test_cli_scans_recursively_and_outputs_unique_sorted_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "job_12147" / "log"
            nested.mkdir(parents=True)
            later = URI.replace("7022.hipo", "7023.hipo")
            (nested / "job.9624.7022.out").write_text(collision(later) + collision(URI))
            (root / "duplicate.out").write_text(collision(URI))
            (root / "ignored.err").write_text(collision(URI.replace("7022.hipo", "7024.hipo")))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(root), str(nested)],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [LOCAL, LOCAL.replace("7022.hipo", "7023.hipo")])
            self.assertIn("Scanned 2 logs; 2 unique review candidates", result.stderr)

    def test_cli_reports_missing_inputs_without_a_partial_list(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "job.out"
            log.write_text(collision(URI))
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(log), str(Path(directory) / "missing")],
                capture_output=True, text=True,
            )
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("Log path does not exist", result.stderr)


if __name__ == "__main__":
    unittest.main()
