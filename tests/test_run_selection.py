"""Check legacy run handling through card parsing and nodescript generation."""

import contextlib
import io
from pathlib import Path
import tempfile
import unittest

from SConfiguration import SConfiguration
from generators.bash.generate_nodescript import generate_nodescript


class RunSelectionTests(unittest.TestCase):
    def configuration(self, version, runs="", generator="gemc"):
        with contextlib.redirect_stdout(io.StringIO()):
            return SConfiguration.from_string(
                f"configuration: rgk_fall2018_FTOn\nsoftwarev: gemc/{version} coatjava/10.0.7\n"
                f"generator: {generator}\noutput_type: 1\n{runs}\n"
            )

    def test_legacy_versions_override_missing_explicit_and_weighted_runs(self):
        for version in ("4.4.2", "5.10", "5.14", "6", "6.0", "6.0.9"):
            for runs in ("", "runs: 19324", "run_list: 19324, 19359",
                         "runs: 19324\nrun_list: 19324, 19359"):
                for generator in ("gemc", "/volatile/clas12/test"):
                    with self.subTest(version=version, runs=runs, generator=generator):
                        config = self.configuration(version, runs, generator)
                        self.assertEqual(config.runs, "11")
                        self.assertIsNone(config.run_list)
                        with tempfile.TemporaryDirectory() as temp_dir:
                            output = Path(temp_dir) / "nodescript.sh"
                            with contextlib.redirect_stdout(io.StringIO()):
                                generate_nodescript(config, 123, output_file=str(output))
                            script = output.read_text()
                        self.assertIn("-RUNNO=11\n", script)
                        self.assertNotIn("-RUNNO=19324", script)
                        self.assertNotIn("select_weighted_run", script)

    def test_supported_and_named_versions_keep_run_selection(self):
        for version in ("6.1", "6.1.0", "6.10", "7.0", "dev", "meson", "latest"):
            for runs, expected_run, expected_list in (
                ("", None, None),
                ("runs: 19324", "19324", None),
                ("run_list: 19324, 19359", None, "19324, 19359"),
            ):
                with self.subTest(version=version, runs=runs):
                    config = self.configuration(version, runs)
                    self.assertEqual(config.runs, expected_run)
                    self.assertEqual(config.run_list, expected_list)


if __name__ == "__main__":
    unittest.main()
