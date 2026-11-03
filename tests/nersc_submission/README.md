Both probes load the read-only report from `$HOME/software/simgrid/main/generators/bash/functions.sh`.
They can run from any submission directory. Keep the helpers available at that path on NERSC;
Slurm copies the batch script alone. The container probe mounts the shared helpers read-only and
runs them inside the GEMC image.

To submit from this directory:

```
sbatch --parsable nersc-test_environment.sbatch
squeue -u mungaro
squeue -j <job_id>
```

Explanation: 

- `sbatch` submits the script to Slurm.
- `--parsable` returns the job ID without the usual descriptive message.
- `squeue`: check job status.

Status:



- `PD`: waiting for resources.
- `R`: running.
- `No job row`: it has left the queue; check the final outcome:

After it finishes:

```
cat "nersc-probe-${job_id}.out"
sacct -j "$job_id" --format=JobID,State,ExitCode,Elapsed,AllocCPUS
```

Expected result: the main job reports COMPLETED with ExitCode=0:0. Missing optional tools and
uninitialized modules are reported without failing the probe.

This requests a small shared allocation. On Perlmutter, Slurm counts hardware threads as CPUs;
two requested CPUs ordinarily correspond to one physical core, with memory also affecting allocation.

These probes do not yet check CVMFS access.
Shared jobs (https://docs.nersc.gov/jobs/examples/#shared),
CVMFS jobs (https://docs.nersc.gov/services/cvmfs/#cvmfs-batch-jobs),
job monitoring (https://docs.nersc.gov/jobs/monitoring/).

The container probe uses the image already pulled with Podman-HPC:

```shell
job_id=$(sbatch --parsable nersc-test_gemc_image.sbatch)
# After completion:
cat "nersc-gemc-image-${job_id}.out"
```

The shared reporting API is:

```shell
source generators/bash/functions.sh
report_environment        # Common system, storage, commands, and loaded modules.
report_environment nersc  # Also report Slurm allocation and scratch location.
report_environment osg    # Also report selected HTCondor job and site metadata.
```

Run the API example from the repository root. Generated OSG workers invoke `report_environment osg`
after module setup. Reporting does not initialize modules or change the caller's shell options.
