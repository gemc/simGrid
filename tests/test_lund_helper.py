"""Tests for LUND-file discovery."""

import subprocess
import unittest
from unittest import mock

from generators import lund_helper


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


if __name__ == "__main__":
    unittest.main()
