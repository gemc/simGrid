"""Exercise the GEMC-only NERSC worker with a fake GEMC executable."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).parents[1]
NODESCRIPT = REPO_ROOT / "tests" / "nersc_submission" / "nodescript.sh"


class NerscNodescriptTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name).resolve()
        config_dir = self.work_dir / "configuration files"
        config_dir.mkdir()
        self.gcard = config_dir / "detector.gcard"
        self.gcard.write_text("<gcard/>\n")
        self.arguments_file = self.work_dir / "gemc-arguments"
        gemc = self.work_dir / "gemc"
        gemc.write_text(
            '#!/bin/bash\nprintf "%s\\0" "$@" > "$GEMC_TEST_ARGUMENTS"\n'
            'if [[ "${GEMC_TEST_FAIL:-0}" != 0 ]]; then exit "$GEMC_TEST_FAIL"; fi\n'
            'if [[ "${GEMC_TEST_NO_OUTPUT:-0}" == 0 ]]; then printf "test output\\n" > gemc.hipo; fi\n'
        )
        gemc.chmod(0o700)
        self.env = dict(
            os.environ, PATH=str(self.work_dir) + os.pathsep + os.environ["PATH"],
            SIMGRID_FUNCTIONS_FILE=str(REPO_ROOT / "generators/bash/functions.sh"),
            SIMGRID_BACKEND="nersc", GEMC_MEM_SAMPLE_INTERVAL="0",
            GEMC_TEST_ARGUMENTS=str(self.arguments_file), SLURM_JOB_ID="validation",
        )

    def run_worker(self, *args):
        return subprocess.run(
            ["bash", str(NODESCRIPT), *map(str, args)], cwd=self.work_dir,
            env=self.env, capture_output=True, text=True,
        )

    def test_internal_beam_produces_output_and_repeated_runs_are_isolated(self):
        for _ in range(2):
            result = self.run_worker(self.gcard)
            self.assertEqual(result.returncode, 0, result.stderr)
        arguments = self.arguments_file.read_bytes().decode().split("\0")[:-1]
        self.assertIn("-INPUT_GEN_FILE=gemc_internal", arguments)
        self.assertIn("-BEAM_P=e-, 4*GeV, 20*deg, 20*deg", arguments)
        self.assertIn(str(self.gcard), arguments)
        self.assertIn("-N=100", arguments)
        outputs = list(self.work_dir.glob("output-validation-*/gemc.hipo"))
        self.assertEqual(len(outputs), 2)
        self.assertTrue(all(path.stat().st_size for path in outputs))
        self.assertIn("Summary:", result.stdout)

    def test_gemc_failure_is_reported_without_cleaning_shared_input_files(self):
        preserved = self.work_dir / "existing.hipo"
        preserved.write_text("keep this output\n")
        self.env["GEMC_TEST_FAIL"] = "7"
        result = self.run_worker(self.gcard, 10)
        self.assertEqual(result.returncode, 204)
        self.assertTrue(preserved.exists())
        self.assertTrue(self.gcard.exists())

    def test_success_without_output_is_a_failure(self):
        self.env["GEMC_TEST_NO_OUTPUT"] = "1"
        result = self.run_worker(self.gcard)
        self.assertEqual(result.returncode, 215)
        self.assertIn("did not produce a nonempty", result.stderr)

    def test_missing_gcard_is_rejected_before_running_gemc(self):
        result = self.run_worker(self.work_dir / "missing.gcard")
        self.assertEqual(result.returncode, 242)
        self.assertFalse(self.arguments_file.exists())

    def test_invalid_event_count_is_rejected_before_running_gemc(self):
        result = self.run_worker(self.gcard, 0)
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.arguments_file.exists())


if __name__ == "__main__":
    unittest.main()
