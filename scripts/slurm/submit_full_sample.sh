#!/usr/bin/env bash
# Submit a prepared complete single-sample SNAIRA-Splice run through SLURM.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: submit_full_sample.sh --preflight|--submit [--sample-id ID] [--outdir DIR]

Run scripts/run_full_sample.sh --dry-run first. This submits the generated
configuration without changing the source VCF or source manifest.
EOF
}

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
sample_id="A4842_DNA_02"
output_root="$repository/output/full-sample"
mode=""
while (($#)); do
  case "$1" in
    --sample-id) sample_id="${2:?missing value}"; shift 2 ;;
    --outdir) output_root="${2:?missing value}"; shift 2 ;;
    --preflight|--submit) mode="$1"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ -n "$mode" ]] || { usage >&2; exit 2; }
config_file="$output_root/metadata/single_sample_input/$sample_id/config.yaml"
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
# Full WGS with local unmasked SpliceAI at a 4,999-bp window merits long jobs.
export SNAIRA_VEP_RUNTIME="${SNAIRA_VEP_RUNTIME:-1440}"
export SNAIRA_SPLICEAI_RUNTIME="${SNAIRA_SPLICEAI_RUNTIME:-4320}"
export SNAIRA_MAIL_USER="${SNAIRA_MAIL_USER:-alihassan1697@gmail.com}"

if [[ "$mode" == "--preflight" ]]; then
  bash "$repository/scripts/slurm/check_slurm_profile.sh" "$config_file"
  exit 0
fi

cd "$repository"
mkdir -p "$SNAIRA_CONDA_PREFIX" logs logs/slurm
sbatch --partition="$SNAIRA_SHORT_PARTITION" --time=3-00:00:00 --nodes=1 \
  --cpus-per-task=2 --mem=64G --job-name=snaira-full-controller \
  --output=logs/%j_%u_%N_snaira_full_controller.out \
  --error=logs/%j_%u_%N_snaira_full_controller.err \
  --account="$SNAIRA_SLURM_ACCOUNT" --mail-type=ALL --mail-user="$SNAIRA_MAIL_USER" \
  scripts/slurm/run_snaira_splice_controller.sbatch --configfile "$config_file"
