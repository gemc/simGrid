"""Owner-authorized deletion requests, serialized with pending-submission claims."""

import re

from statuses import FAILED_TO_READ_DIRECTORY, NOTSUBMITTED, PROCESSING, SCRIPTS_GENERATED, TODELETE


PRE_SUBMIT_STATUSES = {NOTSUBMITTED, FAILED_TO_READ_DIRECTORY, SCRIPTS_GENERATED}


def cluster_id(value):
    """Accept only a positive, numeric HTCondor cluster ID."""
    text = str(value).strip()
    if not re.fullmatch(r"[0-9]+", text) or int(text) <= 0:
        raise ValueError("Submission has no valid HTCondor cluster ID.")
    return int(text)


def get_submission(db, submission_id):
    return db.query_one(
        "SELECT user_submission_id, user, run_status, pool_node, client_time, scard "
        "FROM submissions WHERE user_submission_id = %s",
        [submission_id],
    )


def request_deletion(db, submission_id, username):
    """Delete a pending row or enqueue cluster removal; never delete a processing row."""
    if not username:
        raise PermissionError("Authentication is required.")
    with db.pending_priority_lock():
        row = get_submission(db, submission_id)
        if row is None:
            raise LookupError("Submission was not found.")
        if row["user"] != username:
            raise PermissionError("Only the submitting user can delete this job.")
        status = row["run_status"]
        if status == PROCESSING:
            raise RuntimeError("Submission is being sent to HTCondor. Please try again shortly.")
        if status == TODELETE:
            return {"queued": True, "message": "Job is already scheduled for deletion."}

        no_cluster = str(row["pool_node"] or "").strip().upper() in {"", "NULL"}
        if no_cluster and status in PRE_SUBMIT_STATUSES:
            sql = "DELETE FROM submissions "
            params = []
            queued = False
        else:
            cluster_id(row["pool_node"])
            sql = "UPDATE submissions SET run_status = %s, priority = '0' "
            params = [TODELETE]
            queued = True
        affected = db.execute(
            sql + "WHERE user_submission_id = %s AND user = %s AND run_status = %s "
            "AND pool_node <=> %s",
            params + [submission_id, username, status, row["pool_node"]],
        )
        if affected != 1:
            raise RuntimeError("Submission changed. Reload its details and try again.")
        db._compact_pending_priorities_locked()
        return {
            "queued": queued,
            "message": (
                "Job is scheduled for deletion by the submit node."
                if queued else "Submission deleted."
            ),
        }
