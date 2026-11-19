# Job deletion

Open the submission details by clicking a submission ID or OSG ID. **DELETE JOB** appears only for
the authenticated submitting user. Deletion requires confirmation and a session request token; the
server checks ownership again using `REMOTE_USER` and the current MySQL row.

- A submission still waiting to be submitted is deleted from MySQL immediately. Pending queue
  positions are compacted under the same database lock used to claim submissions.
- A submission with an HTCondor cluster is marked `TODELETE`. This includes idle and held jobs.
  The submit node removes the remaining jobs and then deletes the MySQL submission row.
- A submission currently `Processing` cannot be deleted until its cluster ID has been recorded.
- Existing output files and historical monitoring snapshots are kept. The table reflects changes
  after the next scheduled status snapshot and page refresh.

The web server needs Python with `pymysql`, access to the existing MySQL credentials, PHP sessions,
and permission to execute `db_io/portal_submission.py`. It does not need HTCondor access.

On the submit node, inspect scheduled deletions with:

```shell
./condor_io/delete_jobs.py
./condor_io/delete_jobs.py --database=CLAS12TEST
```

The default is a dry run. Add `--apply` to run `condor_rm` and delete the matching rows. The worker
queries explicit cluster, owner, and status fields rather than JSON. A successful empty `condor_q`
result with no diagnostics also permits row deletion. Query errors, removal errors,
invalid cluster IDs, or a Condor owner other than `gemc` retain the row for retry and return failure.

Add these entries to the submit account's crontab, using its existing `sg`, `sgd`, `rll`, and `logs`
variables. The wrapper serializes runs and captures errors in the usual logs.

```cron
0-59/10 * * * * $rll -l $logs $sg/condor_io/delete_jobs.py --apply
1-59/10 * * * * $rll -l $logs $sgd/condor_io/delete_jobs.py --apply --database=CLAS12TEST
```
