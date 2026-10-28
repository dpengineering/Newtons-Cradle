#!/bin/bash
set -euo pipefail

# Wrapped in main so bash has read the whole script before reset --hard rewrites it.
main() {
	cd "$(dirname "$(readlink -f "$0")")/.."
	export GIT_SSH_COMMAND="ssh -o BatchMode=yes -o ConnectTimeout=10"

	local previous
	previous=$(git rev-parse HEAD)
	if ! timeout 30 git fetch --quiet origin main; then
		echo "Fetch failed, keeping $(git rev-parse --short HEAD)"
		return
	fi

	git reset --quiet --hard origin/main
	if ! uv sync --locked --no-dev; then
		echo "uv sync failed at $(git rev-parse --short HEAD), restoring ${previous:0:7}" >&2
		git reset --quiet --hard "$previous"
		uv sync --locked --no-dev --offline
	fi
	echo "Running $(git rev-parse --short HEAD)"
}

main "$@"
exit
