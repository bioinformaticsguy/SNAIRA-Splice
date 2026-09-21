#!/usr/bin/env bash
# Prepare, dry-run, or evaluate the versioned public curated-variant panel.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: run_curated_evaluation.sh [--prepare-only|--dry-run|--run-local|--evaluate] [options]

The checked-in panel contains real public GRCh38 alleles but a synthetic sample
and genotype. It is an annotation/prediction regression evaluation, not a
clinical sample and not a pathogenicity classifier.

Options:
  --config FILE       Workflow configuration (default: config/cluster.yaml)
  --outdir DIR        Evaluation root (default: output/curated-evaluation)
  --reference FASTA   Reference FASTA for strict REF validation
  --prepare-only      Create the derived BGZF VCF only (default)
  --dry-run           Also generate configuration and dry-run the full DAG
  --run-local         Also execute locally; do not use on a login node
  --evaluate          Evaluate a completed run against the catalog
  --force             Recreate the derived BGZF VCF
  -h, --help          Show this help
EOF
}

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
mode="prepare-only"
force=false
config_file="$repository/config/cluster.yaml"
reference_fasta="/data/humangen_kircherlab/Users/hassan/repos/VariantPiper/assets/reference/hg38.fa"
evaluation_root="$repository/output/curated-evaluation"
sample_id="CURATED-SPLICE-1"
while (($#)); do
  case "$1" in
    --config) config_file="${2:?missing value}"; shift 2 ;;
    --outdir) evaluation_root="${2:?missing value}"; shift 2 ;;
    --reference) reference_fasta="${2:?missing value}"; shift 2 ;;
    --prepare-only) mode="prepare-only"; shift ;;
    --dry-run) mode="dry-run"; shift ;;
    --run-local) mode="run-local"; shift ;;
    --evaluate) mode="evaluate"; shift ;;
    --force) force=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

source_vcf="$repository/tests/curated/curated_splice_variants.grch38.vcf"
catalog="$repository/tests/curated/curated_splice_variants.tsv"
input_vcf="$evaluation_root/input/$sample_id.vcf.gz"
results_root="$evaluation_root"
legacy_results_root="$evaluation_root/results"

if [[ "$mode" == "evaluate" ]]; then
  # Keep already completed runs readable after the output-layout simplification.
  if [[ ! -d "$results_root/$sample_id" && -d "$legacy_results_root/$sample_id" ]]; then
    results_root="$legacy_results_root"
  fi
  python "$repository/workflow/scripts/evaluate_curated_variants.py" \
    --catalog "$catalog" \
    --assignments "$results_root/$sample_id/03_categories/$sample_id.splice_category.assignments.tsv.gz" \
    --transcripts "$results_root/$sample_id/02_vep/$sample_id.vep.transcripts.tsv.gz" \
    --spliceai "$results_root/$sample_id/03_spliceai/$sample_id.spliceai_evidence.tsv.gz" \
    --tsv "$evaluation_root/evaluation/curated_evaluation.tsv" \
    --json "$evaluation_root/evaluation/curated_evaluation.json"
  echo "Evaluation table: $evaluation_root/evaluation/curated_evaluation.tsv"
  exit 0
fi

for command_name in bgzip tabix bcftools python snakemake; do
  command -v "$command_name" >/dev/null || { echo "ERROR: missing command: $command_name" >&2; exit 2; }
done
for required in "$source_vcf" "$catalog" "$reference_fasta" "$reference_fasta.fai" "$config_file"; do
  [[ -s "$required" ]] || { echo "ERROR: missing or empty required file: $required" >&2; exit 2; }
done

mkdir -p "$evaluation_root/input" "$results_root"
if [[ ! -s "$input_vcf" || ! -s "$input_vcf.tbi" ]] || $force; then
  temporary_vcf="$evaluation_root/input/.$sample_id.vcf.gz.tmp"
  rm -f "$temporary_vcf" "$temporary_vcf.tbi"
  trap 'rm -f "$temporary_vcf" "$temporary_vcf.tbi"' EXIT
  bgzip --stdout "$source_vcf" > "$temporary_vcf"
  tabix --preset vcf "$temporary_vcf"
  mv "$temporary_vcf" "$input_vcf"
  mv "$temporary_vcf.tbi" "$input_vcf.tbi"
  trap - EXIT
else
  echo "Curated input already exists; use --force to recreate it: $input_vcf"
fi

bcftools norm --fasta-ref "$reference_fasta" --check-ref e --do-not-normalize --output-type u "$input_vcf" >/dev/null
prepared_samples="$(bcftools query --list-samples "$input_vcf")"
[[ "$prepared_samples" == "$sample_id" ]] || { echo "ERROR: unexpected curated VCF sample: $prepared_samples" >&2; exit 2; }
printf 'Prepared curated VCF: %s\nCases: %s\n' "$input_vcf" "$(($(wc -l < "$catalog") - 1))"

if [[ "$mode" == "prepare-only" ]]; then
  echo "Next: rerun this command with --dry-run."
  exit 0
fi

wrapper_args=(--vcf "$input_vcf" --sample-id "$sample_id" --outdir "$results_root" --config "$config_file" --profile "$repository/profiles/local")
[[ "$mode" == "run-local" ]] || wrapper_args+=(--dry-run)
cd "$repository"
python scripts/run_snaira_splice.py "${wrapper_args[@]}"
