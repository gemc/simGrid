# Dockerfiles for OSG/NERSC container


## Image Registry

Three images are build [by the CI](https://github.com/gemc/simGrid/actions/workflows/deploy.yml) 
and posted to the [registry](ghcr.io/gemc/simgrid)



## Build records

Each CI build uploads a gzip-compressed TAR archive named
`logs<run-number>-<attempt>-<variant>-<architecture>.tar.gz`, with a download link in the build job summary.
For example, `logs123-1-test-amd64.tar.gz` identifies the first attempt of run 123 for the x86_64 test image.
The archive contains Docker's structured build records, including logs and metadata; import it into Docker
Desktop to inspect the build. Records are exported for successful and failed builds when available.

## Publishing to OSG singularity

The process is automatic provided the wanted image is in the list at the 
[CVMFS cvmfs-singularity-sync](https://github.com/opensciencegrid/cvmfs-singularity-sync)
