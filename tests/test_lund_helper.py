"""Tests for Pelican integrations."""

import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest import mock

from generators import lund_helper


FUNCTIONS_SH = Path(__file__).parents[1] / "generators" / "bash" / "functions.sh"


class PelicanRetryTests(unittest.TestCase):
    @mock.patch("generators.lund_helper.time.sleep")
    @mock.patch("generators.lund_helper.subprocess.run")
    def test_list_retries_until_fifth_attempt_succeeds(self, run_mock, sleep_mock):
        failure = subprocess.CalledProcessError(1, ["pelican", "object", "ls"])
        success = subprocess.CompletedProcess([], 0, stdout="lund1.dat\n")
        run_mock.side_effect = [failure, failure, failure, failure, success]

        paths = lund_helper._list_lund_files("/volatile/clas12/test")

        self.assertEqual(paths, ["osdf:///jlab-osdf/clas12/volatile/test/lund1.dat"])
        self.assertEqual(run_mock.call_count, 5)
        self.assertEqual(sleep_mock.call_count, 4)

    @mock.patch("generators.lund_helper.time.sleep")
    @mock.patch("generators.lund_helper.subprocess.run")
    def test_list_raises_after_fifth_failure(self, run_mock, sleep_mock):
        run_mock.side_effect = subprocess.CalledProcessError(
            1,
            ["pelican", "object", "ls"],
        )

        with self.assertRaises(subprocess.CalledProcessError):
            lund_helper._list_lund_files("/volatile/clas12/test")

        self.assertEqual(run_mock.call_count, 5)
        self.assertEqual(sleep_mock.call_count, 4)


class PelicanUploadTests(unittest.TestCase):
    def _run_write_to_jlab(self, pelican_output):
        with tempfile.TemporaryDirectory() as work_dir:
            pelican = Path(work_dir) / "pelican"
            pelican.write_text(
                "#!/bin/bash\n"
                "printf '%s\\n' \"$PELICAN_TEST_OUTPUT\"\n",
                encoding="utf-8",
            )
            pelican.chmod(0o700)
            env = os.environ.copy()
            env["PELICAN_BIN"] = str(pelican)
            env["PELICAN_TEST_OUTPUT"] = pelican_output
            return subprocess.run(
                [
                    "bash",
                    "-c",
                    'source "$1"\nwrite_to_jlab user label 123 4',
                    "bash",
                    str(FUNCTIONS_SH),
                ],
                cwd=work_dir,
                check=False,
                capture_output=True,
                env=env,
                text=True,
            )

    def test_upload_fails_when_zero_exit_has_no_completion_record(self):
        result = self._run_write_to_jlab(
            'time="2026-09-09T13:19:37-07:00" level=error '
            'msg="No progress made in last 1m40.1s in upload"',
        )

        self.assertEqual(result.returncode, 202)
        self.assertIn("did not report successful completion", result.stdout)

    def test_upload_succeeds_with_zero_exit_and_completion_record(self):
        result = self._run_write_to_jlab(
            'time="2026-09-09T13:20:04-07:00" level=debug '
            'msg="Successful upload of 14039432 bytes"',
        )

        self.assertEqual(result.returncode, 0)


if __name__ == "__main__":
    unittest.main()
