# CLAS12 Simulation Portal to OSG




## Submitting jobs to OSG

`osg_submit.py` drives the full submission pipeline. Run it with:

```bash
~/venv/pymysql/bin/python3 osg_submit.py [-b ID] [--devel] [--test] [--print-nodescript] [--print-condor-card]
```

### Steps executed

**1. Capacity check**
Queries HTCondor for the number of running + idle jobs owned by `gemc`.
If the count is above `--max-submitted-jobs` (default 80,000 in both production and `--devel`),
submission is aborted.
Requires the `htcondor2` Python package (available on the submit node); use `--test` to skip.

**2. Fetch job from the database**
Connects to `CLAS12OCR` (or `CLAS12TEST` with `--devel`) and retrieves the first job whose
`run_status` is `Not Submitted`, ordered by the smallest positive `submissions.priority`.
Legacy priority-0 rows are treated as the end of the queue rather than being ignored. Use
`-b ID` to target a specific `user_submission_id`.

**3. Parse the submission card**
The `scard` field stored in the database is parsed into an `SConfiguration` object that
drives all subsequent generation steps.

**3a. Mark job as Processing**
The row is atomically claimed by changing `run_status` from `Not Submitted` to `Processing`.
The remaining pending priorities are compacted to `1..N`. If another process claimed the row
first, this invocation exits without submitting it.

**3b. Create the job staging directory**
A per-submission directory is created on the submit node:

```
~/osgOutput/<username>/job_<user_submission_id>/
    log/              ← HTCondor per-job .err / .out / .log files
```

**4. For type-2 (lund-file) submissions: list and stage lund files**

The generator field in the scard must start with `/volatile/clas12/` — this is enforced
before any file operations begin.

`pelican object ls` is called on the OSDF mirror of that path to enumerate all lund files
(`.dat`, `.txt`, `.lund`).  Each OSDF URI is written as one line to
`~/osgOutput/<username>/job_<id>/lund_files`.  HTCondor reads this file with
`queue lundFile from lund_files` and creates one subjob per entry.

In test mode (`--test`) a three-file mockup is used when `pelican` is not available.

**5. Generate the HTCondor submit file**
`generate_condor_card()` assembles a complete `.sub` file in nine sections and writes it to
`~/osgOutput/<username>/job_<id>/clas12.condor`:

| Section | Content |
|---------|---------|
| Header | Universe, container image, site ranking |
| Retry policy | `on_exit_remove` / `on_exit_hold` / `periodic_release` rules |
| Requirements | Singularity, CVMFS, kernel version, glidein constraints |
| Undesired sites | `+UNDESIRED_Sites` exclusion list |
| Authentication | OAuth token for Pelican / OSDF transfers |
| Hardware | CPUs, memory, scratch disk per slot |
| Executable | `nodescript.sh`, log/output/error paths, `+ProjectName` |
| File transfer | Input staging and output retrieval |
| Queue | `Arguments` line per subjob and `Queue N` (or `queue lundFile from lund_files`) |

**6. Generate `nodescript.sh` and stage all scripts**
`generate_nodescript()` assembles the bash script that runs on each OSG worker node and
writes it directly to the staging directory.  The following files are then staged there:

```
~/osgOutput/<username>/job_<id>/
    clas12.condor                     ← HTCondor submit file
    nodescript.sh                     ← simulation script (executable on the worker node)
    generators/bash/functions.sh      ← shared bash helpers (path required by transfer_input_files)
    lund_files                        ← one OSDF URI per line (type-2 jobs only)
    log/                              ← HTCondor per-job log files
```

Every pipeline step in `nodescript.sh` follows the same pattern: a `# input/output` comment,
an explicit `cmd=(...)` array, a descriptive `echo "Running …: ${cmd[@]}"`, and
`run_timed <fn> "${cmd[@]}"`.

Upcoming in the next release: before downloading inputs or running the simulation, new jobs use
`pelican object ls` to check their exact final output URI. If it exists, the job downloads a temporary
copy and runs `hipo-utils -test`. Exit code zero completes the job successfully without rerunning
the workflow. A failed integrity check holds the job for manual cleanup at JLab; a failed download
returns a retryable infrastructure error. If the URI cannot be listed, the normal workflow continues.
Weighted run selection uses the submission ID and subjob number as a seed, so retries with unchanged
staged weights and run lists select the same run and check the same filename. No selection is stored.

Full pipeline (default):

