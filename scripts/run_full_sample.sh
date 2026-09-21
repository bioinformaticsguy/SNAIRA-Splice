#!/usr/bin/env bash
# Prepare a one-sample full small-variant VCF run without modifying its source.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_full_sample.sh [--dry-run|--run-local] [options]

Create the generated manifest/configuration for one complete small-variant VCF.
The default is a validated cluster sample; override --vcf and --sample-id for
another sample. The source VCF and its index are read only.

Options:
  --vcf FILE             Source SNV/small-indel VCF.gz
  --sample-id ID         VCF sample ID
  --config FILE          Workflow configuration (default: config/cluster.yaml)
  --outdir DIR           Run root (default: output/full-sample)
  --dry-run              Generate the configuration and dry-run the complete DAG
  --run-local            Execute locally; never use this on a login node
  -h, --help             Show this help
EOF
}

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
source_vcf="/data/humangen_sfb1665_seqdata/short_read/processed_data/phase_i/A4842_DNA_02/snv_calls/A4842_DNA_02.pass.vcf.gz"
sample_id="A4842_DNA_02"
config_file="$repository/config/cluster.yaml"
output_root="$repository/output/full-sample"
mode="prepare"

while (($#)); do
  case "$1" in
    --vcf) source_vcf="${2:?missing value}"; shift 2 ;;
    --sample-id) sample_id="${2:?missing value}"; shift 2 ;;
    --config) config_file="${2:?missing value}"; shift 2 ;;
    --outdir) output_root="${2:?missing value}"; shift 2 ;;
    --dry-run) mode="dry-run"; shift ;;
    --run-local) mode="run-local"; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$sample_id" =~ ^[A-Za-z0-9][A-Za-z0-9_.-]*$ ]] || { echo "ERROR: unsafe sample ID: $sample_id" >&2; exit 2; }
for command_name in bcftools python snakemake; do
  command -v "$command_name" >/dev/null || { echo "ERROR: missing command: $command_name" >&2; exit 2; }
done
[[ -s "$source_vcf" ]] || { echo "ERROR: missing or empty source VCF: $source_vcf" >&2; exit 2; }
[[ -s "$config_file" ]] || { echo "ERROR: missing configuration: $config_file" >&2; exit 2; }
if [[ ! -s "$source_vcf.tbi" && ! -s "$source_vcf.csi" ]]; then
  echo "ERROR: source VCF has no readable .tbi or .csi index: $source_vcf" >&2
  exit 2
fi
vcf_samples="$(bcftools query --list-samples "$source_vcf")"
[[ "$vcf_samples" == "$sample_id" ]] || { echo "ERROR: expected VCF sample $sample_id, observed: $vcf_samples" >&2; exit 2; }

echo "Source VCF: $source_vcf"
echo "Sample: $sample_id"
echo "Run root: $output_root"
if [[ "$mode" == "prepare" ]]; then
  echo "Next: rerun with --dry-run, then submit using scripts/slurm/submit_full_sample.sh --submit."
  exit 0
fi

wrapper_args=(--vcf "$source_vcf" --sample-id "$sample_id" --outdir "$output_root" --config "$config_file" --profile "$repository/profiles/local")
[[ "$mode" == "run-local" ]] || wrapper_args+=(--dry-run)
cd "$repository"
python scripts/run_snaira_splice.py "${wrapper_args[@]}"
