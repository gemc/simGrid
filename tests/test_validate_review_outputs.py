"""Verify that only successful HIPO tests generate exact Condor process removals."""

import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest


SCRIPT = Path(__file__).parents[1] / "condor_io" / "validate_review_outputs.py"


class ValidateReviewOutputsTests(unittest.TestCase):
    def run_validation(self, names, *, existing_output=None, have_validator=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "bin"
            tools.mkdir()
            calls = root / "calls.txt"
            validator = tools / "hipo-utils"
            if have_validator:
                validator.write_text(
                    '#!/bin/bash\n'
                    '[[ $1 == -test ]] || exit 99\n'
                    'printf "%s\\n" "$2" >> "$TEST_CALLS"\n'
                    'case "$2" in\n'
                    '  *bad*) echo "status check : OK"; exit 1 ;;\n'
                    '  *) exit 0 ;;\n'
                    'esac\n'
                )
                validator.chmod(0o700)
            paths = [root / name for name in names]
            for path in paths:
                if "missing" not in path.name:
                    path.parent.mkdir(parents=True, exist_ok=True)
                    path.write_text("test HIPO data")
            listing = root / "files-to-review.txt"
            listing.write_text("\n".join(map(str, paths)) + "\n")
            output = root / "remove-verified-jobs.sh"
            if existing_output is not None:
                output.write_text(existing_output)
            env = os.environ.copy()
            env["PATH"] = str(tools) + os.pathsep + "/usr/bin:/bin"
            env["TEST_CALLS"] = str(calls)
            result = subprocess.run(
                [sys.executable, str(SCRIPT), str(listing), "--cluster-id", "9624", "-o", str(output)],
                cwd=root, env=env, capture_output=True, text=True,
            )
            generated = output.read_text() if output.exists() else None
            checked = calls.read_text().splitlines() if calls.exists() else []
            # A real condor_rm is never needed: validation must only write its commands.
            return result, generated, checked

    def test_only_good_files_generate_removals_using_the_supplied_cluster(self):
        result, script, checked = self.run_validation([
            "rgc-spring-12147-6973.hipo", "bad-12147-6974.hipo", "missing-12147-6975.hipo",
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(checked), 2)
        self.assertEqual(script, "condor_rm 9624.6973\n")
        self.assertNotIn("condor_rm 9624.6974", script)
        self.assertNotIn("condor_rm 9624.6975", script)
        self.assertNotIn("condor_rm 12147.", script)
        self.assertIn("Nothing was removed", result.stderr)
        syntax = subprocess.run(["bash", "-n"], input=script, text=True, capture_output=True)
        self.assertEqual(syntax.returncode, 0, syntax.stderr)

    def test_multiple_submissions_are_rejected_before_testing_files(self):
        result, script, checked = self.run_validation(["good-12147-6973.hipo", "good-12148-6974.hipo"])
        self.assertEqual(result.returncode, 1)
        self.assertIn("multiple portal submissions", result.stderr)
        self.assertIsNone(script)
        self.assertEqual(checked, [])

    def test_unrecognized_filename_is_rejected(self):
        result, script, checked = self.run_validation(["unrecognized.hipo"])
        self.assertEqual(result.returncode, 1)
        self.assertIsNone(script)
        self.assertEqual(checked, [])

    def test_duplicate_paths_and_processes_do_not_duplicate_removal_commands(self):
        result, script, checked = self.run_validation([
            "good-12147-0.hipo", "good-12147-0.hipo", "copy/good-12147-0.hipo",
        ])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(len(checked), 2)
        self.assertEqual(script, "condor_rm 9624.0\n")

    def test_existing_output_script_is_preserved(self):
        result, script, checked = self.run_validation(["good-12147-6973.hipo"], existing_output="keep me\n")
        self.assertEqual(result.returncode, 1)
        self.assertEqual(script, "keep me\n")
        self.assertEqual(checked, [])

    def test_missing_validation_tool_cannot_generate_removals(self):
        result, script, checked = self.run_validation(["good-12147-6973.hipo"], have_validator=False)
        self.assertEqual(result.returncode, 1)
        self.assertIn("hipo-utils was not found", result.stderr)
        self.assertIsNone(script)
        self.assertEqual(checked, [])


if __name__ == "__main__":
    unittest.main()
