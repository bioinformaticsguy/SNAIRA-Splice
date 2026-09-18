#!/usr/bin/env bash
# Run Snakemake in one controller allocation; its executor submits rule jobs.
#SBATCH --job-name=snaira-splice-controller
#SBATCH --output=logs/%j_%u_%N_snaira_splice_controller.out
#SBATCH --error=logs/%j_%u_%N_snaira_splice_controller.err
set -euo pipefail

config_file="config/config.yaml"
workflow_profile="profiles/slurm"
extra_args=()
targets=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -c|--configfile) config_file="${2:?missing value for $1}"; shift 2 ;;
    --workflow-profile) workflow_profile="${2:?missing value for $1}"; shift 2 ;;
    --) shift; targets=("$@"); break ;;
    *) extra_args+=("$1"); shift ;;
  esac
done

: "${SNAIRA_MINIFORGE_PATH:?Set SNAIRA_MINIFORGE_PATH in the local launcher}"
: "${SNAIRA_SHORT_PARTITION:?Set SNAIRA_SHORT_PARTITION in the local launcher}"
: "${SNAIRA_LONG_PARTITION:?Set SNAIRA_LONG_PARTITION in the local launcher}"

project_dir="${SLURM_SUBMIT_DIR:-$PWD}"
cd "$project_dir"
[[ -f "$config_file" ]] || { echo "ERROR: missing config: $config_file" >&2; exit 2; }
[[ -f "$workflow_profile/config.yaml" ]] || { echo "ERROR: missing profile: $workflow_profile" >&2; exit 2; }
mkdir -p logs logs/slurm .snakemake/locks
exec > >(tee -a "logs/controller_$(date +%Y%m%dT%H%M%S)_${SLURM_JOB_ID:-manual}.log") 2>&1

source "$SNAIRA_MINIFORGE_PATH/etc/profile.d/conda.sh"
snakemake_env="${SNAIRA_SNAKEMAKE_ENV:-snaira-splice}"
conda activate "$snakemake_env"
python -c 'import snakemake_executor_plugin_slurm' >/dev/null || {
  echo "ERROR: SLURM executor plugin is unavailable in $snakemake_env" >&2
  exit 2
}

max_jobs="${SNAIRA_MAX_JOBS:-40}"
max_threads="${SNAIRA_MAX_THREADS_PER_JOB:-16}"
max_cores=$((max_jobs * max_threads))
conda_prefix_args=()
[[ -z "${SNAIRA_CONDA_PREFIX:-}" ]] || conda_prefix_args=(--conda-prefix "$SNAIRA_CONDA_PREFIX")
default_resources=(--default-resources mem_mb=2048 runtime=60 "slurm_partition=$SNAIRA_SHORT_PARTITION")
[[ -z "${SNAIRA_SLURM_ACCOUNT:-}" ]] || default_resources+=("slurm_account=$SNAIRA_SLURM_ACCOUNT")
long_rules=(
  "vep_annotate:slurm_partition=$SNAIRA_LONG_PARTITION"
  "spliceai_predict:slurm_partition=$SNAIRA_LONG_PARTITION"
)

snakemake --snakefile Snakefile "${targets[@]}" \
  --configfile "$config_file" --workflow-profile "$workflow_profile" \
  --jobs "$max_jobs" --cores "$max_cores" --keep-going \
  "${default_resources[@]}" --set-resources "${long_rules[@]}" \
  "${conda_prefix_args[@]}" "${extra_args[@]}"
