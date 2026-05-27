from generators.lund_helper import LUND_FILES


def create_queue(scard, user_submission_id):
    """
    Generate the HTCondor Arguments and Queue block.

    Type 1 — generator-based
        Queue N where N = scard.njobs (or scard.jobs).
        Each subjob receives: <user_submission_id> <$(Process)>
        $(Process) is used by nodescript.sh as a random seed.

    Type 2 — lund-file-based
        Uses HTCondor itemdata syntax:
          Arguments = <user_submission_id> $(Process) $(lundFile)
          queue lundFile from lund_files
        HTCondor reads lund_files line by line (one OSDF URI per line)
        and creates one subjob per entry, injecting the URI as $(lundFile).
        The lund_files file must be written by write_lund_files() before
        condor_submit is called and staged via transfer_input_files.

    Args:
        scard:               SConfiguration instance. Uses scard.type,
                             scard.njobs or scard.jobs (type 1).
        user_submission_id:  int, DB user_submission_id passed as first
                             argument to run.sh on each node.

    Returns:
        str: HTCondor Arguments and Queue block (always the last section
             of the submit file).
    """
    if scard.type == '2':
        return """# One subjob per lund file — HTCondor expands {lund_files} line by line.
Arguments = {uid} $(Process) $(lundFile)
queue lundFile from {lund_files}
""".format(uid=user_submission_id, lund_files=LUND_FILES)

    njobs_val = scard.njobs or scard.jobs
    njobs = int(njobs_val) if njobs_val else 1
    return """# Arguments passed to run.sh: <user_submission_id> <subjob_index>
Arguments = {uid} $(Process)
Queue {n}
""".format(uid=user_submission_id, n=njobs)
