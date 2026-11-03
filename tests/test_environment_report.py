"""Check environment diagnostics under strict shells and with scheduler metadata."""

import os
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest


FUNCTIONS_SH = Path(__file__).parents[1] / "generators" / "bash" / "functions.sh"


class EnvironmentReportTests(unittest.TestCase):
    def run_report(self, shell, commands, **variables):
        env = {name: value for name, value in os.environ.items()
               if not name.startswith(("SLURM_", "_CONDOR_", "BASH_FUNC_"))}
        env.update(variables)
        return subprocess.run(
            [shell, "-f", "-eu", "-c", 'source "$1"\n' + commands, shell, str(FUNCTIONS_SH)],
            env=env, capture_output=True, text=True, check=True,
        ).stdout

    def test_common_report_handles_unset_scheduler_variables_in_both_shells(self):
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                if not shutil.which(shell):
                    continue
                output = self.run_report(shell, "report_environment")
                self.assertIn("=== System ===", output)
                self.assertIn("=== Storage ===", output)
                self.assertIn("=== Available commands ===", output)
                self.assertIn("=== Loaded modules ===", output)
                self.assertIn("Bash:" if shell == "bash" else "Zsh:", output)
                self.assertNotIn("=== Slurm allocation ===", output)
                self.assertNotIn("=== OSG / HTCondor ===", output)

    def test_nersc_report_shows_allocation_with_defaults_for_missing_fields(self):
        output = self.run_report(
            "bash", "report_environment nersc", SLURM_JOB_ID="12345", SLURM_JOB_ACCOUNT="m5464",
        )
        self.assertIn("Job: 12345", output)
        self.assertIn("Account: m5464", output)
        self.assertIn("Partition: unset", output)
        self.assertNotIn("=== OSG / HTCondor ===", output)

    def test_osg_report_selects_metadata_without_dumping_credentials(self):
        with tempfile.TemporaryDirectory() as work_dir:
            job_ad = Path(work_dir) / "job.ad"
            machine_ad = Path(work_dir) / "machine.ad"
            job_ad.write_text('ClusterId = 123\nProcId = 4\nRequestCpus = 2\nToken = "secret-value"\n')
            machine_ad.write_text('GLIDEIN_Site = "TestSite"\nOtherAttribute = "private-value"\n')
            output = self.run_report(
                "bash", "report_environment osg", _CONDOR_JOB_AD=str(job_ad),
                _CONDOR_MACHINE_AD=str(machine_ad), BEARER_TOKEN="another-secret-value",
            )
        self.assertIn("ClusterId = 123", output)
        self.assertIn('GLIDEIN_Site = "TestSite"', output)
        self.assertNotIn("secret-value", output)
        self.assertNotIn("private-value", output)
        self.assertNotIn("=== Slurm allocation ===", output)

    def test_diagnostic_failures_and_module_changes_do_not_affect_the_caller(self):
        commands = """
module() { set +e; export MODULEPATH=changed; return 1; }
df() { return 1; }
export MODULEPATH=original
options_before=$-
report_environment osg
[[ "$options_before" == "$-" ]]
[[ "$MODULEPATH" == original ]]
printf 'Caller unchanged\\n'
"""
        for shell in ("bash", "zsh"):
            with self.subTest(shell=shell):
                if not shutil.which(shell):
                    continue
                output = self.run_report(shell, commands, _CONDOR_JOB_AD="/nonexistent/job.ad")
                self.assertIn("Unable to report working-directory storage.", output)
                self.assertIn("Unable to list loaded modules.", output)
                self.assertIn("Caller unchanged", output)


if __name__ == "__main__":
    unittest.main()