```
preamble → environment variables → clean_and_check_environment
  → Pelican environment setup
  → [weighted run selection] → existing output check → setup_job_files
  → [fetch_background_file]            # only when bkmerging is set
  → lund_or_generator                  # pelican fetch (type-2) or run_generator cmd array
  → run_gemc                           # gemc.hipo
  → [merge_background]                 # gemc.merged.hipo — only when bkmerging is set
  → [run_denoiser]                     # gemc_denoised.hipo — only for coatjava < 14
  → run_reconstruction                 # recon.hipo
  → test_hipo_file                     # integrity check
  → create_dst                         # $OUTPUT_FILE
  → write_to_jlab                      # upload to OSDF
  → print_timing_summary
```

`nodescript.sh` sets `OSRELEASE=almalinux9-gcc11` before loading modules so CVMFS
modulefiles use the platform directory that contains GEMC, JDK, HIPO, and denoise.
For coatjava 14 and newer, the denoiser step is skipped and reconstruction reads
`gemc.merged.hipo` when background merging was requested, otherwise `gemc.hipo`.

GEMC-only pipeline (`output_type=1`): steps up to (and including) `merge_background` run
as normal; denoising, reconstruction, and DST are skipped; the gemc output file is renamed
to `$OUTPUT_FILE` and uploaded directly via `write_to_jlab`.

**7. Submit to HTCondor**

Runs `condor_submit` in the staging directory and records the returned cluster ID in
`submissions.pool_node`. A successful row becomes `Submitted to OSG`, receives `server_time`, and has
its MySQL pending priority cleared. If submission does not reach HTCondor, the row is restored
to `Not Submitted`. Every transition compacts the remaining pending priorities to `1..N`.

### Useful flags

| Flag | Effect |
|------|--------|
| `--test` | Skip HTCondor capacity check; use a pelican mock for lund-file lookups |
| `--devel` | Use `CLAS12TEST` database and the `devel` container image |
| `-b ID` | Process a specific `user_submission_id` instead of the next pending job |
| `--print-nodescript` | Print the generated `nodescript.sh` to stdout |
| `--print-condor-card` | Print the generated HTCondor submit file to stdout |
| `--target-site SITE` | Pin all jobs to one `GLIDEIN_Site` (e.g. `CNAF`) |

## Recovering jobs with existing output files

Upcoming in the next release: the scripts below identify output conflicts, validate the existing
HIPO results, and generate commands to remove the corresponding jobs from HTCondor. Run the Python
commands from a simGrid checkout. These recovery scripts support Python 3.6 and later and use only
the standard library. PyMySQL is not required; the scanner also needs `condor_q` on the submit node.

1. On the submit node, scan all submissions for ongoing Condor jobs:

   ```shell
   python3 condor_io/list_existing_outputs.py ~/osgOutput > files-to-review.txt
   ```

   The scanner queries the live queue for owner `gemc` (override with `--owner`). It reads logs only
   for idle, running, held, transferring, or suspended jobs; completed, removed, and historical jobs
   are excluded. If the query fails, scanning stops rather than including old submissions.
   Each output row contains a Condor job ID and JLab filesystem path separated by a tab. The ID
   comes from the `job.<cluster>.<process>.out` filename. Rows are unique per job and file pair.
   A conflict does not imply corruption; the existing file may be a completed result from an
   earlier attempt.

2. Copy the list to a JLab host where those files are accessible and `hipo-utils` is in `PATH`.
   Validate the files and generate a removal script:

   ```shell
   python3 condor_io/validate_review_outputs.py files-to-review.txt -o remove-verified-jobs.sh
   ```

   Job IDs are read directly from the list, so it can span portal submissions and Condor clusters.
   Each unique file is tested once; a passing file generates commands for all its associated jobs.
   A row with job ID `9624.6973` produces `condor_rm 9624.6973`. The process number must match the
   output filename. Old path-only lists still require `--cluster-id` and one portal submission.
   Only `hipo-utils -test` exit code zero qualifies. Missing files and failed tests produce no
   Condor removal commands.
   The output script must not already exist.

   Add `--remove-failed` to delete local HIPO files whose integrity tests return nonzero. Good files
   are preserved and still generate Condor removal commands. Without this flag, no HIPO files are
   deleted. Missing files are always skipped; failed deletions are reported and give a nonzero exit.

3. Review `remove-verified-jobs.sh`, copy it to the submit node, and execute it there:

   ```shell
   bash remove-verified-jobs.sh
   ```

Validation does not remove Condor jobs. It removes failed HIPO files only with `--remove-failed`.
Executing the generated script removes the listed Condor jobs while preserving their verified HIPO
results at JLab.

## Submission and priority workflow

The portal has two priority values with different scopes. Current HTCondor occupancy is an input
to the MySQL fair-share calculation, but the values and write targets remain separate.

- MySQL `submissions.priority` is the sequential portal queue position for `Not Submitted` rows;
  `db_io/priority_submissions.py` and `db_io/database.py` write it, and `osg_submit.py` consumes it.
  Priority 1 is next.
