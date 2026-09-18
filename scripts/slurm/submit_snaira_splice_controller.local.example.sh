#!/usr/bin/env bash
# Copy to submit_snaira_splice_controller.local.sh, edit, and do not commit it.
set -euo pipefail

export SNAIRA_MINIFORGE_PATH="/path/to/miniforge"
export SNAIRA_SNAKEMAKE_ENV="snaira-splice"
export SNAIRA_CONDA_PREFIX="/path/to/shared/snaira-splice-conda"
export SNAIRA_SHORT_PARTITION="short"
export SNAIRA_LONG_PARTITION="long"
export SNAIRA_SLURM_ACCOUNT=""
export SNAIRA_MAX_JOBS="40"
export SNAIRA_MAX_THREADS_PER_JOB="16"
export SNAIRA_MAIL_USER=""

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository"
mkdir -p logs
mail_args=()
[[ -z "$SNAIRA_MAIL_USER" ]] || mail_args=(--mail-type=END,FAIL --mail-user="$SNAIRA_MAIL_USER")
account_args=()
[[ -z "$SNAIRA_SLURM_ACCOUNT" ]] || account_args=(--account="$SNAIRA_SLURM_ACCOUNT")

sbatch --partition="$SNAIRA_SHORT_PARTITION" --time=3-00:00:00 --nodes=1 \
  --cpus-per-task=1 --mem=4G --job-name=snaira-splice-controller \
  --output=logs/%j_%u_%N_snaira_splice_controller.out \
  --error=logs/%j_%u_%N_snaira_splice_controller.err \
  "${account_args[@]}" "${mail_args[@]}" \
  scripts/slurm/run_snaira_splice_controller.sbatch "$@"
