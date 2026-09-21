#!/usr/bin/env bash
# Submit the prepared regional smoke test through SLURM.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: submit_region_test.sh --preflight|--submit [--sample-id ID] [--configfile FILE]

Submit a regional SNAIRA-Splice smoke test after scripts/run_region_test.sh
has generated its single-sample configuration. Defaults target the current
cluster smoke test; command-line options override the sample and config file.
EOF
}

sample_id="A4842_DNA_02"
mode=""
repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
config_file=""
while (($#)); do
  case "$1" in
    --sample-id) sample_id="${2:?missing value}"; shift 2 ;;
    --preflight|--submit) mode="$1"; shift ;;
    --configfile) config_file="${2:?missing value}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ -n "$sample_id" && -n "$mode" ]] || { usage >&2; exit 2; }
config_file="${config_file:-$repository/output/region-test/metadata/single_sample_input/$sample_id/config.yaml}"
legacy_config_file="$repository/output/results/metadata/single_sample_input/$sample_id/config.yaml"
if [[ ! -s "$config_file" && -s "$legacy_config_file" ]]; then
  config_file="$legacy_config_file"
fi
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
else
  mkdir -p "$SNAIRA_CONDA_PREFIX" logs logs/slurm
  sbatch --partition="$SNAIRA_SHORT_PARTITION" --time=3-00:00:00 --nodes=1 \
    --cpus-per-task=2 --mem=64G --job-name=snaira-splice-controller \
    --output=logs/%j_%u_%N_snaira_splice_controller.out \
    --error=logs/%j_%u_%N_snaira_splice_controller.err \
    --account="$SNAIRA_SLURM_ACCOUNT" --mail-type=ALL --mail-user="$SNAIRA_MAIL_USER" \
    scripts/slurm/run_snaira_splice_controller.sbatch --configfile "$config_file"
fi
