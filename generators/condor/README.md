# generators/condor

Assembles a complete HTCondor submit file from discrete section generators.
Each section is a single Python function in its own file.
`generate_condor_card.py` calls them in order and joins the results.

## Section sequence

```
generate_condor_card(scard, user_submission_id)
│
├─ 1. create_header(scard)
│       Universe = vanilla
│       +SingularityImage  (from scard.softwarev)
│       +SingularityBindCVMFS = True
│       Rank expression (site preference weights)
│
├─ 2. create_retry_policy(scard)
│       on_exit_remove   (clean exit only)
│       on_exit_hold     (non-zero / signal exit)
│       periodic_release (retry up to 5× for known transient OSG codes)
│
├─ 3. create_requirements(scard)
│       Requirements: HAS_SINGULARITY, HAS_CVMFS, kernel ≥ 2.17,
│                     CVMFS revision, glidein version
│
├─ 4. create_undesired(scard, undesired_sites=None)
│       +UNDESIRED_Sites  (comma-separated list of excluded GLIDEIN_Site names)
│
├─ 5. create_authentication(scard)
│       use_oauth_services = jlab_clas12
│       (CredMon injects BEARER_TOKEN_FILE used by Pelican on the node)
│
├─ 6. create_hardware(scard, cpus=None, memory=None, disk=None)
│       request_cpus   (default 1)
│       request_memory (default 2.256 GB)
│       request_disk   (default 2 GB)
│
├─ 7. create_executable(scard, user_submission_id)
│       Executable = run.sh
│       Error / Output / Log  (per-subjob paths under log/<user_submission_id>/)
│       +ProjectName          (from scard.project)
│
├─ 8. create_file_transfer(scard, extra_input_files=None)
│       transfer_input_files    = run.sh, nodeScript.sh  [+ extras]
│       should_transfer_files   = YES
│       when_to_transfer_output = ON_EXIT
│       transfer_output_files   = output
│
└─ 9. create_queue(scard, user_submission_id)          ← must be last
        Arguments = <user_submission_id> $(Process)
        Queue N
          type 1: N = scard.njobs
          type 2: N = count of lund files at scard.generator (via pelican)
```

## Submission types

| Type | `scard.generator` value | Queue N source |
|------|------------------------|----------------|
| 1    | generator executable name (e.g. `clasdis`, `dvcs`) | `scard.njobs` |
| 2    | `/volatile/clas12/...` path or `://` URL to lund files | `pelican object ls` count |

Type is auto-detected by `SConfiguration._resolve_type()` when not set
explicitly in the scard.

## Adding a new section

1. Create `create_<section>.py` with a function `create_<section>(scard, ...)`.
2. Import and call it in `generate_condor_card.py` at the correct position.
3. Add it to the sequence diagram above.
