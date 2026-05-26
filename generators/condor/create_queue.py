from generators.lund_helper import count_files


def create_queue(scard, user_submission_id):
    """
    Generate the HTCondor Arguments and Queue block.

    Type 1 — generator-based
        The number of subjobs is read from scard.njobs (set in the scard by
        the user).  Each subjob runs the same generator executable with a
        different random seed derived from $(Process).

    Type 2 — lund-file-based
        The number of subjobs equals the number of lund files found at the
        directory given by scard.generator.  count_files() queries the OSDF
        via `pelican object ls` and counts entries with .dat/.txt/.lund
        extensions.  Each subjob reads one lund file, selected by $(Process).
        If pelican is not installed or the query fails, falls back to
        scard.njobs (with a warning printed to stdout).

    Arguments
        Two positional arguments are passed to run.sh for each subjob:
          1. user_submission_id — DB row identifier for this batch.
          2. $(Process) — HTCondor per-subjob index (0, 1, 2, …).

    Queue N
        Creates N subjobs (ProcId 0 … N-1) in a single cluster.

    Args:
        scard:               SConfiguration instance. Uses scard.type,
                             scard.njobs or scard.jobs (type 1), and
                             scard.generator (type 2). Both njobs and jobs
                             are accepted because DB scards may use either key.
        user_submission_id:  int, DB user_submission_id passed as first
                             argument to run.sh on each node.

    Returns:
        str: HTCondor Arguments and Queue block (always the last section
             of the submit file).
    """
    njobs_val = scard.njobs or scard.jobs

    if scard.type == '2':
        try:
            njobs = count_files(scard.generator)
        except (OSError, Exception) as e:
            njobs = int(njobs_val) if njobs_val else 1
            print(
                "Warning: pelican lund-file count failed ({}). "
                "Falling back to njobs = {}.".format(e, njobs)
            )
    else:
        njobs = int(njobs_val) if njobs_val else 1

    return """# Arguments passed to run.sh: <user_submission_id> <subjob_index>
# $(Process) runs from 0 to {0} - 1, one value per subjob.
Arguments = {1} $(Process)
Queue {0}
""".format(njobs, user_submission_id)
