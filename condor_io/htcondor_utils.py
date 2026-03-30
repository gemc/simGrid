from typing import Dict, Optional, Any
from datetime import datetime, timezone

import htcondor2 as htcondor
from typing import Dict, Optional, Any

# HTCondor JobStatus codes
# 0 = UNEXPANDED, 1 = IDLE, 2 = RUNNING, 3 = REMOVED, 4 = COMPLETED, 5 = HELD, 6 = TRANSFERRING_OUTPUT, 7 = SUSPENDED
JOB_STATUS = {
	0: "UNEXPANDED",
	1: "IDLE",
	2: "RUN",
	3: "REMOVED",
	4: "DONE",
	5: "HOLD",
	6: "XFER",
	7: "SUSP",
}


def format_submitted_time(epoch: Optional[int]) -> str:
	"""
	Convert a UNIX epoch submit timestamp (QDate) into a local, human-readable string.

	Args:
		epoch: Submit time as UNIX epoch seconds (QDate). May be None.

	Returns:
		Formatted local time string "MM/DD HH:MM", or "-" if epoch is missing.
	"""
	if epoch is None:
		return "-"
	dt = datetime.fromtimestamp(epoch, tz=timezone.utc).astimezone()
	return dt.strftime("%m/%d %H:%M")


def get_owner_batches(owner: str) -> Dict[int, Dict[str, Any]]:
	"""
	Query the schedd for all jobs owned by `owner`, then group them by ClusterId.

	Important behavior:
	  - schedd.query() returns only jobs still present in the queue (not history).
	  - TotalSubmitProcs is the original batch size (what condor_q shows as TOTAL).

	Args:
		owner: Condor Owner (e.g. "gemc").

	Returns:
		Dict keyed by ClusterId. Each value contains:
		  - owner: owner string
		  - submitted_epoch: earliest QDate seen in the cluster (batch submit time)
		  - total_submit_procs: original batch size (TotalSubmitProcs)
		  - counts: RUN/IDLE/HOLD plus OTHER (UNEXPANDED/XFER/SUSP) currently in queue
		  - min_proc/max_proc: proc id range observed among jobs still in queue
	"""
	schedd = htcondor.Schedd()

	# Robust constraint: ensure Owner exists and matches exactly
	constraint = f'(Owner =!= UNDEFINED) && (Owner == "{owner}")'

	ads = schedd.query(
		constraint=constraint,
		projection=["Owner", "ClusterId", "ProcId", "JobStatus", "QDate", "TotalSubmitProcs",
		            "JobPrio"], )

	batches: Dict[int, Dict[str, Any]] = {}

	for ad in ads:
		cluster_id = ad.get("ClusterId")
		proc_id = ad.get("ProcId")
		status_code = ad.get("JobStatus")
		qdate = ad.get("QDate")
		total_submit_procs = ad.get("TotalSubmitProcs")

		if cluster_id is None:
			continue

		if cluster_id not in batches:
			batches[cluster_id] = {
				"owner":                  owner,
				"submitted_epoch":        qdate,
				"total_submit_procs":     int(total_submit_procs) if total_submit_procs is not None else None,
				"counts":                 {"RUN": 0, "IDLE": 0, "HOLD": 0, "OTHER": 0},
				"min_proc":               proc_id,
				"max_proc":               proc_id,
				"current_priority":       ad.get("JobPrio"),
				"current_priority_mixed": False,
			}

		b = batches[cluster_id]

		# Keep earliest submit time
		if qdate is not None:
			if b["submitted_epoch"] is None or qdate < b["submitted_epoch"]:
				b["submitted_epoch"] = qdate

		# TotalSubmitProcs should be the same for all procs in the cluster.
		# If it wasn't set on the first ad we saw, adopt it when we do see it.
		if b["total_submit_procs"] is None and total_submit_procs is not None:
			b["total_submit_procs"] = int(total_submit_procs)

		# Track current JobPrio across jobs in the cluster.
		# If all jobs agree, keep that value. If not, mark as mixed.
		job_prio = ad.get("JobPrio")
		if not b["current_priority_mixed"]:
			if b["current_priority"] is None:
				b["current_priority"] = job_prio
			elif job_prio is not None and job_prio != b["current_priority"]:
				b["current_priority_mixed"] = True

		# Track proc id range among jobs still present in the queue
		if proc_id is not None:
			if b["min_proc"] is None or proc_id < b["min_proc"]:
				b["min_proc"] = proc_id
			if b["max_proc"] is None or proc_id > b["max_proc"]:
				b["max_proc"] = proc_id

		# Count queue-resident states. DONE is computed later from TotalSubmitProcs.
		if status_code == 2:
			b["counts"]["RUN"] += 1
		elif status_code == 1:
			b["counts"]["IDLE"] += 1
		elif status_code == 5:
			b["counts"]["HOLD"] += 1
		elif status_code in (0, 6, 7):
			# UNEXPANDED / TRANSFERRING_OUTPUT / SUSPENDED are "not done" and still in queue
			b["counts"]["OTHER"] += 1
		else:
			# REMOVED (3) and COMPLETED (4) normally are not present in the queue.
			# If they appear transiently, condor_q's style is to treat them as DONE,
			# so we intentionally do not subtract them from DONE.
			pass

	return batches


def set_cluster_job_priority(cluster_id: int, priority: int) -> Any:
	"""
	Set JobPrio for all jobs in a given cluster.

	Args:
		cluster_id: HTCondor ClusterId.
		priority: Integer JobPrio to assign.

	Returns:
		Result from schedd.edit(...).
	"""
	schedd = htcondor.Schedd()
	return schedd.edit(
		job_spec=int(cluster_id),
		attr="JobPrio",
		value=str(int(priority)),
	)


def apply_priority_map(priority_map: Dict[int, Dict[str, Any]], skip_zero: bool = True) -> Dict[int, Dict[str, Any]]:
	"""
	Apply priorities from the internal priority map to HTCondor JobPrio.

	Args:
		priority_map: Mapping keyed by ClusterId, with each value containing
		              at least a 'priority' field.
		skip_zero: If True, do not edit clusters whose target priority is 0.

	Returns:
		Mapping:
		  {
		    ClusterId: {
		      "old_priority": old priority if uniform, else None,
		      "new_priority": target priority,
		      "result": raw schedd.edit(...) result,
		    }
		  }
	"""
	results: Dict[int, Dict[str, Any]] = {}

	for cluster_id, entry in priority_map.items():
		new_priority = int(entry["priority"])

		if skip_zero and new_priority == 0:
			continue

		old_priority = entry.get("old_priority")
		result = set_cluster_job_priority(int(cluster_id), new_priority)

		results[int(cluster_id)] = {
			"old_priority": old_priority,
			"new_priority": new_priority,
			"result": result,
		}

	return results