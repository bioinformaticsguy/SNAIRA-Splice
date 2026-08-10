#!/usr/bin/env bash
set -euo pipefail
config_file="${1:-config/config.yaml}"
for command in snakemake conda; do command -v "$command" >/dev/null || { echo "ERROR: missing $command" >&2; exit 1; }; done
[[ -f "$config_file" ]] || { echo "ERROR: missing config: $config_file" >&2; exit 1; }
snakemake --configfile "$config_file" --lint
snakemake --configfile "$config_file" --dry-run
