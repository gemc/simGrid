# NERSC

[Documentation Home](https://docs.nersc.gov)

### 1. Log into a login node

   From your Mac:

```shell
   ssh YOUR_USERNAME@perlmutter.nersc.gov
```    

Follow the password/MFA prompts. This connects to a login node, where you can inspect files, prepare
scripts, and submit jobs. Simulation execution belongs on allocated compute nodes.
NERSC login instructions (https://docs.nersc.gov/connect/#connecting-via-ssh).

Once connected:


```shell
hostname
id
echo "$SCRATCH"
```

An interactive compute-node shell is also possible through a Slurm allocation. Initially, a short batch
job gives us a reproducible test and a saved log.


### 2. Check the exact JLab CVMFS paths

   On the login node, run:
```shell
   ls -ld /cvmfs/jlab.opensciencegrid.org
```


   NERSC CVMFS support (https://docs.nersc.gov/services/cvmfs/).

   If those commands fail, send NERSC a help ticket with the hostname and exact errors:

   > Our CLAS12 simulation workflow requires jlab.opensciencegrid.org, including the Hall B CLAS12 software,
   > configuration files, and Geant4 modules. Could this repository be enabled on Perlmutter login and
   > compute nodes, including access inside supported containers?

### 3. Submit a small compute-node probe

   A successful login-node check needs a corresponding compute-node check.

   On NERSC:

   mkdir -p "$SCRATCH/nersc-pilot"
   cd "$SCRATCH/nersc-pilot"

   Create nersc-probe.sbatch there with this content, replacing YOUR_PROJECT:

   #!/bin/bash
   #SBATCH --job-name=nersc-probe
   #SBATCH --account=YOUR_PROJECT
   #SBATCH --constraint=cpu
   #SBATCH --qos=shared
   #SBATCH --nodes=1
   #SBATCH --ntasks=1
   #SBATCH --cpus-per-task=2
   #SBATCH --mem=2G
   #SBATCH --time=00:05:00
   #SBATCH --licenses=cvmfs
   #SBATCH --output=nersc-probe-%j.out

set -u

hostname
date
printf 'Job ID: %s\n' "$SLURM_JOB_ID"
printf 'Working directory: %s\n' "$PWD"

status=0
for path in \
/cvmfs/jlab.opensciencegrid.org/hallb/clas12/sw/modulefiles \
/cvmfs/jlab.opensciencegrid.org/geant4/modules \
/cvmfs/jlab.opensciencegrid.org/hallb/clas12/sw/noarch/clas12-config/prod
do
if ls -ld "$path"; then
ls "$path" | head -n 5
else
status=1
fi
done

exit "$status"

Submit and inspect it:

job_id=$(sbatch --parsable nersc-probe.sbatch)
echo "$job_id"
squeue -j "$job_id"

After it finishes:

cat "nersc-probe-${job_id}.out"
sacct -j "$job_id" --format=JobID,State,ExitCode,Elapsed,AllocCPUS

Expected result: the required directories are readable and the main job reports COMPLETED with
ExitCode=0:0. A queued job or a failed path check gives us a specific issue to investigate.

This requests a small shared allocation. On Perlmutter, Slurm counts hardware threads as CPUs;
two requested CPUs ordinarily correspond to one physical core, with memory also affecting allocation.
The CVMFS license lets scheduling account for service availability.
Shared jobs (https://docs.nersc.gov/jobs/examples/#shared),
CVMFS jobs (https://docs.nersc.gov/services/cvmfs/#cvmfs-batch-jobs),
job monitoring (https://docs.nersc.gov/jobs/monitoring/).

4. Validate the container, then the physics workflow

   After CVMFS works, pull our production image on the login node:

   podman-hpc pull docker.io/jeffersonlab/clas12software:production
   podman-hpc images

   NERSC documents that pulled images are automatically prepared for execution in jobs.
   Podman-HPC instructions (https://docs.nersc.gov/development/containers/podman-hpc/overview/#pulling-images).

   The next shared-node job should launch that image with CVMFS and its working directory mounted, then
   check:
    - JLab paths are readable inside the container.
    - Module initialization works.
    - The selected GEMC, generator, SQLite, Java, and coatjava versions resolve correctly.
    - Pelican is available.

   We should then advance through these tests:

   | Trial | What it establishes |
      |---|---|
   | GEMC-only, 10–100 events, internal generator | Simulation and configuration compatibility |
   | One external generator | Generator environment and seed handling |
   | One staged Lund input | File-input workflow |
   | Background merging using a staged background file | Shared storage and merging |
   | Reconstruction and HIPO validation | Complete processing chain |
   | Pelican download and upload | Connectivity, authorization, and reliable output delivery |
   | Several concurrent workflows | Directory isolation, memory use, and throughput |

   Use exact versions from a working portal submission and retain logs and commands. Once one workflow
   passes, we can increase concurrency.

   The existing generated worker script needs a small NERSC adaptation before use: it expects Condor
   staging and _CONDOR_CREDS. Its simulation command blocks are reusable.
   Current worker generation (generators/bash/generate_nodescript.py:143).
5. Build toward portal submission in stages

   I recommend a native Slurm backend for the first implementation. The progression would be:

   | Stage | Deliverable |
      |---|---|
   | Access and CVMFS | Successful compute-node probe |
   | Software compatibility | One validated containerized GEMC job |
   | Complete workflow | Reconstruction and verified output delivery |
   | Efficient execution | Shared jobs for development; packed nodes for throughput |
   | Submission adapter | Generate, submit, monitor, and cancel NERSC jobs from a command-line tool |
   | Portal pilot | Route selected development submissions through that adapter |
   | Production operation | Account permissions, credential renewal, monitoring, and recovery agreed with NERSC |

   The intended flow is:

   web_portal → submission database → background dispatcher
   ├─ OSG → HTCondor
   └─ NERSC → Superfacility API → Slurm

   NERSC’s Superfacility API supports remote job submission and monitoring. Its submission credentials have
   renewal requirements that we must address for unattended operation.
   API overview (https://docs.nersc.gov/services/sfapi/),
   authentication (https://docs.nersc.gov/services/sfapi/authentication/).

   Our repository would need:
    - An explicit execution backend and scheduler identifiers, alongside stable simulation task IDs.
    - Shared pipeline generation with backend-specific environment, staging, and transfer handling.
    - Slurm monitoring and completion checks that include successful output delivery.
    - Retries that preserve completed tasks and avoid duplicate execution.
    - Backend-specific capacity limits while retaining the portal’s pending-submission ordering.

   Current submission and monitoring assume HTCondor cluster IDs, so these are meaningful integration changes.
   The existing completion helper also derives candidates from a Condor-based snapshot; NERSC completion must
   use its own evidence.
   Submitter (osg_submit.py:365),
   completion logic (db_io/mark_completed_submissions.py:150).

Start with SSH and the four CVMFS path checks above. Share their output and your NERSC project name, and
we can tailor the first batch and container trials to your account. I checked the probe’s Bash syntax locally;
it has not been executed on NERSC. No repository files were changed.