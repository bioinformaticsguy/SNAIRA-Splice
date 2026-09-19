#!/usr/bin/env bash
# Run the committed, cache-free SNAIRA-Splice synthetic workflow fixture.
set -euo pipefail

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository"

# Keep Snakemake's transient source cache outside the checkout. This also
# makes the helper usable from read-only repository mounts.
export XDG_CACHE_HOME="${XDG_CACHE_HOME:-${TMPDIR:-/tmp}/snaira-splice-cache}"
mkdir -p "$XDG_CACHE_HOME"

if ! command -v snakemake >/dev/null 2>&1; then
    echo "ERROR: snakemake is not available. Activate the snaira-splice Conda environment first." >&2
    exit 127
fi

snakemake --snakefile tests/Snakefile --cores 1 --forceall

report="tests/work/e2e/SYNTHETIC-1.snaira_splice.html"
test -s "$report"
printf 'Quick synthetic workflow test passed. Report: %s/%s\n' "$repository" "$report"
