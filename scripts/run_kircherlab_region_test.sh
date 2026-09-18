#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_kircherlab_region_test.sh [--prepare-only | --dry-run | --run-local] [--force]

Prepare the A4842_DNA_02 BRCA1-region fixture on the Kircherlab cluster and
optionally run the SNAIRA-Splice single-sample wrapper. The source VCF is never
modified. Defaults are intentionally site-specific and recorded below.

  --prepare-only  Create and validate the regional input (default)
  --dry-run       Prepare the input and dry-run the complete Snakemake DAG
  --run-local     Prepare the input and execute locally (not recommended on a login node)
  --force         Recreate the derived regional input
  -h, --help      Show this help
EOF
}

mode="prepare-only"
force=false
while (($#)); do
  case "$1" in
    --prepare-only) mode="prepare-only"; shift ;;
    --dry-run) mode="dry-run"; shift ;;
    --run-local) mode="run-local"; shift ;;
    --force) force=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
sample_id="A4842_DNA_02"
sample_dir="/data/humangen_sfb1665_seqdata/short_read/processed_data/phase_i/$sample_id"
source_vcf="$sample_dir/snv_calls/$sample_id.pass.vcf.gz"
reference_fasta="/data/humangen_kircherlab/Users/hassan/repos/VariantPiper/assets/reference/hg38.fa"
resource_root="/data/humangen_kircherlab/Users/hassan/resources/SNAIRA-Splice"
reference_dict="$resource_root/reference/hg38.dict"
work_root="/data/humangen_kircherlab/Users/hassan/snaira-splice-runs/${sample_id}_BRCA1"
test_vcf="$work_root/input/$sample_id.BRCA1.vcf.gz"
region="chr17:43000000-43200000"
site_config="$repository/config/kircherlab.cluster.yaml"

for command_name in bcftools tabix samtools python snakemake; do
  command -v "$command_name" >/dev/null || { echo "ERROR: missing command: $command_name" >&2; exit 2; }
done
for required in "$source_vcf" "$source_vcf.tbi" "$reference_fasta" "$reference_fasta.fai" "$site_config" "$resource_root/spliceai/grch38.txt"; do
  [[ -s "$required" ]] || { echo "ERROR: missing or empty required file: $required" >&2; exit 2; }
done

mkdir -p "$work_root/input" "$work_root/tmp" "$(dirname "$reference_dict")"
if [[ ! -s "$test_vcf" || ! -s "$test_vcf.tbi" ]] || $force; then
  temporary_vcf="$work_root/input/.$sample_id.BRCA1.vcf.gz.tmp"
  rm -f "$temporary_vcf" "$temporary_vcf.tbi"
  trap 'rm -f "$temporary_vcf" "$temporary_vcf.tbi"' EXIT
  bcftools view --samples "$sample_id" --regions "$region" --output-type z \
    --output "$temporary_vcf" "$source_vcf"
  tabix --preset vcf "$temporary_vcf"
  mv "$temporary_vcf" "$test_vcf"
  mv "$temporary_vcf.tbi" "$test_vcf.tbi"
  trap - EXIT
else
  echo "Regional input already exists; use --force to recreate it: $test_vcf"
fi

bcftools norm --fasta-ref "$reference_fasta" --check-ref e --do-not-normalize \
  --output-type u "$test_vcf" >/dev/null
vcf_samples="$(bcftools query --list-samples "$test_vcf")"
[[ "$vcf_samples" == "$sample_id" ]] || { echo "ERROR: unexpected VCF sample: $vcf_samples" >&2; exit 2; }

if [[ ! -s "$reference_dict" ]]; then
  temporary_dict="$reference_dict.tmp"
  samtools dict -o "$temporary_dict" "$reference_fasta"
  mv "$temporary_dict" "$reference_dict"
fi

variant_count="$(bcftools index --nrecords "$test_vcf")"
echo "Prepared $test_vcf"
echo "Region: $region"
echo "Variants: $variant_count"
echo "Reference dictionary: $reference_dict"

if [[ "$mode" == "prepare-only" ]]; then
  echo "Next: bash scripts/run_kircherlab_region_test.sh --dry-run"
  exit 0
fi

wrapper_args=(
  --vcf "$test_vcf"
  --sample-id "$sample_id"
  --outdir "$work_root/results"
  --config "$site_config"
  --profile "$repository/profiles/local"
)
[[ "$mode" == "run-local" ]] || wrapper_args+=(--dry-run)
cd "$repository"
python scripts/run_snaira_splice.py "${wrapper_args[@]}"
