def create_retry_policy(scard):
	"""
	Generate the HTCondor retry and hold policy block.

	on_exit_remove
	    Removes the job from the queue only when it exits cleanly (not via
	    signal and exit code == 0). Jobs that exit non-zero stay in the queue
	    so periodic_release can retry them.

	on_exit_hold
	    Places a job on hold whenever it exits via signal OR exits with a
	    non-zero code. This prevents immediate re-queuing and allows the
	    periodic_release expression to decide whether to retry.

	periodic_release
	    Releases a held job back to idle when ALL of the following are true:
	      - The job has been retried fewer than 5 times (NumJobCompletions < 5)
	      - The job has been held for more than 1 hour
	      - The exit code is one of the known transient OSG failure codes
	        (202, 204-208, 210-213), which indicate infrastructure issues
	        (e.g. CVMFS unavailable, pilot evicted) rather than job bugs.
	    Jobs that exceed 5 retries or exit with unexpected codes remain held
	    for manual inspection.

	Args:
		scard: SConfiguration instance (not used directly; included for
		       consistency with all other generator signatures). The retry
		       policy is identical for type-1 and type-2 submissions.

	Returns:
		str: HTCondor retry/hold policy block.
	"""
	transient_exit_codes = (
		"(ExitCode == 202) || "
		"(ExitCode == 204) || (ExitCode == 205) || (ExitCode == 206) || "
		"(ExitCode == 207) || (ExitCode == 208) || "
		"(ExitCode == 210) || (ExitCode == 211) || (ExitCode == 212) || (ExitCode == 213)"
	)

	return """# Retry policy
# Jobs exit cleanly (no signal, code 0) are removed from queue.
# Jobs that fail are held; periodic_release retries known transient failures.
on_exit_remove   = (ExitBySignal == False) && (ExitCode == 0)
on_exit_hold     = (ExitBySignal == True) || (ExitCode != 0)
periodic_release = (NumJobCompletions < 5) && ((CurrentTime - EnteredCurrentStatus) > (60*60)) && ({0})

""".format(transient_exit_codes)
