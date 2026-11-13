"""Exercise full-chain commands and TaskFarmer layouts without Slurm, CVMFS, or simulation tools."""

import os
from pathlib import Path
import shlex
import subprocess
import tempfile
import unittest


ROOT = Path(__file__).resolve().parents[1]
NERSC = ROOT / "tests" / "nersc"


class FullWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.trace = self.work / "commands"
        functions = self.work / "functions.sh"
        functions.write_text(
            f'source {shlex.quote(str(ROOT / "generators/bash/functions.sh"))}\n'
            'run_timed() { "$@"; }\n'
            'report_environment() { :; }\n'
            'setup_test_environment() { CLAS12_CONFIG=/config; }\n'
            'load_module() { :; }\n'
            'unload_module_if_loaded() { :; }\n'
            'require_executable() { :; }\n'
            'run_gemc() { echo "gemc $*" >> "$TRACE"; printf data > gemc.hipo; }\n'
            'run_reconstruction() {\n'
            '  echo "recon $*" >> "$TRACE"\n'
            '  [[ "${FAIL_STEP:-}" != recon ]] || return 207\n'
            '  cp gemc.hipo recon.hipo\n'
            '}\n'
            'test_hipo_file() { "$@"; }\n'
            'hipo-utils() {\n'
            '  echo "hipo $*" >> "$TRACE"\n'
            '  [[ "${FAIL_STEP:-}" != "$1" ]] || return 214\n'
            '  if [[ "$1" == -filter ]]; then cp recon.hipo dst.hipo; else test -s "$2"; fi\n'
            '}\n'
            'pelican() { printf input > lund.dat; }\n'
            'print_timing_summary() { :; }\n'
        )
        token = self.work / "token"
        token.write_text("dummy")
        self.env = dict(os.environ, SIMGRID_FUNCTIONS_FILE=str(functions), TRACE=str(self.trace),
                        SIMGRID_TASK_ID="17", SIMGRID_TASK_SEED="100017", SIMGRID_TOKEN_READY="1",
                        BEARER_TOKEN_FILE=str(token), SLURM_JOB_ID="123")

    def run_workflow(self, workflow):
        args = ["bash", str(NERSC / f"nodescript-{workflow}.sh"), "500"]
        if workflow == "lund":
            args.append("osdf:///input/dis1.dat")
        return subprocess.run(args, cwd=self.work, env=self.env, capture_output=True, text=True)

    def test_both_workflows_reconstruct_validate_and_retain_only_dst(self):
        for workflow in ("lund", "clasdis"):
            with self.subTest(workflow=workflow):
                result = self.run_workflow(workflow)
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                commands = self.trace.read_text()
                self.assertIn("-N=500", commands)
                self.assertIn("-RANDOM=100017", commands)
                self.assertIn("-- -Xmx1920m", commands)
                self.assertIn("hipo -test recon.hipo", commands)
                self.assertIn("MC::Lund,MC::Event,RICH::Particle,RICH::Ring", commands)
                self.assertLess(commands.index("recon /"), commands.index("hipo -test recon.hipo"))
                dst = list(self.work.glob(f"output-*/{workflow}-*123-17.hipo"))
                self.assertEqual(len(dst), 1)
                self.assertFalse((dst[0].parent / "gemc.hipo").exists())
                self.assertFalse((dst[0].parent / "recon.hipo").exists())
                self.trace.unlink()

    def test_reconstruction_and_integrity_failures_do_not_create_dst(self):
        for step in ("recon", "-test", "-filter"):
            with self.subTest(step=step):
                self.env["FAIL_STEP"] = step
                result = self.run_workflow("clasdis")
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("DST output:", result.stdout)


class TaskFarmerLayoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.work = Path(self.temp.name).resolve()
        self.env = dict(os.environ, SCRATCH=str(self.work), SLURM_JOB_ID="123", SLURM_NNODES="2",
                        SIMGRID_FULL_PREPARE_ONLY="1")

    def prepare(self, layout):
        result = subprocess.run(["bash", str(NERSC / "full-taskfarmer.sh"), layout, "image:test"],
                                env=self.env, capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return self.work / "simgrid" / f"full-{layout.lower()}" / "123"

    def test_layouts_have_identical_200_task_workloads_and_resume_preserves_state(self):
        for layout in ("B", "C"):
            with self.subTest(layout=layout):
                campaign = self.prepare(layout)
                tasks = [shlex.split(line) for line in (campaign / "tasks.txt").read_text().splitlines()]
                self.assertEqual(len(tasks), 200)
                self.assertEqual([int(task[4]) for task in tasks], list(range(200)))
                self.assertEqual(sum(task[5] == "lund" for task in tasks), 100)
                self.assertEqual(sum(task[5] == "clasdis" for task in tasks), 100)
                self.assertEqual(len({task[7] for task in tasks if task[5] == "lund"}), 4)
                progress = campaign / "progress.tasks.txt.tfin"
                progress.write_text("existing progress")
                self.assertEqual(self.prepare(layout), campaign)
                self.assertEqual(progress.read_text(), "existing progress")

    def test_b_uses_fresh_containers_and_c_reuses_one_container_and_renews_once(self):
        bin_dir = self.work / "bin"
        bin_dir.mkdir()
        calls = self.work / "calls"
        mock = bin_dir / "podman-hpc"
        mock.write_text(
            '#!/bin/bash\n'
            'printf "%s\\n" "$*" >> "$CALLS"\n'
            'case "$1 $2" in\n'
            '  "container exists") test -f "$CONTAINER_EXISTS"; exit $? ;;\n'
            '  "run --rm") touch "$CONTAINER_EXISTS" ;;\n'
            'esac\n'
            'exit "${MOCK_EXIT:-0}"\n'
        )
        mock.chmod(0o755)
        # A tiny flock stub suffices for these sequential calls; real host serialization uses flock.
        flock = bin_dir / "flock"
        flock.write_text("#!/bin/bash\nexit 0\n")
        flock.chmod(0o755)
        self.env.update(PATH=str(bin_dir) + os.pathsep + os.environ["PATH"], CALLS=str(calls),
                        CONTAINER_EXISTS=str(self.work / "container"))
        for layout in ("B", "C"):
            campaign = self.prepare(layout)
            for task_id in (0, 2):
                result = subprocess.run(
                    ["bash", str(campaign / "scripts/full-task.sh"), str(campaign), layout,
                     str(task_id), "lund", "image:test", "osdf:///input/dis1.dat"],
                    env=self.env, capture_output=True, text=True,
                )
                self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
                self.assertEqual((campaign / f"jobs/{task_id}/exit-code").read_text().strip(), "0")
            commands = calls.read_text().splitlines()
            if layout == "B":
                self.assertEqual(sum(line.startswith("run ") for line in commands), 2)
                self.assertTrue(all("--env SIMGRID_TASK_SEED" in line for line in commands))
            else:
                self.assertEqual(sum(line.startswith("run ") for line in commands), 1)
                self.assertEqual(sum("zsh /sshkeys/token-renew.zsh" in line for line in commands), 1)
                self.assertEqual(sum(line.startswith("exec --workdir") for line in commands), 2)
            calls.unlink()
            (self.work / "container").unlink(missing_ok=True)

    def test_task_startup_failure_is_recorded_and_returned(self):
        campaign = self.prepare("C")
        bin_dir = self.work / "bin"
        bin_dir.mkdir()
        for name, body in (("podman-hpc", "exit 23"), ("flock", "exit 0")):
            command = bin_dir / name
            command.write_text(f"#!/bin/bash\n{body}\n")
            command.chmod(0o755)
        self.env["PATH"] = str(bin_dir) + os.pathsep + os.environ["PATH"]
        result = subprocess.run(
            ["bash", str(campaign / "scripts/full-task.sh"), str(campaign), "C", "0",
             "lund", "image:test", "osdf:///input/dis1.dat"], env=self.env,
        )
        self.assertEqual(result.returncode, 23)
        self.assertEqual((campaign / "jobs/0/exit-code").read_text().strip(), "23")

    def test_driver_checks_all_task_outcomes_and_cleans_up_shared_containers(self):
        bin_dir = self.work / "bin"
        bin_dir.mkdir()
        farmer = bin_dir / "runcommands.sh"
        farmer.write_text(
            '#!/bin/bash\n'
            'for ((i=0; i<200; i++)); do\n'
            '  mkdir -p "jobs/$i"\n'
            '  code=0\n'
            '  if [[ "${FAIL_ONE:-0}" == 1 && "$i" == 199 ]]; then code=207; fi\n'
            '  printf "%s\\n" "$code" > "jobs/$i/exit-code"\n'
            'done\n'
        )
        farmer.chmod(0o755)
        srun = bin_dir / "srun"
        srun.write_text('#!/bin/bash\nprintf "%s\\n" "$*" >> "$CLEANUP_CALLS"\n')
        srun.chmod(0o755)
        self.env.update(PATH=str(bin_dir) + os.pathsep + os.environ["PATH"],
                        SIMGRID_FULL_PREPARE_ONLY="0", CLEANUP_CALLS=str(self.work / "cleanup"))
        for failed in ("0", "1"):
            with self.subTest(failed=failed):
                self.env["FAIL_ONE"] = failed
                result = subprocess.run(["bash", str(NERSC / "full-taskfarmer.sh"), "C", "image:test"],
                                        env=self.env, capture_output=True, text=True)
                self.assertEqual(result.returncode, 0 if failed == "0" else 1, result.stderr)
                self.assertIn("Completed: 200/200" if failed == "0" else "Completed: 199/200", result.stdout)
        cleanup = (self.work / "cleanup").read_text().splitlines()
        self.assertEqual(len(cleanup), 2)
        self.assertTrue(all("--ntasks=2" in line and "--cleanup" in line for line in cleanup))


if __name__ == "__main__":
    unittest.main()
