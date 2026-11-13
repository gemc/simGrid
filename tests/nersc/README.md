# Test Submissions

All jobs use `nersc_io/container.sh` and the `ghcr.io/gemc/simgrid:test` image. 
The available tests are:


- `environment.sbatch` runs `report_environment nersc`.
- `clasdis.sbatch` runs `nodescript-clasdis.sh`: the GEMC-only trial with the internal electron
   generator; `gemc` is loaded from CVMFS modules via the shared `setup_test_environment`.
- `pelican-transfer.sbatch` runs `pelican_transfer.sh` it lists the test area, fetches the template
   `dis.dat`, and uploads a copy under the first unused `dis<N>.dat` slot. It renews its
   `osdf://jlab-osdf` token in-container with `token-renew.zsh`.
- `lund.sbatch` runs `nodescript-lund.sh` as a Slurm job array, one task per row
   in `lund_files`: each task renews its `osdf://jlab-osdf` token with `token-renew.zsh`, fetches its
   Lund file from OSDF, and runs GEMC on it.
- `generators.sbatch` runs `nodescript-generators.sh` as a Slurm job array, one task per
   row in `generators_list`: each task loads the `mcgen` module and runs that generator with
   `--trig 100 --docker`, confirming it produces output.

Each test writes separate Slurm stdout (`.out`) and stderr (`.err`) logs into a directory named for the
submission file (`environment.sbatch` → `environment/`, `lund.sbatch` → `lund/`). Slurm does not create
it, so make the directory in the submission directory before submitting:

```
mkdir -p pelican-transfer
sbatch pelican-transfer.sbatch
squeue -u mungaro
squeue -j <job_id>
```

To launch all .sbatch files in a directory:

```
for f in *.sbatch; do mkdir -p "${f%.sbatch}"; sbatch "$f"; done
```

To cancel selected jobs or all your jobs:

```
scancel 123456 123457          # kill several jobs by ID
scancel -u $USER               # kill ALL your jobs

```

Explanation: 

- `sbatch` submits the script to Slurm.
- `squeue`: check job status.

Status:

- `PD`: pending; the reason may indicate resource availability, a dependency, or a hold.
- `R`: running.
- `No job row`: it has left the queue; check the final outcome with `sacct`.

After it finishes:

```
job_id=123456  # Replace with the ID printed by sbatch.
cat "pelican-transfer/pelican-transfer-${job_id}.err"
cat "pelican-transfer/pelican-transfer-${job_id}.out"
sacct -j "$job_id" --format=JobID%25,State%20,ExitCode,Elapsed,AllocCPUS
```

Slurm records runtime failures as terminal states such as `FAILED`, `OUT_OF_MEMORY`, `TIMEOUT`, or
`NODE_FAIL`; it does not automatically keep them in a Condor-style `HOLD` queue. Use `squeue` for active
jobs and `sacct` for completed jobs. A Slurm hold is a pending-job condition, not a runtime failure report.
To see why an active job is pending:

```shell
squeue -j "$job_id" -o "%.20i %.12T %R"
```

For the Lund and generators arrays, `sacct -j "$job_id"` shows individual tasks; check every task's state
and exit code. Their logs use `<test-name>/<test-name>-<arrayID>_<taskID>.out` and the matching `.err`.
The container launcher returns the worker's nonzero exit code to the batch script so Slurm can record
the failure. An empty `.err` is not proof of success: some applications and shared worker functions print
failure messages to stdout, while warnings may appear on stderr. Check `State` and `ExitCode`, then read
both logs for details. These directives apply to newly submitted jobs; existing logs remain combined.

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

## clasdis (GEMC-only)

`clasdis.sbatch` runs `nodescript-clasdis.sh`: GEMC with its internal electron generator
(`-INPUT_GEN_FILE=gemc_internal`, `-BEAM_P="e-, 4*GeV, 20*deg, 20*deg"`). Optional argument
`[nevents]` (default 100). It uses the shared `setup_test_environment` (below), loading `gemc` and
`sqlite` from CVMFS modules and taking the gcard from `${CLAS12_CONFIG}/gemc/<tag>/<config>.gcard`.

The launcher mounts the working directory (`$SCRATCH/simgrid/<test-name>`, holding the staged scripts
and receiving output), `/cvmfs`, and the host `.ssh` (at `/sshkeys`). `/cvmfs` is required, since the
software is loaded from CVMFS modules. Each run creates a separate `output-<jobid>-<suffix>` directory
under the working directory and retains `gemc.hipo` inside it; the full path is printed in the log, and
the Slurm log stays in `<test-name>/` in the submission directory.

## Shared environment setup

