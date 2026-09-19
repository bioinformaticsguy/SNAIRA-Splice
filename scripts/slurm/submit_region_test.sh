#!/usr/bin/env bash
# Submit a prepared generic regional smoke test through the local SLURM launcher.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: submit_region_test.sh --sample-id ID --preflight|--submit [--configfile FILE]

Submit a regional SNAIRA-Splice smoke test after scripts/run_region_test.sh
has generated its single-sample configuration. Site account, partitions,
Conda paths, email, and allocations belong in the git-ignored local launcher.
EOF
}

sample_id=""
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
config_file="${config_file:-$repository/output/results/metadata/single_sample_input/$sample_id/config.yaml}"
[[ -s "$config_file" ]] || { echo "ERROR: generated run configuration is missing: $config_file" >&2; exit 2; }

launcher="$repository/scripts/slurm/submit_snaira_splice_controller.local.sh"
[[ -x "$launcher" ]] || {
  echo "ERROR: local SLURM launcher is missing. Copy and configure scripts/slurm/submit_snaira_splice_controller.local.example.sh first." >&2
  exit 2
}

if [[ "$mode" == "--preflight" ]]; then
  bash "$repository/scripts/slurm/check_slurm_profile.sh" "$config_file"
else
  bash "$launcher" --configfile "$config_file"
fi