- HTCondor `JobPrio` is the runtime scheduling preference for jobs already in the local queue;
  `condor_io/run_priority_map.py` writes it, and the scheduler consumes it. Larger values run first.

The complete flow is:

```text
db_io/upload_submission.py
    -> MySQL: Not Submitted, appended to submissions.priority 1..N
    -> db_io/priority_submissions.py: recalculate the MySQL fair-share queue
    -> osg_submit.py: claim MySQL priority 1 and submit one HTCondor cluster
    -> MySQL: Submitted to OSG, pool_node = ClusterId, pending priority = 0
    -> condor_io/run_priority_map.py: calculate/apply HTCondor JobPrio

condor_io/list_owner_submission.py
    <- joins live HTCondor cluster counts to MySQL rows through pool_node = ClusterId
```

`update_simgrid.sh` only pulls repository updates. It does not calculate either priority value.

### 1. Create a MySQL submission: `db_io/upload_submission.py`

`db_io/upload_submission.py` reads a gcard, ensures that the user exists, and inserts one row in
the `submissions` table. The initial state is:

- `run_status = 'Not Submitted'`
- `client_time` set to the upload time
- `pool_node` does not yet contain an HTCondor `ClusterId`
- `priority` appended to the end of the current pending queue

The insert and renumbering are serialized with a MySQL advisory lock. Existing pending rows are
preserved in their current order, priority-0 legacy rows are placed at the tail, and the result is
compacted to `1..N`. The periodic fair-share calculation can subsequently reorder these rows.

### 2. Calculate the MySQL queue: `db_io/priority_submissions.py`

Upcoming in the next release: pending priorities count running plus idle HTCondor jobs and
preserve every waiting user's round allowance across recalculations.

This script calculates only `submissions.priority`; it never writes HTCondor `JobPrio`. It:

1. Reads submission users, IDs, timestamps, and statuses from MySQL.
2. Queries the live HTCondor batches owned by `gemc`.
3. Maps each `ClusterId` to a portal user through `submissions.pool_node` and sums that user's
   jobs in the HTCondor `RUN` and `IDLE` states separately.
4. Orders eligible users by ascending running-plus-idle job count. Work already waiting in Condor
   counts toward load even when none of it has started running.
5. Applies the selected history/aging algorithm among users with equal outstanding load. For
   `aging_interleaved`, users who have consumed their round allowance wait until the other
   waiting users have received their turns, including across recalculations.
6. Assigns each `Not Submitted` row a unique sequential priority from 1 through N.
7. Writes `submission_priorities.json` in the working directory.
8. With `--write-to-db`, uses one locked operation to clear non-pending priority values, write the
   calculated pending queue, and compact it to `1..N`.

On the submit node, the live running and idle counts come directly from the `htcondor2` Python bindings.
On the web server, where HTCondor is not installed, the calculation uses the latest
`owner_submission_snapshots` row written by `condor_io/list_owner_submission.py --store-db`. The
calculation stops with an error if neither source is available.
The console summary and JSON output include `running_jobs`, `idle_jobs`, and their sum,
`outstanding_jobs`, so the load used for ordering is visible.

The current production wrapper is equivalent to:

```bash
~/venv/pymysql/bin/python3 /path/to/simGrid/db_io/priority_submissions.py \
    -c msql_conn.txt \
    -d 60 \
    --priority-algorithm aging_interleaved \
    --half-life-days 3.0 \
    --history-half-life-days 5 \
    --queue-penalty-exponent 2.0 \
    --burst-per-user 2 \
    --write-to-db
```

These settings have the following effects:

- `-d 60` considers the last 60 days. The script aborts if an older pending row would be omitted.
- `aging_interleaved` alternates users in rounds instead of draining one user's queue at once.
- `--half-life-days 3.0` controls how quickly waiting age increases a submission's score.
- `--history-half-life-days 5` controls decay of earlier served-submission history.
- `--queue-penalty-exponent 2.0` strengthens the history/pending-load penalty.
- `--burst-per-user 2` allows at most two rows from one user in each interleaving round.

For non-pending history, `server_time` is preferred because it records when `osg_submit.py`
served the row; `client_time` is the fallback. On recalculation, the `server_time` sequence also
reconstructs each waiting user's consumed round allowance. Services before that user's oldest
remaining pending submission was created do not consume the current allowance. Missing or invalid
service timestamps are ignored for round reconstruction. Allowances reset once all waiting users
have received their turns; users without pending work do not block the next round. No additional
database table or persistent state file is required.

### 3. Consume the MySQL queue: `osg_submit.py`

Without `-b ID`, one invocation processes one portal submission:

1. Refuse new work when owner `gemc` is above the configured running-plus-idle job limit.
2. Select the `Not Submitted` row with the smallest positive MySQL priority. A legacy zero is
   selected only after all positive priorities.