The GEMC-based tests (clasdis, lund) and the OSG test node script all call
`setup_test_environment` in `generators/bash/functions.sh`. It exports
`CLAS12_CONFIG`/`OSRELEASE`/`RCDB_CONNECTION`, runs `clean_and_check_environment` and
`setup_job_files`, and takes every software version from the `CLAS12_*` defaults at the top of
`functions.sh` (`gemc/dev`, `sqlite/dev`, `jdk/21.0.2`, `coatjava/14.1.2`, config tag `dev`,
reconstruction `highlumi_stage2`/`mc-ai`). OSG and NERSC therefore exercise the same stack; override
any default in the environment before submitting.

## Lund workflow

`lund.sbatch` runs the GEMC trial on staged Lund input instead of the internal
generator. It is a Slurm job array: each task reads one row of `lund_files` by its array index
(`sed -n "${SLURM_ARRAY_TASK_ID}p"`), so the array index is the row position and the filenames do not
matter. `nodescript-lund.sh` then fetches that file with `pelican object get <url> lund.dat` and runs
GEMC with `-INPUT_GEN_FILE="lund, lund.dat"`. Per-task logs are
`lund/lund-<arrayID>_<taskID>.out` and the matching `.err`.

The in-file default is `#SBATCH --array=1-4`, matching the four rows currently in `lund_files`. Submit
with that default, or size the array to the file's line count:

```shell
mkdir -p lund
sbatch lund.sbatch
sbatch --array=1-$(grep -c . lund_files) lund.sbatch
```

`#SBATCH --array` cannot size itself, so `nersc_io/submit-lund.sh` counts the rows and submits
the array in one step — the NERSC analog of the OSG `queue lundFile from lund_files` fan-out:

```shell
nersc_io/submit-lund.sh [nevents] [image]
```

Each task fetches from OSDF, so it first renews an `osdf://jlab-osdf` bearer token by running
`/sshkeys/token-renew.zsh` in-container. The launcher mounts the host `$HOME/.ssh` (holding both
`id_ed25519` and `token-renew.zsh`) read-only at `/sshkeys`, and the token is written to
`$BEARER_TOKEN_FILE`. The job fails fast if no token is produced.

## Generators workflow

`generators.sbatch` is a smoke test for the mcgen event generators. It is a Slurm job array
over `generators_list` (one generator per row); each task loads the `mcgen` module and runs
`<generator> --trig <ntrig> --docker` (default `ntrig` 100), then checks a nonempty `.dat` was
produced. Per-task logs are `generators/generators-<arrayID>_<taskID>.out` and the matching `.err`.

```shell
mkdir -p generators
sbatch generators.sbatch
sbatch --array=1-$(grep -c . generators_list) generators.sbatch
```

`generators_list` holds the generators from https://code.jlab.org/hallb/clas12/mcgen; edit it (and the
`--array` range) to add or remove generators.

The shared host launcher handles mounts, metadata forwarding, and container startup. Additional
arguments are passed unchanged to the node script, and its exit code is returned to the caller.
From an interactive compute allocation, the equivalent standalone call is:

```shell
repo_dir="$HOME/software/simgrid/main"
export SIMGRID_FUNCTIONS_FILE="$repo_dir/generators/bash/functions.sh"
source "$repo_dir/nersc_io/container.sh"
mkdir -p "$SCRATCH/simgrid/clasdis"
cd "$SCRATCH/simgrid/clasdis"
run_nersc_container ghcr.io/gemc/simgrid:test \
    "$repo_dir/tests/nersc/nodescript-clasdis.sh"
```

The launcher stages `functions.sh` and the node script into the working directory (as HTCondor does
on OSG), then runs the staged node script there. It exposes `SIMGRID_FUNCTIONS_FILE` and
`SIMGRID_BACKEND` to the container. A caller can set `SIMGRID_FUNCTIONS_FILE` before launching to use a
different host copy of the shared functions.
Use Slurm for simulation execution; a standalone invocation runs on the calling node. To run only the
environment report directly on a login node, use:

```shell
repo_dir="$HOME/software/simgrid/main"
export SIMGRID_FUNCTIONS_FILE="$repo_dir/generators/bash/functions.sh"
source "$repo_dir/nersc_io/container.sh"
run_nersc_container ghcr.io/gemc/simgrid:test \
    "$repo_dir/tests/nersc/environment.sh"
```

To open an interactive container shell on a login node:

```shell
podman-hpc run --rm -it --pull=never \
    --entrypoint /bin/bash \
    ghcr.io/gemc/simgrid:test -l
```

Replace the image reference to use another image already pulled with `podman-hpc pull`. Type `exit`
to return to the login-node shell. Add explicit volume mounts when host files are needed in the container.

The shared reporting API is:

```shell
source generators/bash/functions.sh
report_environment        # Common system, storage, CVMFS, and loaded modules.
report_environment nersc  # Also report Slurm allocation and scratch location.
report_environment osg    # Also report selected HTCondor job and site metadata.
```

Run the API example from the repository root. Generated OSG workers invoke `report_environment osg`
after module setup. Reporting does not initialize modules or change the caller's shell options.
