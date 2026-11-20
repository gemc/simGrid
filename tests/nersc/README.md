# Test Submissions

All tests use the `ghcr.io/gemc/simgrid:test` image by default. Layout C manages its shared
container directly; the other tests use `nersc_io/container.sh`.
The available tests are:


- `environment.sbatch` runs `report_environment nersc`.
- `clasdis.sbatch` runs `nodescript-clasdis.sh`: the internal electron generator, GEMC,
   reconstruction, HIPO validation, and DST creation using the shared CVMFS environment.
- `pelican-transfer.sbatch` runs `pelican_transfer.sh` it lists the test area, fetches the template
   `dis.dat`, and uploads a copy under the first unused `dis<N>.dat` slot. It renews its
   `osdf://jlab-osdf` token in-container with `token-renew.zsh`.
- `lund.sbatch` runs `nodescript-lund.sh` as a Slurm job array, one task per row
   in `lund_files`: each task renews its `osdf://jlab-osdf` token with `token-renew.zsh`, fetches its
   Lund file from OSDF, and runs GEMC, reconstruction, HIPO validation, and DST creation.
- `full-b.sbatch` runs TaskFarmer with a separate container for each simulation task (layout B).
- `full-c.sbatch` runs TaskFarmer with one shared container per worker node (layout C).
   Each full test runs 100 clasdis jobs with 5,000 events per job.
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

### Where logs and working files go

These paths describe the NERSC batch scripts in this directory; they are not a rule for all Slurm or OSG jobs.
With the default submission settings:

| Files | Location |
|---|---|
| Slurm stdout and stderr for every test | `<submission-directory>/<test-name>/*.out` and `*.err` |
| B/C campaign files and TaskFarmer progress | `$SCRATCH/simgrid/full-b/<job_id>/` or `full-c/<job_id>/` |
| B/C per-task logs and result | `<campaign>/jobs/<task_id>/task.out`, `task.err`, and `exit-code` |
| Other tests' staged scripts and working data | `$SCRATCH/simgrid/<test-name>/` |

B and C have one Slurm log pair per allocation and a separate scratch log pair for each simulation task.
Standalone jobs and the Lund/generators arrays send worker stdout and stderr to their Slurm logs; they do
not create B/C-style `task.out`, `task.err`, or `exit-code` files. Arrays have one Slurm log pair per
array task.
The physics scripts print their exact `Output directory:` path in stdout.

`SIMGRID_FULL_CAMPAIGN` overrides the B/C scratch campaign path, including when resuming a campaign.
Slurm `--output`, `--error`, and `--chdir` options can also change the default log locations. Scratch files
remain after a job finishes unless removed separately; do not use the number of files as a success count.

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

For standalone jobs and arrays, count allocation/task records by state and exit code, excluding Slurm's
internal `.batch` and `.extern` steps:

```shell
sacct -X -j "$job_id" --noheader --parsable2 --format=State%30,ExitCode | sort | uniq -c
```

`COMPLETED|0:0` indicates success. `PENDING`, `RUNNING`, and `COMPLETING` are unfinished states;
terminal states such as `FAILED`, `CANCELLED`, `TIMEOUT`, `OUT_OF_MEMORY`, and `NODE_FAIL` indicate
unsuccessful jobs. Accounting may lag behind execution. For B/C, this command describes the allocation,
not the 100 simulations; use the task counts below.

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

## Memory requests, live usage, and completed-job accounting

Run these commands on NERSC. Set `job_id` to the allocation ID, or an individual array task such as
`123456_1` when inspecting one Lund/generators task. Resource allocation and measured usage are separate.

### Requested and allocated resources

```shell
job_id=61656225  # Replace with your job ID.
sacct -X -j "$job_id" --format=JobID,State,ReqMem,AllocTRES%80
```

Example from the two-task C validation run while it was running:

```text
JobID        State    ReqMem   AllocTRES
61656225     RUNNING  975604M  billing=512,cpu=512,mem=975604M,node=2
```

