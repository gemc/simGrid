# NERSC

[Documentation Home](https://docs.nersc.gov)

## Permutter

Perlmutter is the supercomputer at NERSC where we would run our simulations. It consists of thousands of
connected Linux computers, called nodes.

There are two kinds we would use:

- Login nodes: where you connect through SSH, prepare files, and submit jobs.
- Compute nodes: where Slurm schedules our GEMC instances to run.

So `ssh mungaro@perlmutter.nersc.gov` connects you to a login node belonging to that system.

NERSC is the facility; Perlmutter is the computing system.

<br/>

## Storage

CFS is shared disk space for active project work. HPSS is tape storage for long-term archiving.

|                  | CFS Shared Project Storage                                | HPSS Archival Storage                                       |
|------------------|-----------------------------------------------------------|-------------------------------------------------------------|
| Purpose          | Files you regularly access                                | Important datasets you rarely access                        |
| Access           | Normal directories and file operations                    | Explicit transfers using tools such as hsi, htar, or Globus |
| Typical contents | Inputs, scripts, configurations, logs, validation results | Archived simulation campaigns and preserved datasets        |
| Running jobs     | Files are directly accessible                             | Retrieve files to disk before processing                    |

To inquiry:

```shell
showquota m5464
```

<br/>

### CSF Directory for my project: `/global/cfs/cdirs/m5464`

- CFS documentation (https://docs.nersc.gov/filesystems/community/)
- HPSS documentation (https://docs.nersc.gov/filesystems/archive/).

<br/>

## Container Images

Podman runs containers, much like Docker.
It can download, build, list, and run the same standard container images, including our jeffersonlab/clas12software
images.
It supports running containers without administrator privileges. Podman documentation
(https://docs.podman.io/en/latest/)

Podman-HPC adds features for supercomputers. NERSC developed it to make Podman work efficiently across compute nodes,
including preparing images for shared storage and supporting facilities such as MPI and GPUs.
For our NERSC work, we use the podman-hpc command.
NERSC documentation (https://docs.nersc.gov/development/containers/podman-hpc/overview/)

The pieces have different roles:

| Component       | Role                                               |
|-----------------|----------------------------------------------------|
| Docker Hub      | Hosts the downloadable image                       |
| Container image | Provides the packaged software environment         |
| Podman-HPC      | Starts that environment on a NERSC node            |
| Slurm           | Allocates the node resources and schedules the job |

Our batch script will ask Slurm for resources, then use Podman-HPC to run the simulation inside the container.

```
podman-hpc pull docker.io/jeffersonlab/clas12software:production
podman-hpc pull docker.io/jeffersonlab/gemc:dev-almalinux94
podman-hpc images
```

NERSC documents that pulled images are automatically prepared for execution in jobs.
Podman-HPC instructions (https://docs.nersc.gov/development/containers/podman-hpc/overview/#pulling-images).

## Scrontab

Before each cron command, a #SCRON directive is needed. Parameters:

| Short option                | Equivalent long option    | Purpose                                   |
|-----------------------------|---------------------------|-------------------------------------------|
| -q cron                     | --qos=cron                | Select the cron service                   |
| -C cron                     | --constraint=cron         | Select nodes for cron tasks               |
| -A YOUR_PROJECT             | --account=YOUR_PROJECT    | Specify your project                      |
| -t 00:05:00                 | --time=00:05:00           | Set the maximum runtime                   |
| --open-mode=append          | Same                      | Append to the output log                  |
| -J simgrid-update           | --job-name=simgrid-update | Optional readable name in squeue          |
| -o /path/log-%j.out         | --output=/path/log-%j.out | Optional output location; %j means job ID |
| --mail-user=ungaro@jlab.org | Same                      | Email recipient                           |
| --mail-type=FAIL            | Same                      | Send email when a run fails               |

<br/>

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

<br/>

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

<br/>

### 3. Submit a small compute-node probe

See `tests/nersc_submission`


<br/>

### 4. Validate the container, then the physics workflow

The next shared-node job should launch that image with CVMFS and its working directory mounted, then
check:

- JLab paths are readable inside the container.
- Module initialization works.
- The selected GEMC, generator, SQLite, Java, and coatjava versions resolve correctly.
- Pelican is available.

We should then advance through these tests:

| Trial                                             | What it establishes                                       |
|---------------------------------------------------|-----------------------------------------------------------|
| GEMC-only, 10–100 events, internal generator      | Simulation and configuration compatibility                |
| One external generator                            | Generator environment and seed handling                   |
| One staged Lund input                             | File-input workflow                                       |
| Background merging using a staged background file | Shared storage and merging                                |
| Reconstruction and HIPO validation                | Complete processing chain                                 |
| Pelican download and upload                       | Connectivity, authorization, and reliable output delivery |
| Several concurrent workflows                      | Directory isolation, memory use, and throughput           |

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