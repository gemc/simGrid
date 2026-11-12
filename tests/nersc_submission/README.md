# Test Submissions

All jobs use `nersc_io/container.sh`. The available tests are:


- `environment.sbatch` runs `environment.sh` inside
`docker.io/jeffersonlab/clas12software:production`: a read-only probe that reports the system,
storage, available commands, and loaded modules (`report_environment nersc`).
- `pelican-transfer.sbatch` runs `pelican_transfer.sh` inside
`ghcr.io/gemc/simgrid:test`: it lists the test area, fetches the template
`dis.dat`, and uploads a copy under the first unused `dis<N>.dat` slot. It renews its
`osdf://jlab-osdf` token in-container with `token-renew.zsh`.
- `nersc-test-workflow.sbatch` runs the GEMC-only `nodescript.sh`; reconstruction will be added later.
- `lund-workflow.sbatch` runs `nodescript-lund.sh` as a Slurm job array, one task per row
in `lund_files`: each task renews its `osdf://jlab-osdf` token with `token-renew.zsh`, fetches its
Lund file from OSDF, and runs GEMC on it.

Each test writes its Slurm logs and job output into a directory named for the submission file
(`environment.sbatch` → `environment/`, `lund-workflow.sbatch` → `lund-workflow/`). Slurm does not
create it, so make the directory in the submission directory before submitting:

```
mkdir -p pelican-transfer
sbatch pelican-transfer.sbatch
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
cat "pelican-transfer/pelican-transfer-${job_id}.out"
sacct -j "$job_id" --format=JobID,State,ExitCode,Elapsed,AllocCPUS
```

Expected result: the main job reports COMPLETED with ExitCode=0:0. Missing optional tools and
uninitialized modules are reported without failing the environment report. The GEMC trial also
requires a readable detector gcard, a working `gemc` command, and nonempty output.

This requests a small shared allocation. On Perlmutter, Slurm counts hardware threads as CPUs;
two requested CPUs ordinarily correspond to one physical core, with memory also affecting allocation.

The launcher mounts `/cvmfs` read-only at the same path when `/cvmfs/jlab.opensciencegrid.org` is
available on the node, so GEMC resolves its config, geometry, fields, and modules from CVMFS; it
prints a warning and skips the mount when the repository is absent.
Shared jobs (https://docs.nersc.gov/jobs/examples/#shared),
CVMFS jobs (https://docs.nersc.gov/services/cvmfs/#cvmfs-batch-jobs),
job monitoring (https://docs.nersc.gov/jobs/monitoring/).

The GEMC trial defaults to `docker.io/jeffersonlab/gemc:dev-almalinux94`, already pulled with Podman-HPC,
and the detector gcard `/global/cfs/cdirs/m5464/clas12-config/main/gemc/dev/rga_fall2018.gcard`.

```shell
job_id=$(sbatch --parsable nersc-test-workflow.sbatch)
# After completion:
cat "nersc-workflow-${job_id}.out"
```

The optional arguments are `[gcard] [nevents] [image]`. The default event count is 100.
An empty gcard argument preserves the default. To select another image:

```shell
sbatch nersc-test-workflow.sbatch "" 100 docker.io/jeffersonlab/clas12software:production
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
directory read-only at the same absolute path, including related configuration files, and mounts
`/cvmfs` read-only at `/cvmfs` when the JLab repository is present. The batch job runs from
`$SCRATCH/simgrid/<test-name>`.
Each run creates a separate `output-<jobid>-<suffix>` directory there and retains `gemc.hipo` inside it.
The full output path is printed in the log. Slurm's log remains in the submission directory.

## Lund workflow

`lund-workflow.sbatch` runs the GEMC trial on staged Lund input instead of the internal
generator. It is a Slurm job array: each task reads one row of `lund_files` by its array index
(`sed -n "${SLURM_ARRAY_TASK_ID}p"`), so the array index is the row position and the filenames do not
matter. `nodescript-lund.sh` then fetches that file with `pelican object get <url> lund.dat` and runs
GEMC with `-INPUT_GEN_FILE="lund, lund.dat"`. Per-task logs are
`lund-workflow/lund-workflow-<arrayID>_<taskID>.out`.

The in-file default is `#SBATCH --array=1-4`, matching the four rows currently in `lund_files`. Submit
with that default, or size the array to the file's line count:

```shell
mkdir -p lund-workflow
sbatch lund-workflow.sbatch
sbatch --array=1-$(grep -c . lund_files) lund-workflow.sbatch
```

`#SBATCH --array` cannot size itself, so `nersc_io/submit-lund-workflow.sh` counts the rows and submits
the array in one step — the NERSC analog of the OSG `queue lundFile from lund_files` fan-out:

```shell
nersc_io/submit-lund-workflow.sh [gcard] [nevents] [image]
```

Each task fetches from OSDF, so it first renews an `osdf://jlab-osdf` bearer token by running
`/sshkeys/token-renew.zsh` in-container. The launcher mounts the host `$HOME/.ssh` (holding both
`id_ed25519` and `token-renew.zsh`) read-only at `/sshkeys`, and the token is written to
`$BEARER_TOKEN_FILE`. The job fails fast if no token is produced.

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
Use Slurm for simulation execution; a standalone invocation runs on the calling node. To run only the
environment report directly on a login node, use:

```shell
repo_dir="$HOME/software/simgrid/main"
source "$repo_dir/nersc_io/container.sh"
run_nersc_container docker.io/jeffersonlab/clas12software:production \
    "$repo_dir/tests/nersc_submission/environment.sh"
```

To open an interactive container shell on a login node:

```shell
podman-hpc run --rm -it --pull=never \
    --entrypoint /bin/bash \
    docker.io/jeffersonlab/clas12software:production -l
```

Replace the image reference to use another image already pulled with `podman-hpc pull`. Type `exit`
to return to the login-node shell. Add explicit volume mounts when host files are needed in the container.

The shared reporting API is:

```shell
source generators/bash/functions.sh
report_environment        # Common system, storage, commands, and loaded modules.
report_environment nersc  # Also report Slurm allocation and scratch location.
report_environment osg    # Also report selected HTCondor job and site metadata.
```

Run the API example from the repository root. Generated OSG workers invoke `report_environment osg`
after module setup. Reporting does not initialize modules or change the caller's shell options.
