#!/usr/bin/env bash
set -euo pipefail
python3 -m pytest
snakemake --snakefile tests/Snakefile --cores 1 --forceall
snakemake --configfile tests/config.test.yaml --dry-run --cores 1
