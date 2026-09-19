#!/usr/bin/env bash
# Prepare a small, immutable regional VCF input for a real-resource smoke test.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_region_test.sh [options]

Extract and validate a small region from a source VCF, then optionally invoke
the SNAIRA-Splice single-sample wrapper. The source VCF is never modified.

The current cluster defaults select the checked-in 200 kb regional smoke test.
Override any input below to run another sample or site.

Options:
  --config FILE           Workflow configuration (default: config/cluster.yaml)
  --work-dir DIR          Derived input location (default: output/region-test-input/ID)
  --outdir DIR            Pipeline result root (default: output/results)
  --prepare-only          Create and validate the regional VCF (default)
  --dry-run               Also dry-run the complete pipeline DAG
  --run-local             Also execute locally; do not use on a login node
  --force                 Recreate the derived regional VCF
  -h, --help              Show this help
EOF
}

mode="prepare-only"
force=false
source_vcf="/data/humangen_sfb1665_seqdata/short_read/processed_data/phase_i/A4842_DNA_02/snv_calls/A4842_DNA_02.pass.vcf.gz"
sample_id="A4842_DNA_02"
reference_fasta="/data/humangen_kircherlab/Users/hassan/repos/VariantPiper/assets/reference/hg38.fa"
region="chr17:43000000-43200000"
repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
site_config="$repository/config/cluster.yaml"
work_root=""
output_root="$repository/output/results"

while (($#)); do
  case "$1" in
    --vcf) source_vcf="${2:?missing value}"; shift 2 ;;
    --sample-id) sample_id="${2:?missing value}"; shift 2 ;;
    --reference) reference_fasta="${2:?missing value}"; shift 2 ;;
    --region) region="${2:?missing value}"; shift 2 ;;
    --config) site_config="${2:?missing value}"; shift 2 ;;
    --work-dir) work_root="${2:?missing value}"; shift 2 ;;
    --outdir) output_root="${2:?missing value}"; shift 2 ;;
    --prepare-only) mode="prepare-only"; shift ;;
    --dry-run) mode="dry-run"; shift ;;
    --run-local) mode="run-local"; shift ;;
    --force) force=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

[[ "$sample_id" =~ ^[A-Za-z0-9._-]+$ ]] || { echo "ERROR: unsafe sample ID: $sample_id" >&2; exit 2; }
work_root="${work_root:-$repository/output/region-test-input/$sample_id}"
test_vcf="$work_root/input/$sample_id.region.vcf.gz"
reference_dict="$work_root/reference/$(basename "${reference_fasta%.*}").dict"

for command_name in bcftools tabix samtools python snakemake; do
  command -v "$command_name" >/dev/null || { echo "ERROR: missing command: $command_name" >&2; exit 2; }
done
for required in "$source_vcf" "$reference_fasta" "$reference_fasta.fai" "$site_config"; do
  [[ -s "$required" ]] || { echo "ERROR: missing or empty required file: $required" >&2; exit 2; }
done

mkdir -p "$work_root/input" "$output_root" "$(dirname "$reference_dict")"
if [[ ! -s "$test_vcf" || (! -s "$test_vcf.tbi" && ! -s "$test_vcf.csi") ]] || $force; then
  temporary_vcf="$work_root/input/.$sample_id.region.vcf.gz.tmp"
  rm -f "$temporary_vcf" "$temporary_vcf.tbi" "$temporary_vcf.csi"
  trap 'rm -f "$temporary_vcf" "$temporary_vcf.tbi" "$temporary_vcf.csi"' EXIT
  bcftools view --samples "$sample_id" --regions "$region" --output-type z --output "$temporary_vcf" "$source_vcf"
  tabix --preset vcf "$temporary_vcf"
  mv "$temporary_vcf" "$test_vcf"
  mv "$temporary_vcf.tbi" "$test_vcf.tbi"
  trap - EXIT
else
  echo "Regional input already exists; use --force to recreate it: $test_vcf"
fi

bcftools norm --fasta-ref "$reference_fasta" --check-ref e --do-not-normalize --output-type u "$test_vcf" >/dev/null
vcf_samples="$(bcftools query --list-samples "$test_vcf")"
[[ "$vcf_samples" == "$sample_id" ]] || { echo "ERROR: unexpected VCF sample: $vcf_samples" >&2; exit 2; }

if [[ ! -s "$reference_dict" ]]; then
  samtools dict -o "$reference_dict.tmp" "$reference_fasta"
  mv "$reference_dict.tmp" "$reference_dict"
fi

variant_count="$(bcftools index --nrecords "$test_vcf")"
printf 'Prepared regional VCF: %s\nRegion: %s\nVariants: %s\nReference dictionary: %s\n' "$test_vcf" "$region" "$variant_count" "$reference_dict"

if [[ "$mode" == "prepare-only" ]]; then
  echo "Next: rerun this command with --dry-run."
  exit 0
fi

wrapper_args=(--vcf "$test_vcf" --sample-id "$sample_id" --outdir "$output_root" --config "$site_config" --profile "$repository/profiles/local")
[[ "$mode" == "run-local" ]] || wrapper_args+=(--dry-run)
cd "$repository"
python scripts/run_snaira_splice.py "${wrapper_args[@]}"
