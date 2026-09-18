#!/usr/bin/env bash
set -euo pipefail

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository"

missing=()
for command_name in conda python snakemake sinfo sacctmgr sbatch sacct; do
  if ! command -v "$command_name" >/dev/null; then
    missing+=("$command_name")
  fi
done

echo "SNAIRA-Splice SLURM site inspection"
echo "Repository: $repository"
echo "User: ${USER:-unknown}"
echo

if command -v conda >/dev/null; then
  echo "Conda base:"
  conda info --base
  echo
fi

echo "Controller software:"
if command -v python >/dev/null; then
  python --version
fi
if command -v snakemake >/dev/null; then
  printf 'Snakemake '
  snakemake --version
fi
if command -v python >/dev/null && python -c 'import snakemake_executor_plugin_slurm' >/dev/null 2>&1; then
  echo "SLURM executor plugin: OK"
else
  echo "SLURM executor plugin: MISSING"
fi
echo

if command -v sinfo >/dev/null; then
  echo "SLURM partitions:"
  sinfo -h -o '%P | state=%a | limit=%l | nodes=%D'
  echo
fi

if command -v sacctmgr >/dev/null; then
  echo "SLURM account associations:"
  sacctmgr show assoc user="${USER:-}" format=User,Account,Partition
  echo
fi

echo "Local launcher:"
launcher="scripts/slurm/submit_snaira_splice_controller.local.sh"
if [[ -f "$launcher" ]]; then
  echo "$launcher exists"
else
  echo "$launcher has not been created"
fi
echo

if ((${#missing[@]})); then
  echo "Missing required commands: ${missing[*]}" >&2
  exit 2
fi

echo "Inspection complete; no jobs were submitted and no files were changed."
