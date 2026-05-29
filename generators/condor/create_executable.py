def create_executable(scard):
	"""
	Generate the HTCondor executable and logging block.

	Executable
	    nodescript.sh is staged to the worker node and run directly by
	    HTCondor. It contains the full simulation pipeline and handles
	    its own output directory setup.

	Error / Output / Log
	    Per-job log paths using HTCondor's $(Cluster) and $(Process) macros:
	      $(Cluster)  — the ClusterId shared by all jobs in this submission
	      $(Process)  — the ProcId, unique per subjob (0, 1, 2, …)
	    Files are written under a 'log/' subdirectory on the submit node
	    inside the job's IWD (initial working directory). The directory must
	    exist before submission; it is created by the bash generator.

	    .err — stderr from the job (gemc output, generator stderr)
	    .out — stdout from the job
	    .log — HTCondor accounting: submit, execute, evict, terminate events

	+ProjectName
	    The OSG/XSEDE project name for fair-share accounting. Must be
	    double-quoted in the submit file. Taken from scard.project.
	    Incorrect or missing project names cause submission to be rejected
	    by the JLab OSG connect service.

	Args:
		scard:  SConfiguration instance. Uses scard.project.

	Returns:
		str: HTCondor executable and logging block.
	"""
	return """# Executable: simulation script staged to the worker node.
Executable = nodescript.sh

# Per-job log files ($(Cluster).$(Process) gives unique names per subjob).
Error  = log/job.$(Cluster).$(Process).err
Output = log/job.$(Cluster).$(Process).out
Log    = log/job.$(Cluster).$(Process).log

# OSG/XSEDE project for fair-share accounting.
+ProjectName = "{0}"

""".format(scard.project or "CLAS12")
