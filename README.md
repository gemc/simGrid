# CLAS12 Simulation Portal to OSG




## Submitting jobs to OSG

`osg_submit.py` drives the full submission pipeline. Run it with:

```bash
~/venv/pymysql/bin/python3 osg_submit.py [-b ID] [--devel] [--test] [--print-nodescript] [--print-condor-card]
```

### Steps executed

**1. Capacity check**
Queries HTCondor for the number of running + idle jobs owned by `gemc`.
If the count is at or above `--max-submitted-jobs` (default 80 000), submission is aborted.
Requires the `htcondor2` Python package (available on the submit node); use `--test` to skip.

**2. Fetch job from the database**
Connects to `CLAS12OCR` (or `CLAS12TEST` with `--devel`) and retrieves the first job whose
status is *not submitted*. Use `-b ID` to target a specific `user_submission_id`.

**3. Parse the submission card**
The `scard` field stored in the database is parsed into an `SConfiguration` object that
drives all subsequent generation steps.

**3a. Mark job as Processing**
The `run_status` column in the database is immediately updated from `Not Submitted` to
`Processing`, preventing a concurrent `osg_submit.py` instance from picking up the same job.

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

Full pipeline (default):

```
preamble → environment variables → clean_and_check_environment → setup_job_files
  → Pelican environment setup
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

**7. Submit to HTCondor** *(not yet implemented)*

### Useful flags

| Flag | Effect |
|------|--------|
| `--test` | Skip HTCondor capacity check; use a pelican mock for lund-file lookups |
| `--devel` | Use `CLAS12TEST` database and the `devel` container image |
| `-b ID` | Process a specific `user_submission_id` instead of the next pending job |
| `--print-nodescript` | Print the generated `nodescript.sh` to stdout |
| `--print-condor-card` | Print the generated HTCondor submit file to stdout |
| `--target-site SITE` | Pin all jobs to one `GLIDEIN_Site` (e.g. `CNAF`) |

## Condor_io
