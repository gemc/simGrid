"""Check collision-log extraction without contacting Condor or remote storage."""

import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

from condor_io.list_existing_outputs import collect_candidates, jlab_path, ongoing_job_ids


SCRIPT = Path(__file__).parents[1] / "condor_io" / "list_existing_outputs.py"
URI = "osdf:///jlab-osdf/clas12/volatile/osg/pilleux/12147/rgc_spring2023_dvcs_ND3-12147-7022.hipo"
LOCAL = "/volatile/clas12/osg/pilleux/12147/rgc_spring2023_dvcs_ND3-12147-7022.hipo"


def collision(uri):
    return 'level=error msg="Error transferring {}: remote object already exists, upload aborted"\n'.format(uri)


class ExistingOutputTests(unittest.TestCase):
    def run_scanner(self, *paths, ads=None, query_exit=0):
        if ads is None:
            ads = [
                {"ClusterId": 9624, "ProcId": 7022, "JobStatus": 5},
                {"ClusterId": 9624, "ProcId": 7023, "JobStatus": 2},
                {"ClusterId": 9540, "ProcId": 15, "JobStatus": 1},
                {"ClusterId": 9624, "ProcId": 1, "JobStatus": 5},
            ]
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            queue = root / "queue.json"
            queue.write_text(json.dumps(ads))
            command_log = root / "calls.txt"
            executable = root / "condor_q"
            executable.write_text(
                '#!/bin/bash\n'
                'printf "%s\\n" "$*" >> "$TEST_CONDOR_CALLS"\n'
                'cat "$TEST_CONDOR_JSON"\n'
                'exit "$TEST_CONDOR_EXIT"\n'
            )
            executable.chmod(0o700)
            env = os.environ.copy()
            env.update({
                "PATH": str(root) + os.pathsep + env["PATH"],
                "TEST_CONDOR_CALLS": str(command_log),
                "TEST_CONDOR_JSON": str(queue),
                "TEST_CONDOR_EXIT": str(query_exit),
            })
            result = subprocess.run(
                [sys.executable, str(SCRIPT), *map(str, paths)],
                env=env, capture_output=True, text=True,
            )
            if command_log.exists():
                self.assertEqual(command_log.read_text(), "gemc -json -attributes ClusterId,ProcId,JobStatus\n")
            return result

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
            self.assertEqual(collect_candidates([log]), [("9624.7022", LOCAL)])

    def test_cli_scans_recursively_and_outputs_unique_sorted_paths(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            nested = root / "job_12147" / "log"
            nested.mkdir(parents=True)
            later = URI.replace("7022.hipo", "7023.hipo")
            (nested / "job.9624.7022.out").write_text(collision(URI))
            (root / "job.9624.7022.out").write_text(collision(URI))
            (root / "job.9624.7023.out").write_text(collision(later))
            (root / "ignored.err").write_text(collision(URI.replace("7022.hipo", "7024.hipo")))
            result = self.run_scanner(root, nested)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [
                "9624.7022\t" + LOCAL, "9624.7023\t" + LOCAL.replace("7022.hipo", "7023.hipo"),
            ])
            self.assertIn("Scanned 3 ongoing job logs; 2 unique review candidates", result.stderr)

    def test_scanning_all_submissions_keeps_their_distinct_condor_clusters(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            first = root / "pilleux" / "job_12147" / "log"
            second = root / "carman" / "job_12069" / "log"
            first.mkdir(parents=True)
            second.mkdir(parents=True)
            other_uri = URI.replace("12147", "12069").replace("7022.hipo", "15.hipo")
            (first / "job.9624.7022.out").write_text(collision(URI))
            (second / "job.9540.15.out").write_text(collision(other_uri))
            result = self.run_scanner(root)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout.splitlines(), [
                "9540.15\t" + jlab_path(other_uri), "9624.7022\t" + LOCAL,
            ])

    def test_mismatched_job_and_output_process_numbers_are_excluded(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "job.9624.1.out"
            log.write_text(collision(URI))
            result = self.run_scanner(log)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(result.stdout, "")
            self.assertIn("Skipping unverified job/file association", result.stderr)

    def test_cli_reports_missing_inputs_without_a_partial_list(self):
        with tempfile.TemporaryDirectory() as directory:
            log = Path(directory) / "job.out"
            log.write_text(collision(URI))
            result = self.run_scanner(log, Path(directory) / "missing")
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("Log path does not exist", result.stderr)

    def test_only_ongoing_jobs_are_selected_even_when_old_logs_remain(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "job.9624.7022.out").write_text(collision(URI))
            (root / "job.9624.7023.out").write_text(collision(URI.replace("7022.hipo", "7023.hipo")))
            # Reading this historical path would fail; it must be excluded before scanning.
            (root / "job.9999.7022.out").mkdir()
            result = self.run_scanner(root, ads=[
                {"ClusterId": 9624, "ProcId": 7022, "JobStatus": 5},
                {"ClusterId": 9624, "ProcId": 7023, "JobStatus": 4},
                {"ClusterId": 9999, "ProcId": 7022, "JobStatus": 3},
            ])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "9624.7022\t" + LOCAL + "\n")
            self.assertIn("Scanned 1 ongoing job logs", result.stderr)

    def test_empty_queue_does_not_fall_back_to_scanning_historical_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "job.9624.7022.out").write_text(collision(URI))
            result = self.run_scanner(root, ads=[])
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(result.stdout, "")
            self.assertIn("Scanned 0 ongoing job logs", result.stderr)

    def test_queue_failure_does_not_produce_candidates_from_historical_logs(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "job.9624.7022.out").write_text(collision(URI))
            result = self.run_scanner(root, query_exit=1)
            self.assertEqual(result.returncode, 1)
            self.assertEqual(result.stdout, "")
            self.assertIn("condor_q failed", result.stderr)

    @mock.patch("condor_io.list_existing_outputs.subprocess.run")
    def test_ongoing_statuses_include_held_jobs_but_exclude_completed_and_removed(self, run_mock):
        run_mock.return_value.stdout = json.dumps([
            {"ClusterId": 9624, "ProcId": status, "JobStatus": status} for status in range(8)
        ])
        self.assertEqual(ongoing_job_ids("gemc"), {"9624.1", "9624.2", "9624.5", "9624.6", "9624.7"})
        run_mock.assert_called_once()

    @mock.patch("condor_io.list_existing_outputs.subprocess.run")
    def test_malformed_queue_responses_are_rejected(self, run_mock):
        for payload in ({"error": "unavailable"}, [{"ClusterId": 9624, "ProcId": 1}]):
            with self.subTest(payload=payload):
                run_mock.return_value.stdout = json.dumps(payload)
                with self.assertRaises(ValueError):
                    ongoing_job_ids("gemc")


if __name__ == "__main__":
    unittest.main()
