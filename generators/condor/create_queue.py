from generators.lund_helper import LUND_FILES


def create_queue(scard):
    """
    Generate the HTCondor Arguments and Queue block.

    Type 1 — generator-based
        Queue N where N = scard.njobs (or scard.jobs).
        Each subjob receives: <$(Process)>
        $(Process) is the subjob index (0-based); used as sjob in nodescript.sh.

    Type 2 — lund-file-based
        Uses HTCondor itemdata syntax:
          Arguments = $(Process) $(lundFile)
          queue lundFile from lund_files
        HTCondor reads lund_files line by line (one OSDF URI per line)
        and creates one subjob per entry, injecting the URI as $(lundFile).
        The lund_files file must be written by write_lund_files() before
        condor_submit is called and staged via transfer_input_files.

    Args:
        scard:  SConfiguration instance. Uses scard.type,
                scard.njobs or scard.jobs (type 1).

    Returns:
        str: HTCondor Arguments and Queue block (always the last section
             of the submit file).
    """
    if scard.type == '2':
        return """# One subjob per lund file — HTCondor expands {lund_files} line by line.
Arguments = $(Process) $(lundFile)
queue lundFile from {lund_files}
""".format(lund_files=LUND_FILES)

    njobs_val = scard.njobs or scard.jobs
    njobs = int(njobs_val) if njobs_val else 1
    return """# Arguments passed to nodescript.sh: <sjob_index>
Arguments = $(Process)
Queue {n}
""".format(n=njobs)
