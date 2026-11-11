"""Exercise startup recovery in generated jobs using local command stubs."""

import contextlib
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

from SConfiguration import SConfiguration
from generators.bash.generate_nodescript import generate_nodescript


FUNCTIONS_SH = Path(__file__).parents[1] / "generators" / "bash" / "functions.sh"


class ExistingOutputCheckTests(unittest.TestCase):
    def run_job(self, *, generator="gemc", output_type="1", runs="", ls_exit=0,
                get_exit=0, test_exit=0, write_download=True):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            tools = root / "bin"
            tools.mkdir()
            (tools / "python3").symlink_to(sys.executable)
            calls = root / "calls.txt"
            pelican = tools / "pelican"
            pelican.write_text(
                '#!/bin/bash\n'
                'printf "pelican %s\\n" "$*" >> "$TEST_CALLS"\n'
                'case "$1 $2" in\n'
                '  "object ls") exit "$TEST_LS_EXIT" ;;\n'
                '  "object get")\n'
                '    if [[ $TEST_WRITE_DOWNLOAD == 1 ]]; then printf data > "$4"; fi\n'
                '    exit "$TEST_GET_EXIT" ;;\n'
                '  *) exit 99 ;;\n'
                'esac\n'
            )
            pelican.chmod(0o700)
            validator = tools / "hipo-utils"
            validator.write_text(
                '#!/bin/bash\n'
                'printf "hipo-utils %s\\n" "$*" >> "$TEST_CALLS"\n'
                '[[ $1 == -test && -f $2 ]] || exit 99\n'
                'exit "$TEST_HIPO_EXIT"\n'
            )
            validator.chmod(0o700)
            (root / "functions.sh").write_text(
                'source "{}"\n'.format(FUNCTIONS_SH)
                + 'clean_and_check_environment() { :; }\n'
                + 'report_environment() { :; }\n'
                + 'module() { printf "module %s\\n" "$*" >> "$TEST_CALLS"; }\n'
                + 'setup_job_files() { echo NORMAL_PIPELINE; exit 77; }\n'
            )
            with contextlib.redirect_stdout(io.StringIO()):
                config = SConfiguration.from_string(
                    "configuration: rgc_summer2022\nsoftwarev: gemc/6.1 coatjava/14.2.2\n"
                    "generator: {}\noutput_type: {}\nstring_id: label\n{}\n".format(
                        generator, output_type, runs,
                    )
                )
                config.username = "pilleux"
                generate_nodescript(config, 12147, output_file=str(root / "nodescript.sh"))
            if config.run_list:
                (root / "select_run.py").write_text((FUNCTIONS_SH.parent / "select_run.py").read_text())
                (root / "runs.json").write_text(json.dumps({"test": {"19324": 1, "19359": 3}}))
                (root / "run_list.txt").write_text("19324\n19359\n")
            env = os.environ.copy()
            env.update({
                "PATH": str(tools) + os.pathsep + env["PATH"],
                "PELICAN_BIN": str(pelican),
                "_CONDOR_CREDS": str(root / "credentials"),
                "TEST_CALLS": str(calls),
                "TEST_LS_EXIT": str(ls_exit),
                "TEST_GET_EXIT": str(get_exit),
                "TEST_HIPO_EXIT": str(test_exit),
                "TEST_WRITE_DOWNLOAD": "1" if write_download else "0",
            })
            result = subprocess.run(
                ["bash", str(root / "nodescript.sh"), "6973", "osdf:///inputs/lund1.dat"],
                cwd=root, env=env, capture_output=True, text=True,
            )
            command_log = calls.read_text()
            self.assertFalse((root / "output" / "existing-output.hipo").exists())
            return result, command_log

    def test_valid_existing_output_exits_successfully_before_simulation_setup(self):
        for generator in ("gemc", "clasdis", "/volatile/clas12/inputs"):
            for output_type in ("1", "2"):
                with self.subTest(generator=generator, output_type=output_type):
                    result, calls = self.run_job(generator=generator, output_type=output_type)
                    self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                    lund = "lund1-" if generator.startswith("/") else ""
                    uri = (
                        "osdf:///jlab-osdf/clas12/volatile/osg/pilleux/12147/"
                        "label-{}12147-6973.hipo".format(lund)
                    )
                    self.assertIn("pelican object ls " + uri, calls)
                    self.assertIn("pelican object get " + uri + " existing-output.hipo", calls)
                    self.assertIn("module load coatjava/14.2.2", calls)
                    self.assertIn("hipo-utils -test existing-output.hipo", calls)
                    self.assertNotIn("NORMAL_PIPELINE", result.stdout)

    def test_missing_remote_output_continues_without_download_or_validation(self):
        result, calls = self.run_job(ls_exit=1)
        self.assertEqual(result.returncode, 77)
        self.assertIn("NORMAL_PIPELINE", result.stdout)
        self.assertNotIn("object get", calls)
        self.assertNotIn("hipo-utils", calls)

    def test_invalid_remote_output_is_held_for_manual_cleanup(self):
        result, calls = self.run_job(test_exit=1)
        self.assertEqual(result.returncode, 214)
        self.assertIn("manual cleanup at JLab", result.stdout)
        self.assertIn("hipo-utils -test", calls)
        self.assertNotIn("NORMAL_PIPELINE", result.stdout)

    def test_download_failure_does_not_report_success(self):
        for options in ({"get_exit": 1}, {"write_download": False}):
            with self.subTest(options=options):
                result, calls = self.run_job(**options)
                self.assertEqual(result.returncode, 202)
                self.assertNotIn("hipo-utils", calls)
                self.assertNotIn("NORMAL_PIPELINE", result.stdout)

    def test_fixed_run_is_included_in_the_lookup_filename(self):
        result, calls = self.run_job(runs="runs: 19324")
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        self.assertIn("label-19324-12147-6973.hipo", calls)

    def test_weighted_run_retries_check_the_same_filename(self):
        first, first_calls = self.run_job(runs="run_list: 19324, 19359")
        second, second_calls = self.run_job(runs="run_list: 19324, 19359")
        self.assertEqual(first.returncode, 0, first.stdout + first.stderr)
        self.assertEqual(second.returncode, 0, second.stdout + second.stderr)
        self.assertEqual(first_calls, second_calls)
        self.assertRegex(first_calls, r"label-(19324|19359)-12147-6973\.hipo")


if __name__ == "__main__":
    unittest.main()
