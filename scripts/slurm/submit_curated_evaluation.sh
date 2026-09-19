#!/usr/bin/env bash
# Submit the prepared public curated-variant evaluation via SLURM.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: submit_curated_evaluation.sh --preflight|--submit

Run scripts/run_curated_evaluation.sh --dry-run first. The generated
single-sample configuration is then checked or submitted without modifying the
checked-in catalog or source VCF.
EOF
}

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
mode=""
while (($#)); do
  case "$1" in
    --preflight|--submit) mode="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ -n "$mode" ]] || { usage >&2; exit 2; }

sample_id="CURATED-SPLICE-1"
config_file="$repository/output/curated-evaluation/results/metadata/single_sample_input/$sample_id/config.yaml"
[[ -s "$config_file" ]] || { echo "ERROR: generated run configuration is missing: $config_file" >&2; exit 2; }

export SNAIRA_MINIFORGE_PATH="${SNAIRA_MINIFORGE_PATH:-/work/hassan/hassan/miniforge}"
export SNAIRA_SNAKEMAKE_ENV="${SNAIRA_SNAKEMAKE_ENV:-snaira-splice}"
export SNAIRA_CONDA_PREFIX="${SNAIRA_CONDA_PREFIX:-/data/humangen_kircherlab/Users/hassan/conda/snaira-splice-rules}"
export SNAIRA_SHORT_PARTITION="${SNAIRA_SHORT_PARTITION:-shortterm}"
export SNAIRA_LONG_PARTITION="${SNAIRA_LONG_PARTITION:-longterm}"
export SNAIRA_SLURM_ACCOUNT="${SNAIRA_SLURM_ACCOUNT:-hassan}"
export SNAIRA_MAX_JOBS="${SNAIRA_MAX_JOBS:-20}"
export SNAIRA_MAX_THREADS_PER_JOB="${SNAIRA_MAX_THREADS_PER_JOB:-16}"
export SNAIRA_VEP_MEM_MB="${SNAIRA_VEP_MEM_MB:-32768}"
export SNAIRA_SPLICEAI_MEM_MB="${SNAIRA_SPLICEAI_MEM_MB:-32768}"
export SNAIRA_MAIL_USER="${SNAIRA_MAIL_USER:-alihassan1697@gmail.com}"

if [[ "$mode" == "--preflight" ]]; then
  bash "$repository/scripts/slurm/check_slurm_profile.sh" "$config_file"
  exit 0
fi

mkdir -p "$SNAIRA_CONDA_PREFIX" logs logs/slurm
sbatch --partition="$SNAIRA_SHORT_PARTITION" --time=3-00:00:00 --nodes=1 \
  --cpus-per-task=2 --mem=64G --job-name=snaira-curated-controller \
  --output=logs/%j_%u_%N_snaira_curated_controller.out \
  --error=logs/%j_%u_%N_snaira_curated_controller.err \
  --account="$SNAIRA_SLURM_ACCOUNT" --mail-type=ALL --mail-user="$SNAIRA_MAIL_USER" \
  scripts/slurm/run_snaira_splice_controller.sbatch --configfile "$config_file"
