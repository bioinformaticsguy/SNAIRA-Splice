#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: submit_kircherlab_region_test.sh --preflight | --submit

Use the verified Kircherlab SLURM settings for the prepared A4842_DNA_02
BRCA1-region smoke test. --preflight performs a dry run and submits no jobs.
EOF
}

case "${1:-}" in -h|--help) usage; exit 0 ;; esac
[[ $# -eq 1 ]] || { usage >&2; exit 2; }
mode="$1"
[[ "$mode" == "--preflight" || "$mode" == "--submit" ]] || { usage >&2; exit 2; }

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
sample_id="A4842_DNA_02"
work_root="/data/humangen_kircherlab/Users/hassan/snaira-splice-runs/${sample_id}_BRCA1"
config_file="$work_root/results/metadata/single_sample_input/$sample_id/config.yaml"

[[ -s "$config_file" ]] || {
  echo "ERROR: generated run configuration is missing: $config_file" >&2
  echo "Run first: bash scripts/run_kircherlab_region_test.sh --dry-run" >&2
  exit 2
}

export SNAIRA_MINIFORGE_PATH="/work/hassan/hassan/miniforge"
export SNAIRA_SNAKEMAKE_ENV="snaira-splice"
export SNAIRA_CONDA_PREFIX="/data/humangen_kircherlab/Users/hassan/conda/snaira-splice-rules"
export SNAIRA_SHORT_PARTITION="shortterm"
export SNAIRA_LONG_PARTITION="longterm"
export SNAIRA_SLURM_ACCOUNT="hassan"
export SNAIRA_MAX_JOBS="20"
export SNAIRA_MAX_THREADS_PER_JOB="16"
export SNAIRA_MAIL_USER="alihassan1697@gmail.com"

cd "$repository"

if [[ "$mode" == "--preflight" ]]; then
  bash scripts/slurm/check_slurm_profile.sh "$config_file"
  exit 0
fi

mkdir -p "$SNAIRA_CONDA_PREFIX" logs logs/slurm

mail_args=()
[[ -z "$SNAIRA_MAIL_USER" ]] || mail_args=(--mail-type=ALL --mail-user="$SNAIRA_MAIL_USER")
account_args=()
[[ -z "$SNAIRA_SLURM_ACCOUNT" ]] || account_args=(--account="$SNAIRA_SLURM_ACCOUNT")

sbatch --partition="$SNAIRA_SHORT_PARTITION" --time=3-00:00:00 --nodes=1 \
  --cpus-per-task=1 --mem=4G --job-name=snaira-splice-controller \
  --output=logs/%j_%u_%N_snaira_splice_controller.out \
  --error=logs/%j_%u_%N_snaira_splice_controller.err \
  "${account_args[@]}" "${mail_args[@]}" \
  scripts/slurm/run_snaira_splice_controller.sbatch --configfile "$config_file"
