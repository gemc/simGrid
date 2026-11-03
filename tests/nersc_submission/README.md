Both probes load the read-only report from `$HOME/software/simgrid/main/generators/bash/functions.sh`.
They can run from any submission directory. Keep the repository available at that path on NERSC;
Slurm copies the batch script alone. The container probe also uses `nersc_io/container.sh` and
`tests/nersc_submission/nodescript.sh` from the repository.

To submit from this directory:

```
sbatch nersc-test_environment.sbatch
squeue -u mungaro
squeue -j <job_id>
```

Explanation: 

- `sbatch` submits the script to Slurm.
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
uninitialized modules are reported without failing the environment report. The GEMC trial also
requires a readable detector gcard, a working `gemc` command, and nonempty output.

This requests a small shared allocation. On Perlmutter, Slurm counts hardware threads as CPUs;
two requested CPUs ordinarily correspond to one physical core, with memory also affecting allocation.

These probes do not yet check CVMFS access.
Shared jobs (https://docs.nersc.gov/jobs/examples/#shared),
CVMFS jobs (https://docs.nersc.gov/services/cvmfs/#cvmfs-batch-jobs),
job monitoring (https://docs.nersc.gov/jobs/monitoring/).

The GEMC trial defaults to `docker.io/jeffersonlab/gemc:dev-almalinux94`, already pulled with Podman-HPC,
and the detector gcard `/global/cfs/cdirs/m5464/clas12-config/main/gemc/dev/rga_fall2018.gcard`.

```shell
job_id=$(sbatch --parsable nersc-test_gemc_image.sbatch)
# After completion:
cat "nersc-gemc-image-${job_id}.out"
```

The optional arguments are `[gcard] [nevents] [image]`. The default event count is 100.
An empty gcard argument preserves the default. To select another image:

```shell
sbatch nersc-test_gemc_image.sbatch "" 100 docker.io/jeffersonlab/clas12software:production
```

The batch script defines resources and selects the image. `nodescript.sh` follows the command-array
and timing structure of the OSG worker, using GEMC's internal electron generator:

```shell
-INPUT_GEN_FILE=gemc_internal
-BEAM_P="e-, 4*GeV, 20*deg, 20*deg"
```

It uses GEMC from the container's PATH and preserves its initialized software environment. The trial
omits host CVMFS setup, Condor credentials, Lund downloads, background merging, reconstruction,
DST creation, and Pelican uploads. The gcard must reference geometry and other data available in
the image or mounted configuration tree.

The batch job sets `SIMGRID_CONFIG_DIR=/global/cfs/cdirs/m5464`. The launcher mounts that project
directory read-only at the same absolute path, including related configuration files. No CVMFS mount
is added. The batch job runs from `$SCRATCH/simgrid/gemc-tests`.
Each run creates a separate `output-<jobid>-<suffix>` directory there and retains `gemc.hipo` inside it.
The full output path is printed in the log. Slurm's log remains in the submission directory.

The shared host launcher handles mounts, metadata forwarding, and container startup. Additional
arguments are passed unchanged to the node script, and its exit code is returned to the caller.
From an interactive compute allocation, the equivalent standalone call is:

```shell
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"
export SIMGRID_CONFIG_DIR=/global/cfs/cdirs/m5464
mkdir -p "$SCRATCH/simgrid/gemc-tests"
cd "$SCRATCH/simgrid/gemc-tests"
run_nersc_container docker.io/jeffersonlab/gemc:dev-almalinux94 \
    "$repo_dir/tests/nersc_submission/nodescript.sh"
```

The launcher mounts the current directory read-write and the node script and shared functions read-only.
It exposes `SIMGRID_FUNCTIONS_FILE` and `SIMGRID_BACKEND` to the container. A caller can set
`SIMGRID_FUNCTIONS_FILE` before launching to use a different host copy of the shared functions.
Use Slurm for simulation execution; a standalone invocation runs on the calling node. Login-node
container tests should use a separate diagnostic script containing only environment checks.

The shared reporting API is:

```shell
source generators/bash/functions.sh
report_environment        # Common system, storage, commands, and loaded modules.
report_environment nersc  # Also report Slurm allocation and scratch location.
report_environment osg    # Also report selected HTCondor job and site metadata.
```

Run the API example from the repository root. Generated OSG workers invoke `report_environment osg`
after module setup. Reporting does not initialize modules or change the caller's shell options.
