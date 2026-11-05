#!/usr/bin/env bash
set -e

host=$(hostname -s)

if [[ "$host" == "gemc-rh9" ]]; then
	(cd "$HOME/simGrid" && git pull)
elif [[ "$host" == "scosg2202" ]]; then
	(cd "$HOME/software/simgrid/main" && git pull)
	(cd "$HOME/software/simgrid/dev" && git pull)
elif [[ -n "${NERSC_HOST:-}" || "$(hostname -f)" == *.nersc.gov ]]; then
	(cd "$HOME/software/simgrid/main" && git pull)
	(cd "$HOME/software/simgrid/dev" && git pull)
	(cd "/global/cfs/cdirs/m5464/clas12-config/main" && git pull)
	(cd "/global/cfs/cdirs/m5464/clas12-config/dev" && git pull)
	cp "$HOME/software/simgrid/main/nerc_io/token-renew" "$HOME/.ssh"
	cp "$HOME/.zshrc" "$HOME/.ssh"
else
	printf 'Unsupported host: %s\n' "$host" >&2
	exit 1
fi
