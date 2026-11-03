To submit:

```
job_id=$(sbatch --parsable nersc-test.sbatch)
echo "$job_id"
squeue -j "$job_id"
```

Explanation: 

- `sbatch` submits the script to Slurm.
- `--parsable` returns the job ID without the usual descriptive message.
- `squeue`": check the jobs status

Status:



- `PD`: waiting for resources.
- `R`: running.
- `No job row`: it has left the queue; check the final outcome:

After it finishes:

```
cat "nersc-probe-${job_id}.out"
sacct -j "$job_id" --format=JobID,State,ExitCode,Elapsed,AllocCPUS
```