| Field | Meaning in this example |
|---|---|
| `RUNNING` | The Slurm allocation is active. |
| `ReqMem=975604M` | Memory requirement recorded by Slurm; this is not measured consumption. |
| `node=2` | Two allocated CPU nodes. |
| `cpu=512` | 512 logical CPUs, or 256 hardware threads per node with this allocation. |
| `mem=975604M` | Total allocated memory: about 953 GiB, or 476 GiB per node if evenly allocated. |
| `billing=512` | The allocation's scheduler accounting weight, matching its logical CPU count here. |

Slurm memory values use binary-scaled units: `975604M / 1024` is about 953 GiB. When `ReqMem` has
an `n` suffix, it denotes a per-node request; a `c` suffix denotes a per-CPU request. Use `AllocTRES`
to see the total allocation, and do not assume `ReqMem` is always a whole-job total.

`billing=512` is a resource weight. An hour at that weight represents 512 billing-unit-hours;
NERSC's charging policy determines the conversion to project allocation usage. The displayed value
does not measure CPU utilization, memory consumption, or elapsed time.

The B/C scripts request two nodes without an explicit `--mem`; inspect the granted memory rather
than assuming a limit. One node manages TaskFarmer and one runs the simulations, so those simulations
share the worker node's allocation, not the sum across both nodes. Standalone clasdis/Lund scripts
request `--mem=2500M`; generators/environment/transfer tests request `--mem=2G`.

### Memory statistics while a job is running

```shell
sstat --allsteps -j "$job_id" --format=JobID,NTasks,AveRSS,MaxRSS,MaxRSSNode

# Optional: refresh every ten seconds; press Ctrl-C to stop.
watch -n 10 "sstat --allsteps -j $job_id --format=JobID,NTasks,AveRSS,MaxRSS,MaxRSSNode"
```

| Field | Meaning |
|---|---|
| `JobID` | Slurm step ID, for example `61656225.0`. |
| `NTasks` | Number of Slurm tasks in that step, not the number of TaskFarmer simulations. |
| `AveRSS` | Average reported resident memory across the step's Slurm tasks. |
| `MaxRSS` | Largest reported Slurm-task resident-memory peak in the step. |
| `MaxRSSNode` | Node where that maximum was recorded. |

`MaxRSS` is a recorded peak, not instantaneous whole-node memory usage or a sum across both nodes.
For B/C, many simulations run within TaskFarmer's Slurm tasks; do not multiply `MaxRSS` by the
number of simulations. Accounting updates are sampled, and container/process attribution depends
on the site's accounting configuration. Blank statistics mean unavailable or uncollected data,
not zero usage. A blank field does not establish that a job fits its memory allowance.

### Memory and step results after completion

```shell
sacct -j "$job_id" --format=JobID%25,State,ReqMem,MaxRSS,MaxRSSNode

# Include exit codes and durations when investigating a failed step:
sacct -j "$job_id" --format=JobID%25,State%25,ExitCode,Elapsed,MaxRSS
```

Example from the same C run after both HIPO files reached JLab, before the cleanup handling fix:

```text
JobID             State       ReqMem    MaxRSS    MaxRSSNode
61656225          COMPLETED   975604M
61656225.batch    COMPLETED             34900K    nid004234
61656225.extern   COMPLETED
61656225.0        COMPLETED             6117676K  nid004234
61656225.1        FAILED                0         nid004235
```

| Record | Interpretation for this B/C launcher |
|---|---|
| `61656225` | Overall allocation; the driver reported success. |
| `.batch` | Campaign driver; `34900K` is about 34 MiB of reported peak resident memory. |
| `.extern` | Slurm's external-process tracking step, separate from the simulation workflow. |
| `.0` | TaskFarmer workload step; `6117676K` is about 5.83 GiB for its largest reported task peak. |
| `.1` | Subsequent shared-container cleanup step; investigate its failure in the Slurm stderr log. |

