# Default resource requests per job slot.
# These values are chosen to match the CLAS12 gemc simulation profile:
#   - single-threaded gemc → 1 CPU
#   - gemc peak RSS ≈ 1.8 GB; 2.256 GB gives ~25% headroom
#   - output hipo + scratch ≈ 1 GB; 2 GB covers typical jobs
# Adjust if running multi-threaded generators or larger detector configurations.

DEFAULT_CPUS   = 1
DEFAULT_MEMORY = "2.256 GB"
DEFAULT_DISK   = "2 GB"


def create_hardware(scard, cpus=None, memory=None, disk=None):
	"""
	Generate the HTCondor hardware resource request block.

	request_cpus
	    Number of CPU cores allocated to the job slot. gemc runs
	    single-threaded, so the default is 1. Multi-threaded generators
	    (e.g. Pythia8 with OpenMP) should set cpus accordingly.

	request_memory
	    RAM reserved for the job. HTCondor will evict or hold the job if
	    it exceeds this limit. The default (2.256 GB) covers the gemc peak
	    RSS with headroom. Background-merging jobs may need more.

	request_disk
	    Scratch disk space on the worker node used for temporary files,
	    intermediate evio output, and the hipo output before transfer.
	    The default (2 GB) is sufficient for typical single-job output.

	Args:
		scard:  SConfiguration instance (not used directly; included for
		        consistency with all other generator signatures). Default
		        hardware limits suit both type-1 and type-2 workloads;
		        type-2 jobs with background merging (scard.bkmerging) or
		        large lund files may need higher memory/disk overrides.
		cpus:   int, number of CPUs to request. Defaults to DEFAULT_CPUS.
		memory: str, memory string understood by HTCondor (e.g. "4 GB").
		        Defaults to DEFAULT_MEMORY.
		disk:   str, disk string understood by HTCondor (e.g. "5 GB").
		        Defaults to DEFAULT_DISK.

	Returns:
		str: HTCondor resource request block.
	"""
	cpus   = cpus   if cpus   is not None else DEFAULT_CPUS
	memory = memory if memory is not None else DEFAULT_MEMORY
	disk   = disk   if disk   is not None else DEFAULT_DISK

	return """# Hardware resource requests per job slot.
request_cpus   = {0}
request_memory = {1}
request_disk   = {2}

""".format(cpus, memory, disk)
