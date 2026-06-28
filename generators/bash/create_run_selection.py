"""
create_run_selection.py

Emit the nodescript.sh run-by-run selection section.

When a submission specifies `run_list`, each subjob simulates a single run drawn
at random, weighted by the per-run luminosity weights in runs.json. Both files —
runs.json and run_list.txt — are staged to the worker node (see osg_submit.py);
the draw itself is performed at runtime by select_weighted_run in functions.sh,
which delegates to select_run.py. This generator only wires the call that
captures the chosen run number into the `runno` bash variable.
"""

RUNS_JSON_FILE = "runs.json"
RUN_LIST_FILE  = "run_list.txt"


def create_run_selection(sconfiguration):
    """Return the bash block that sets `runno` from the weighted draw, or "".

    Returns "" when the submission has no run_list.
    """
    if not getattr(sconfiguration, 'run_list', None):
        return ""

    return (
        '\n# Run-by-run selection: pick one run weighted by luminosity\n'
        '# (from {runs_json}) restricted to the submitted runs ({run_list}).\n'
        'runno=$(select_weighted_run "{runs_json}" "{run_list}")\n'
        'echo "Run-by-run selection: runno=$runno"\n'
    ).format(runs_json=RUNS_JSON_FILE, run_list=RUN_LIST_FILE)
