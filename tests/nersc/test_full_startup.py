"""Check shared-container startup with real file locks and a mocked Podman-HPC."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


WRAPPER = Path(__file__).resolve().parent / "full-task.sh"


@unittest.skipUnless(shutil.which("flock"), "host flock is required")
class SharedStartupTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.work = Path(temp.name).resolve()
        self.campaign = self.work / "campaign"
        self.campaign.mkdir()
        self.trace = self.work / "calls"
        binary = self.work / "bin"
        binary.mkdir()
        podman = binary / "podman-hpc"
        podman.write_text(
            '#!/bin/bash\n'
            '# Startup children must not inherit the parent shell\'s lock descriptor.\n'
            'if [[ "${CHECK_LOCK_FD:-1}" == 1 ]] && ( : >&9 ) 2>/dev/null; then\n'
            '  echo "inherited lock" >&2; exit 86\n'
            'fi\n'
            'case "$1 $2" in\n'
            '  "container exists")\n'
            '    echo lookup >> "$CALLS"\n'
            '    if [[ -f "$MOCK_CONTAINER.stopped" && -n "${AFTER_STOP_LOOKUP_ERROR:-}" ]]; then\n'
            '      exit "$AFTER_STOP_LOOKUP_ERROR"\n'
            '    fi\n'
            '    [[ -z "${LOOKUP_ERROR:-}" ]] || exit "$LOOKUP_ERROR"\n'
            '    [[ ! -d "$MOCK_CONTAINER" ]] || exit 0\n'
            '    sleep 0.15\n'
            '    exit 1 ;;\n'
            '  "run --rm")\n'
            '    mkdir "$MOCK_CONTAINER" || exit 125\n'
            '    echo create >> "$CALLS" ;;\n'
            '  "stop --time")\n'
            '    echo stop >> "$CALLS"\n'
            '    touch "$MOCK_CONTAINER.stopped"\n'
            '    [[ "${KEEP_CONTAINER:-0}" == 1 ]] || rmdir "$MOCK_CONTAINER"\n'
            '    exit "${STOP_ERROR:-0}" ;;\n'
            '  "exec --workdir")\n'
            '    echo physics >> "$CALLS"\n'
            '    if [[ "${WAIT_FOR_PEER:-0}" == 1 ]]; then\n'
            '      for ((i=0; i<100; i++)); do\n'
            '        [[ $(grep -c "^physics$" "$CALLS") -lt 2 ]] || exit 0\n'
            '        sleep 0.02\n'
            '      done\n'
            '      echo "physics was serialized" >&2; exit 87\n'
            '    fi ;;\n'
            '  exec*)\n'
            '    if [[ "$*" == *token-renew* ]]; then\n'
            '      echo token >> "$CALLS"\n'
            '    else\n'
            '      echo ready >> "$CALLS"\n'
            '      exit "${READINESS_ERROR:-0}"\n'
            '    fi ;;\n'
            'esac\n'
        )
        podman.chmod(0o755)
        self.env = dict(os.environ, PATH=str(binary) + os.pathsep + os.environ["PATH"],
                        SLURM_JOB_ID="123", CALLS=str(self.trace),
                        MOCK_CONTAINER=str(self.work / "container"))

    def start_task(self, task_id):
        temporary = self.work / f"tmp-{task_id}"
        temporary.mkdir()
        env = dict(self.env, TMPDIR=str(temporary))
        return subprocess.Popen(
            ["bash", str(WRAPPER), str(self.campaign), "C", str(task_id), "clasdis", "image:test"],
            env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True,
        )

    def finish_task(self, task_id, process, expected=0):
        try:
            stdout, stderr = process.communicate(timeout=15)
        except subprocess.TimeoutExpired:
            process.kill()
            process.communicate()
            self.fail(f"task {task_id} did not finish")
        task = self.campaign / "jobs" / str(task_id)
        diagnostic = stdout + stderr + (task / "task.err").read_text()
        self.assertEqual(process.returncode, expected, diagnostic)
        self.assertEqual((task / "exit-code").read_text().strip(), str(expected))

    def test_concurrent_tasks_with_distinct_tmpdirs_create_one_container_and_token(self):
        self.env.update(WAIT_FOR_PEER="1", CHECK_LOCK_FD="0")
        processes = [self.start_task(i) for i in range(8)]
        try:
            for task_id, process in enumerate(processes):
                self.finish_task(task_id, process)
        finally:
            for process in processes:
                if process.poll() is None:
                    process.kill()
                process.communicate()
        calls = self.trace.read_text().splitlines()
        self.assertEqual(calls.count("create"), 1)
        self.assertEqual(calls.count("token"), 1)
        self.assertEqual(calls.count("ready"), 8)
        self.assertEqual(calls.count("physics"), 8)

    def test_podman_children_do_not_inherit_the_startup_lock(self):
        self.finish_task(0, self.start_task(0))
        self.assertEqual(self.trace.read_text().splitlines(), ["lookup", "create", "ready", "token", "physics"])

    def test_lookup_error_is_recorded_without_attempting_creation(self):
        self.env["LOOKUP_ERROR"] = "125"
        self.finish_task(0, self.start_task(0), expected=125)
        self.assertEqual(self.trace.read_text().splitlines(), ["lookup"])

    def test_unusable_existing_container_does_not_start_token_or_physics(self):
        Path(self.env["MOCK_CONTAINER"]).mkdir()
        self.env["READINESS_ERROR"] = "125"
        self.finish_task(0, self.start_task(0), expected=125)
        self.assertEqual(self.trace.read_text().splitlines(), ["lookup", "ready"])

    def run_cleanup(self):
        Path(self.env["MOCK_CONTAINER"]).mkdir()
        self.env["STOP_ERROR"] = "125"
        return subprocess.run(["bash", str(WRAPPER), "--cleanup"], env=self.env,
                              capture_output=True, text=True)

    def test_stop_monitor_error_succeeds_when_container_removal_is_confirmed(self):
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("removal confirmed", result.stdout)
        self.assertEqual(self.trace.read_text().splitlines(), ["lookup", "stop", "lookup"])

    def test_stop_error_is_preserved_when_container_still_exists(self):
        self.env["KEEP_CONTAINER"] = "1"
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 125)
        self.assertEqual(self.trace.read_text().splitlines(), ["lookup", "stop", "lookup"])

    def test_stop_error_is_preserved_when_removal_check_fails(self):
        self.env["AFTER_STOP_LOOKUP_ERROR"] = "125"
        result = self.run_cleanup()
        self.assertEqual(result.returncode, 125)
        self.assertEqual(self.trace.read_text().splitlines(), ["lookup", "stop", "lookup"])

    def test_small_fresh_campaign_and_resume_keep_the_original_task_list(self):
        driver = WRAPPER.parent / "full-taskfarmer.sh"
        env = dict(self.env, SCRATCH=str(self.work), SIMGRID_FULL_PREPARE_ONLY="1", SIMGRID_FULL_TASKS="2")
        command = ["bash", str(driver), "C", "image:test"]
        subprocess.run(command, env=env, check=True, capture_output=True)
        campaign = self.work / "simgrid" / "full-c" / "123"
        original = (campaign / "tasks.txt").read_text()
        self.assertEqual(len(original.splitlines()), 2)
        env["SIMGRID_FULL_TASKS"] = "100"
        subprocess.run(command, env=env, check=True, capture_output=True)
        self.assertEqual((campaign / "tasks.txt").read_text(), original)
        for value in ("0", "101", "invalid"):
            env["SIMGRID_FULL_TASKS"] = value
            result = subprocess.run(command, env=env, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertIn("SIMGRID_FULL_TASKS must be between 1 and 100", result.stderr)


if __name__ == "__main__":
    unittest.main()
