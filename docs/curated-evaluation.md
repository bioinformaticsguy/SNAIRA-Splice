# Curated public-variant evaluation panel v1.0

This panel is a small reproducible regression evaluation for the full SNAIRA-Splice vertical slice: normalization, VEP, GTF-backed categories, SpliceAI, candidate tables, and the HTML report. It is not a clinical test, a benchmark with performance estimates, or a pathogenicity classifier.

## What is committed

`tests/curated/curated_splice_variants.grch38.vcf` contains five real public GRCh38 alleles in a synthetic heterozygous sample named `CURATED-SPLICE-1`. It contains no patient data. The sample genotype is synthetic and is only present to make it a valid one-sample VCF.

`tests/curated/curated_splice_variants.tsv` is the frozen v1.0 catalog. It identifies each allele, the expected gene/category behaviour, the expected VEP term, and a public source. The catalog deliberately does **not** use ClinVar clinical significance as an acceptance criterion. It tests annotation and prediction coverage, while preserving the distinction between a category, a computational prediction, and experimental/clinical evidence.

The VCF and normalized identifiers use forward-reference genomic alleles. HGVS descriptions remain transcript-oriented; for genes on the reverse strand, their displayed alleles are therefore reverse complements of the VCF REF/ALT alleles. Every panel revision must pass the helper's strict `bcftools norm --check-ref e` check against the configured GRCh38 FASTA before it can be submitted.

| Case | GRCh38 allele | Expected pipeline observation | External provenance |
|---|---|---|---|
| `canonical_donor_brca1` | `chr17:43115724:A>T` | `BRCA1`, VEP `splice_donor_variant`, `canonical` | ClinVar Variation ID 867519; functional evidence is recorded by ClinVar. |
| `near_splice_klhl7` | `chr7:23144030:G>C` | `KLHL7`, VEP `splice_region_variant`, `near_splice` | ClinVar Variation ID 452804; c.793+5 donor-side position. |
| `deep_intronic_cngb3` | `chr8:86605416:C>T` | `CNGB3`, VEP `intron_variant`, `deep_intronic`, distance ≥101 bp | ClinVar Variation ID 635822; RNA pseudoexon evidence includes PMID:31544997. |
| `exonic_motif_pkhd1` | `chr6:51903693:G>A` | `PKHD1`, VEP `synonymous_variant`, `exonic_splicing_motif` | ClinVar Variation ID 558073; reported aberrant splicing includes PMID:28170084. |
| `proximal_intronic_hbb` | `chr11:5226820:C>T` | `HBB`, VEP `intron_variant`, `outside_v1_categories`, distance 9–100 bp | ClinVar Variation ID 15454; intentional test of the frozen v1.0 gap. |

The public record URLs are stored row-by-row in the catalog. ClinVar records and interpretations can change; the catalog is versioned as an evaluation input, not as a clinical database mirror.

## Acceptance criteria

With the pinned GRCh38 reference, VEP 115.2/cache 115, Ensembl 115 GTF, and local SpliceAI 1.3.1:

1. Every catalog allele passes strict REF validation and reaches VEP, category, and SpliceAI stages.
2. Each expected gene/category/status/VEP term is observed in at least one relevant transcript assignment.
3. The deep-intronic control has an observed nearest junction distance of at least 101 bp.
4. The HBB control remains outside v1.0 categories at an observed distance between 9 and 100 bp; it must not be falsely renamed deep intronic.
5. A SpliceAI result is recorded as `scored` for the expected gene in every case. The evaluator records raw observed maxima but intentionally does not assert a pathogenicity threshold or clinical conclusion.

A failure is useful information. It can expose a reference/cache/GTF mismatch, changed VEP transcript modelling, missing SpliceAI annotation, a parser regression, or a genuine discrepancy with the expected transcript interpretation. Review the generated TSV before changing catalog expectations.

## Cluster workflow

Activate the controller environment and prepare/dry-run the complete panel:

```bash
conda activate snaira-splice
cd /data/humangen_kircherlab/Users/hassan/repos/SNAIRA-Splice

bash scripts/run_curated_evaluation.sh --dry-run
bash scripts/slurm/submit_curated_evaluation.sh --preflight
```

The helper writes only beneath `output/curated-evaluation/`; it never changes the committed source VCF. After preflight passes, submit it:

```bash
bash scripts/slurm/submit_curated_evaluation.sh --submit
```

After the SLURM workflow completes successfully, produce the strict expected-versus-observed evaluation:

```bash
bash scripts/run_curated_evaluation.sh --evaluate

column -t -s $'\t' output/curated-evaluation/evaluation/curated_evaluation.tsv | less -S
```

The evaluation exits nonzero if an acceptance criterion fails and writes both `curated_evaluation.tsv` and `curated_evaluation.json` for review. The candidate report is at:

```text
output/curated-evaluation/results/CURATED-SPLICE-1/05_report/CURATED-SPLICE-1.snaira_splice.html
```

## Scope limitations

The panel contains one allele per core category plus the intentional proximal-intronic gap. It does not yet estimate sensitivity, specificity, or calibration; it does not include a curated benign set, indels, multiallelic sites, or a multi-transcript conflict case. Those are required before claiming a benchmark and remain explicitly tracked in `TODO.md`.