Step numbers describe this run's launch order; they are not universal names for workload and cleanup.
The overall job and workload completed, and both files arrived at JLab. The failed cleanup step
reported a Podman-HPC container-monitor shutdown error with exit 125. The driver tolerates cleanup
errors, so a cleanup failure can coexist with overall success. `0` in that step's `MaxRSS` field is
an accounting result, not evidence that its commands consumed no memory.

The 5.83 GiB value is not the combined consumption of both nodes or a proven per-simulation memory
requirement. A successful two-task run also does not establish the memory needed at 100-way
concurrency. Use task results and JLab output checks alongside Slurm accounting; see the
[B/C monitoring commands](#count-successful-and-failed-bc-tasks-during-or-after-a-run).

## clasdis workflow

`clasdis.sbatch` runs `nodescript-clasdis.sh`: GEMC with its internal electron generator
(`-INPUT_GEN_FILE=gemc_internal`, `-BEAM_P="e-, 4*GeV, 20*deg, 20*deg"`). Optional argument
`[nevents]` (default 200). It uses the shared `setup_test_environment` (below), loading `gemc` and
`sqlite` from CVMFS modules and taking the gcard from `${CLAS12_CONFIG}/gemc/<tag>/<config>.gcard`.

The launcher mounts the working directory (`$SCRATCH/simgrid/<test-name>`, holding the staged scripts
and receiving output), `/cvmfs`, and the host `.ssh` (at `/sshkeys`). `/cvmfs` is required, since the
software is loaded from CVMFS modules. Each run creates a separate `output-<jobid>-<suffix>` directory
under the working directory. After GEMC, both this workflow and the Lund workflow use the OSG test's
reconstruction command (`recon-util ... -- -Xmx1920m`), test `recon.hipo`, and apply the same DST bank
filter. The shared `create_dst` wrapper validates the final DST and removes `recon.hipo`; GEMC output
is removed after successful reconstruction. The resulting named DST stays in the output directory,
and its full path is printed in the log. The DST is also uploaded to JLab under a unique per-job path.
The standalone Lund and clasdis jobs request 30 minutes to accommodate reconstruction.

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
GEMC with `-INPUT_GEN_FILE="lund, lund.dat"`. At startup each task requests a Slurm name based on its
input basename, such as `lund-dis1.dat`. Pending tasks keep the initial `lund` name until they start.
Per-task logs are
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
produced. At startup each task requests a Slurm name such as `generators-clasdis`; pending tasks keep the
initial `generators` name until they start. Per-task logs are
`generators/generators-<arrayID>_<taskID>.out` and the matching `.err`.

Use a wider name column to display these names in accounting history:

```shell
sacct -u "$USER" --starttime today -X --format=JobID%25,JobName%40,State%20,ExitCode,Elapsed
```

Task naming uses `scontrol update JobId=<arrayID>_<taskID> JobName=<name>`. If the scheduler rejects the
rename, the test prints a warning and continues with the original name. See the
[Slurm array-task documentation](https://slurm.schedmd.com/job_array.html).

```shell
mkdir -p generators
sbatch generators.sbatch
sbatch --array=1-$(grep -c . generators_list) generators.sbatch
```

`generators_list` holds the generators from https://code.jlab.org/hallb/clas12/mcgen; edit it (and the
`--array` range) to add or remove generators.

## Full TaskFarmer comparison: B and C

See [README_b.md](README_b.md) for the per-task container walkthrough and
[README_c.md](README_c.md) for the shared-container walkthrough, including startup, physics steps,
outputs, monitoring, and restart behavior.

Upcoming in the next release: `full-b.sbatch` and `full-c.sbatch` run the same 100-task workload:
100 clasdis jobs with 5,000 requested events each. The clasdis workflow retains the existing internal
electron generator; it does not invoke the external `clasdis` executable. The full tests do not use
Lund inputs. Task IDs run from 0 through 99, with the same GEMC seed `100000 + task_id` in B and C.

Each test requests two full CPU nodes in the regular QOS: one TaskFarmer manager and one worker.
The CPU request exposes all 256 hardware threads per node. `THREADS=100` sets the worker's maximum
concurrent simulation tasks; it can be lowered before submission. There are 500,000 requested
events per test, or 1,000,000 across both layouts. These are two Slurm allocations, each containing
100 simulation tasks, rather than 200 separate Slurm submissions.

Submit from `tests/nersc` after pulling the image and preparing `$HOME/.ssh` as for the Lund test:

```shell
module load taskfarmer
mkdir -p full-b full-c
sbatch full-b.sbatch
sbatch full-c.sbatch
```

An optional first argument selects another image already pulled with `podman-hpc pull`. To lower
concurrency, submit with `THREADS=20 sbatch full-b.sbatch` and the same setting for C. Both use
the same shared CLAS12 defaults as the standalone tests. For a fair comparison, keep the image,
software versions, inputs, node count, and concurrency unchanged between the two runs.

Upcoming in the next release: `SIMGRID_FULL_TASKS=2 THREADS=2 sbatch full-c.sbatch` creates a fresh
two-task campaign for a smaller validation run; B accepts the same setting. The default remains 100
tasks, and each task still requests 5,000 events. The setting accepts 1 through 100 and applies only
when creating a task list. Resuming retains the original task count and script snapshots; see the
[C startup validation procedure](README_c.md#validate-the-startup-fix-before-another-full-campaign).

`full-taskfarmer.sh` snapshots the clasdis node script, shared functions, and task wrappers into
`$SCRATCH/simgrid/full-b/<job_id>/` or `full-c/<job_id>/`, then writes `tasks.txt` and starts
`runcommands.sh`. Each task has a separate `jobs/<task_id>/` directory with `task.out`, `task.err`,
an `exit-code` file, and an isolated output directory containing the validated DST. All tasks use
the internal generator. Success requires 100 zero exit-code records for a new campaign.
The batch log prints completed tasks and elapsed seconds; include the manager node when comparing
allocated node-hours. Slurm accounting alone describes the allocation, so also inspect task logs
and TaskFarmer's progress and error files.

### Count successful and failed B/C tasks, during or after a run

Upcoming in the next release: B/C task wrappers write `exit-code` when each task attempt exits.
`0` means the entire workflow succeeded, including validation and the JLab upload; a nonzero code means
that attempt failed. Use the campaign path printed in the Slurm `.out` log. For the example B campaign:

```shell
job_id=61609884
campaign="$SCRATCH/simgrid/full-b/$job_id"
# For C instead:
# job_id=61609889
# campaign="$SCRATCH/simgrid/full-c/$job_id"

task_status() {
    local campaign="$1" total task_id rc succeeded=0 failed=0
    total=$(awk 'END {print NR}' "$campaign/tasks.txt") || return 1
    for (( task_id=0; task_id<total; task_id++ )); do
        rc=$(cat "$campaign/jobs/$task_id/exit-code" 2>/dev/null) || rc=''
        case "$rc" in
            0) succeeded=$((succeeded + 1)) ;;
            ''|*[!0-9]*) ;;  # No complete numeric result yet.
            *) failed=$((failed + 1)) ;;
        esac
    done
    printf 'Successful: %s; failed: %s; no result: %s; total: %s\n' \
        "$succeeded" "$failed" "$((total - succeeded - failed))" "$total"
}

task_status "$campaign"
# Optional: refresh every ten seconds; press Ctrl-C to stop monitoring.
while true; do task_status "$campaign"; sleep 10; done
```

The same function works in Bash and Zsh, for both B and C. It checks the expected task IDs from 0 through
the task-list length minus one, so tasks that have not created a directory are still counted as having
no result. Counts are a live snapshot and can change while tasks finish.

While the campaign is running, **no result** includes queued and running tasks. After it finishes, a missing
result remains unknown: a hard kill or failure before the exit trap was installed can prevent a record.
Do not count these tasks as successful or assume they are still running. On a resumed campaign, records
describe the most recently recorded attempt; an older result remains visible until a new attempt exits.

List recorded failures with task IDs and exit codes, then inspect both logs for one failed task:

```shell
find "$campaign/jobs" -name exit-code -type f -exec grep -H -E '^[0-9]+$' {} + | grep -v ':0$'
task_id=37  # Replace with an ID from the failure list.
cat "$campaign/jobs/$task_id/task.err"
tail -n 80 "$campaign/jobs/$task_id/task.out"
squeue -j "$job_id"
sacct -j "$job_id" --format=JobID%25,State%20,ExitCode,Elapsed
```

No failure-list output means there are no recorded nonzero results; also check the **no result** count.
Common workflow codes include `204` for GEMC, `207` for reconstruction, `208` for DST creation, and
`214` for HIPO integrity. Read both task logs for the underlying error, including container-runtime errors.
TaskFarmer's `Remaining jobs` messages are not success/failure counts. The final `Completed: N/100` in
the Slurm `.out` log counts zero-valued task records; the driver requires all tasks to succeed and
TaskFarmer to exit successfully. Slurm accounting reports the overall outcome.

Each task sends its validated DST to JLab with Pelican. All HIPO files are placed directly inside
the allocation's job-ID directory:

```text
/volatile/clas12/osg/ungaro/test/
    full-b/<job_id>/clasdis-<job_id>-<task_id>.hipo
    full-c/<job_id>/clasdis-<job_id>-<task_id>.hipo
```

The corresponding OSDF destinations are
`osdf:///jlab-osdf/clas12/volatile/osg/ungaro/test/full-b/<job_id>/` and
`osdf:///jlab-osdf/clas12/volatile/osg/ungaro/test/full-c/<job_id>/`. Each task keeps its scratch
copy and reports a nonzero exit code if token initialization or the transfer fails.

- B calls the existing container launcher once per task, with up to 100 simultaneous containers on
  the worker node. Each task renews its token before uploading the DST to JLab.
- C starts a named container on first use of each worker node and uses `podman-hpc exec` for each
  task. Startup and token initialization are serialized with a host-local `flock`; the lock is
  released before simulation. Tasks reuse that container's token. Their physics files, shell
  environments, and logs remain in separate task directories.

For comparison, each task log records its launch delay from wrapper startup to the worker script.
This includes staging and container startup; in C it also includes shared startup and token-lock
waits. Stage timing summaries distinguish GEMC, reconstruction, validation, and Pelican uploads.
Compare launch delay, physics time, upload time, failures, and allocation node-hours separately.
Use matching image/software versions, resources, event counts, and seeds, and repeat runs before
drawing performance conclusions; network transfers and shared-service load can vary between runs.

C uses explicit container lifecycle management rather than inserting `shared-run` around individual
TaskFarmer commands: Podman-HPC's shared launcher expects coordinated parallel ranks. The batch script
attempts to stop shared containers on completion or interruption. Slurm termination and node failures
can prevent cleanup; inspect remaining containers on the affected node if needed. The early TERM
signal stops the driver before walltime, but does not checkpoint an in-flight physics process.

For a restart, set `SIMGRID_FULL_CAMPAIGN` to the original scratch campaign directory and submit the
same layout and image. The original task list, script snapshots, and TaskFarmer progress files are
preserved; TaskFarmer resumes unfinished tasks. A fresh submission without that override creates an
independent campaign. Keep one allocation per campaign directory at a time.

TaskFarmer's [worker and recovery model](https://docs.nersc.gov/jobs/workflow/taskfarmer/) and
Podman-HPC's
[shared launcher implementation](https://github.com/NERSC/podman-hpc/blob/main/podman_hpc/podman_hpc.py)
describe the underlying mechanisms. Local mocked tests check task counts, command sequencing,
container reuse, failure propagation, and event arguments. The B/C batch tests still require
execution on Perlmutter to establish runtime compatibility, memory use, and throughput.

## Container launcher

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
