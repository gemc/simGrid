"""Verify NERSC container launch arguments and failure propagation without Podman."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


REPO_ROOT = Path(__file__).parents[1]
LAUNCHER = REPO_ROOT / "nersc_io" / "container.sh"
FUNCTIONS_SH = REPO_ROOT / "generators" / "bash" / "functions.sh"


class NerscContainerTests(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp_dir.cleanup)
        self.work_dir = Path(self.temp_dir.name).resolve()
        self.node_script = self.work_dir / "node script.sh"
        self.node_script.write_text("#!/bin/bash\nexit 0\n")
        self.args_file = self.work_dir / "podman-arguments"
        podman = self.work_dir / "podman-hpc"
        podman.write_text(
            '#!/bin/bash\nprintf "%s\\0" "$@" > "$PODMAN_TEST_ARGS_FILE"\n'
            'exit "${PODMAN_TEST_EXIT_CODE:-0}"\n'
        )
        podman.chmod(0o700)
        self.env = dict(
            os.environ, PATH=str(self.work_dir) + os.pathsep + os.environ["PATH"],
            SIMGRID_FUNCTIONS_FILE=str(FUNCTIONS_SH), PODMAN_TEST_ARGS_FILE=str(self.args_file),
        )
        self.env.pop("SIMGRID_CONFIG_DIR", None)

    def run_launcher(self, shell, *args):
        return subprocess.run(
            [shell, "-f", "-eu", "-c", 'source "$1"; shift; run_nersc_container "$@"',
             shell, str(LAUNCHER), *args],
            cwd=self.work_dir, env=self.env, capture_output=True, text=True,
        )

    def test_mounts_and_script_arguments_are_preserved_in_both_shells(self):
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                if not shutil.which(shell):
                    continue
                worker_args = ("arg with spaces", "$(touch should-not-exist)")
                result = self.run_launcher(shell, "registry/image:test", "node script.sh", *worker_args)
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = self.args_file.read_bytes().decode().split("\0")[:-1]
                mounts = [arguments[i + 1] for i, value in enumerate(arguments) if value == "--volume"]
                self.assertIn(f"{self.node_script}:/opt/simgrid/nodescript.sh:ro", mounts)
                self.assertIn(f"{FUNCTIONS_SH}:/opt/simgrid/functions.sh:ro", mounts)
                self.assertEqual(arguments[-2:], list(worker_args))
                self.assertFalse((self.work_dir / "should-not-exist").exists())

    def test_missing_scripts_fail_before_starting_podman(self):
        result = self.run_launcher("bash", "registry/image:test", "missing.sh")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Required script is not readable", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_container_failure_is_returned_to_the_scheduler(self):
        self.env["PODMAN_TEST_EXIT_CODE"] = "17"
        result = self.run_launcher("bash", "registry/image:test", str(self.node_script))
        self.assertEqual(result.returncode, 17)

    def test_usage_error_does_not_start_podman(self):
        result = self.run_launcher("bash")
        self.assertEqual(result.returncode, 2)
        self.assertIn("Usage:", result.stderr)
        self.assertFalse(self.args_file.exists())

    def test_configuration_directory_is_mounted_read_only_with_group_access(self):
        config_dir = self.work_dir / "configuration files"
        config_dir.mkdir()
        self.env["SIMGRID_CONFIG_DIR"] = config_dir.name
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                if not shutil.which(shell):
                    continue
                result = self.run_launcher(shell, "registry/image:test", str(self.node_script))
                self.assertEqual(result.returncode, 0, result.stderr)
                arguments = self.args_file.read_bytes().decode().split("\0")[:-1]
                self.assertIn(f"{config_dir}:{config_dir}:ro", arguments)
                self.assertEqual(arguments[arguments.index("--group-add") + 1], "keep-groups")

    def test_missing_configuration_directory_fails_before_starting_podman(self):
        self.env["SIMGRID_CONFIG_DIR"] = str(self.work_dir / "missing")
        result = self.run_launcher("bash", "registry/image:test", str(self.node_script))
        self.assertEqual(result.returncode, 2)
        self.assertFalse(self.args_file.exists())


if __name__ == "__main__":
    unittest.main()
