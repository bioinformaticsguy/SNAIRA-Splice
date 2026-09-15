#!/usr/bin/env bash
# Validate the production DAG and SLURM tooling without submitting jobs.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: check_slurm_profile.sh CONFIG_FILE [Snakemake arguments] [-- targets...]

Environment:
  SNAIRA_WORKFLOW_PROFILE  Profile directory (default: profiles/slurm)
EOF
}

[[ $# -gt 0 ]] || { usage >&2; exit 2; }
case "${1:-}" in -h|--help) usage; exit 0 ;; esac
config_file="$1"
shift
workflow_profile="${SNAIRA_WORKFLOW_PROFILE:-profiles/slurm}"
extra_args=()
targets=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    --) shift; targets=("$@"); break ;;
    *) extra_args+=("$1"); shift ;;
  esac
done

[[ -f "$config_file" ]] || { echo "ERROR: missing config: $config_file" >&2; exit 2; }
[[ -f "$workflow_profile/config.yaml" ]] || { echo "ERROR: missing profile: $workflow_profile" >&2; exit 2; }
for command_name in snakemake python sbatch sacct; do
  command -v "$command_name" >/dev/null || { echo "ERROR: missing command: $command_name" >&2; exit 2; }
done
python -c 'import snakemake_executor_plugin_slurm' >/dev/null || {
  echo "ERROR: install snakemake-executor-plugin-slurm in the controller environment" >&2
  exit 2
}

snakemake --snakefile Snakefile "${targets[@]}" \
  --configfile "$config_file" --workflow-profile "$workflow_profile" \
  --jobs 1 --cores 1 --dry-run "${extra_args[@]}"
echo "SLURM preflight passed; no jobs were submitted."
