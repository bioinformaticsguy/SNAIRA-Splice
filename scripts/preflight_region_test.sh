#!/usr/bin/env bash
# Prepare and validate the default regional smoke test without submitting jobs.
set -euo pipefail

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$repository"

echo "[1/2] Preparing regional input and dry-running the workflow DAG"
bash scripts/run_region_test.sh --dry-run

echo "[2/2] Validating the SLURM profile without submission"
bash scripts/slurm/submit_region_test.sh --preflight

echo "Preflight passed. Submit the real run with:"
echo "  bash scripts/slurm/submit_region_test.sh --submit"
