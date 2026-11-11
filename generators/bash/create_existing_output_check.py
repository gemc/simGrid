"""Generate the startup check for a result uploaded by an earlier execution."""


def create_existing_output_check(sconfiguration, user_submission_id):
    """Finish successfully when the exact remote output passes hipo-utils -test."""
    return '''
# Check for output from an earlier execution before starting the simulation.
get_output_filename "{string_id}" "{submission_id}" "$sjob"
existing_output_uri="osdf:///jlab-osdf/clas12/volatile/osg/{username}/{submission_id}/${{OUTPUT_FILE}}"
# input: final output URI, output: existence check
cmd=("${{PELICAN_BIN:-/usr/bin/pelican}}" object ls "$existing_output_uri")
echo "Checking Existing Output: ${{cmd[@]}}"
if "${{cmd[@]}}"; then
    # input: existing remote output, output: existing-output.hipo
    cmd=("${{PELICAN_BIN:-/usr/bin/pelican}}" object get "$existing_output_uri" existing-output.hipo)
    echo "Fetching Existing Output: ${{cmd[@]}}"
    run_timed fetch_existing_output "${{cmd[@]}}"
    run_timed load_module "jdk/21.0.2"
    run_timed load_module "coatjava/{coatjavav}"
    run_timed require_executable "hipo-utils"
    # input: existing-output.hipo, output: integrity status
    cmd=(hipo-utils -test existing-output.hipo)
    echo "Testing Existing Output: ${{cmd[@]}}"
    run_timed test_existing_output "${{cmd[@]}}"
    rm -f existing-output.hipo
    echo "Existing output passed HIPO validation; job is already complete: $existing_output_uri"
    print_timing_summary
    exit 0
fi
echo "Final output was not found or could not be listed; continuing the simulation."
'''.format(
        string_id=(sconfiguration.string_id or "output").strip('-'),
        submission_id=user_submission_id,
        username=sconfiguration.username or "unknown",
        coatjavav=sconfiguration.coatjavav or "latest",
    )