3. Atomically change the row to `Processing` and compact the remaining pending queue to `1..N`.
4. Generate and store the worker and HTCondor scripts, then run `condor_submit`.
5. On success, set `run_status = 'Submitted to OSG'`, record `server_time` and the returned
   `ClusterId` in `pool_node`, clear the pending priority, and compact the queue.
6. On a recoverable failure, restore `Not Submitted` and compact the queue. A terminal Lund
   directory failure receives `Failed to Read Directory` and priority 0.

The `-b ID` option targets one submission explicitly instead of choosing priority 1. The atomic
claim still requires the row to be `Not Submitted`, preventing two processes from submitting it.
`--test` performs no MySQL status update and does not invoke `condor_submit`.

### 4. Calculate local runtime priority: `condor_io/run_priority_map.py`

This script calculates only HTCondor `JobPrio`; it never changes `submissions.priority`. It:

1. Queries live batches for the shared HTCondor owner `gemc`.
2. Selects the oldest `--max-running` clusters; production uses 20.
3. Computes their average number of running jobs.
4. Maps each selected cluster to an integer priority from -5 through 5. Below-average clusters
   receive positive values, and above-average clusters receive negative values.
5. With `--apply`, writes nonzero values to `JobPrio` for every job in the selected cluster.

Production runs this every ten minutes:

```cron
7-59/10 * * * * $sg/run_with_lock_and_log.zsh -l /home/gemc/logs \
    $sg/condor_io/run_priority_map.py -p -a -m 20
```

The calculation balances running jobs per cluster, not per portal user, because every cluster has
the same Condor owner. `-p` prints the old and proposed values; without `-a`, the command is a
read-only preview. Target priority 0 and unselected clusters are not written by the current apply
path.

### 5. Build the submissions display: `condor_io/list_owner_submission.py`

This script produces the combined data used by the portal submissions table. It:

1. Reads live HTCondor batches and their total, done, running, idle, and held job counts.
2. Joins each cluster to the newest matching MySQL row where `pool_node = ClusterId`.
3. Adds MySQL rows that have not reached Condor, including `Not Submitted` and terminal
   pre-submission failures.
4. Prints the result with `-q`, writes JSON with `-j FILE`, stores a database snapshot with
   `--store-db`, or reads the latest stored snapshot with `--from-db`.

The completed-events table sums hourly `global.done` counts from `timeline.json` in the repository root,
falling back to `~/timeline.json`, where the monitoring producer writes it on the submit host. Use
`--timeline-file /path/to/timeline.json` to select another location. The file is read directly on each refresh;
no separate tail file or cron job is required. Ten consecutive 24-hour intervals end at the
latest sample, with dates and exact interval endpoints in UTC. Sample ages are rounded to the nearest hour
relative to that sample to tolerate scheduling jitter; duplicate hourly slots use the newest sample.
Incomplete intervals display `N/A`, and an unreadable timeline omits the table with a warning. The timeline
contains global monitoring counts, shared across database views, rather than per-submission completion dates.
The portal converts jobs to events using 5,000 events per job. The completion rate used for time estimates
comes from the latest complete 24-hour timeline interval, matching the last column of the completed-events
table. If that interval is incomplete or the timeline is unavailable, the rate and dependent time estimates
display `N/A`. The old live Condor history counter has been retired: retained history may cover less than
24 hours and undercount completions. `--from-db` preserves stored rates and totals until a new snapshot
is built.

For a matched submission, the script initially reads Condor `JobPrio` but then replaces its
displayed `priority` field with MySQL `submissions.priority`. Therefore the portal table does not
show the runtime priority applied by `run_priority_map.py`; use that script's `-p` output to inspect
live `JobPrio` values.

Examples:

```bash
~/venv/pymysql/bin/python3 condor_io/list_owner_submission.py -q
~/venv/pymysql/bin/python3 condor_io/list_owner_submission.py -j submissions.json
~/venv/pymysql/bin/python3 condor_io/list_owner_submission.py --store-db
~/venv/pymysql/bin/python3 condor_io/list_owner_submission.py --from-db -q
~/venv/pymysql/bin/python3 condor_io/list_owner_submission.py -dev -q
```

### MySQL status and priority transitions

| `run_status` | Meaning | MySQL `submissions.priority` |
|--------------|---------|----------------------------------|
| `Not Submitted` | Waiting in the portal queue | Unique position from 1 through N |
| `Processing` | Claimed; unavailable to other submitters | Excluded from the pending queue |
| `Submitted to OSG` | HTCondor accepted the cluster | 0 |
| `Failed to Read Directory` | Terminal failure before HTCondor submission | 0 |

Only rows whose status is `Not Submitted` participate in the contiguous `1..N` invariant.

## Condor_io
