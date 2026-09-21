# Output contract

All paths are beneath configured `output_root`.

For the checked-in helpers, new outputs use direct, purpose-specific roots:
`output/curated-evaluation/`, `output/region-test/`, and
`output/full-sample/`. Each run root directly contains its sample directories,
`cohort/`, and `metadata/`; it does not add an otherwise redundant `results/`
directory. Historical outputs are never moved by the workflow.

- `metadata/resolved_samples.tsv`: resolved immutable inputs and manifest hashes.
- `metadata/manifest_validation.json`: cohort validation errors/warnings.
- `{sample}/logs/input_validation/`: BGZF, header, sample, and contig checks.
- `{sample}/01_normalized/`: split, left-aligned VCF, TBI, bcftools stats, and `*.call_evidence.tsv.gz`.
- `{sample}/02_vep/`: retained annotated VCF/TBI, explicit transcript TSV, HTML statistics, and VEP version text.
- `{sample}/03_spliceai/{sample}.spliceai.vcf.gz`: raw local SpliceAI annotation and TBI.
- `{sample}/03_spliceai/{sample}.spliceai_evidence.tsv.gz`: one row per allele/gene prediction, including all DS/DP values, tied events, predicted positions, status, and missing reason.
- `{sample}/03_categories/{sample}.vep.transcripts.categorized.tsv.gz`: the complete parsed VEP transcript table augmented with transcript-aware category fields from the release-matched Ensembl GTF.
- `{sample}/03_categories/{sample}.splice_category.assignments.tsv.gz`: normalized allele × transcript × category assignments. Empty `category` rows explicitly retain assignments outside the frozen v1.0 categories rather than silently dropping them.
- `{sample}/04_splice_candidates/{sample}.splice_candidates.transcripts.tsv.gz`: joined candidate evidence at normalized allele × transcript granularity (with transcript-less rows when only unmatched SpliceAI gene evidence exists).
- `{sample}/04_splice_candidates/{sample}.splice_candidates.variants.tsv.gz`: deterministic one-row-per-allele main candidate table.
- `{sample}/04_splice_candidates/{sample}.splice_review.variants.tsv.gz`: broader allele table meeting the review score threshold.
- `{sample}/05_report/{sample}.snaira_splice.html`: self-contained searchable/sortable candidate report with expandable transcript evidence and provenance.
- `{sample}/03_canonical_splice/*.transcripts.tsv.gz`: all donor/acceptor transcript rows.
- `{sample}/03_canonical_splice/*.variants.tsv.gz`: one row per qualifying normalized allele.
- `{sample}/03_canonical_splice/*.noncanonical_splice_region.tsv.gz`: region-only rows, excluded from canonical candidates.
- `{sample}/04_summary/`: static TSV, JSON, and HTML counts.
- `cohort/`: concatenated allele rows and cohort summaries.
- `metadata/run_metadata.json`: pipeline/git/software/cache/reference/config provenance.

The variant key is `CHROM:POS:REF:ALT` after normalization. Transcript tables are never deleted after collapse. Logs exist per operational rule and expensive rules have benchmark TSVs.

## Joined evidence schema

Stable transcript-table columns are grouped as follows:

- identity: `sample_id`, `CHROM`, `POS`, `REF`, `ALT`, `normalized_variant_id`;
- transcript: `SYMBOL`, `Gene`, `Feature`, `BIOTYPE`, `STRAND`, `EXON`, `INTRON`, `HGVSc`, `HGVSp`;
- quality: `MANE_SELECT`, `MANE_PLUS_CLINICAL`, `CANONICAL`, `TSL`, `APPRIS`;
- VEP: `Consequence`, `IMPACT`, `splice_category`;
- category assignment: `category_set`, `category_assignment_status`, `category_assignment_reason`, `nearest_junction_distance`, `nearest_junction_type`;
- call evidence from the normalized VCF: `vcf_qual`, `vcf_filter`, `genotype`, `read_depth`, `genotype_quality`, `allele_depth`;
- SpliceAI: `DS_AG`, `DS_AL`, `DS_DG`, `DS_DL`, `DP_AG`, `DP_AL`, `DP_DG`, `DP_DL`, `SpliceAI_max`, `SpliceAI_event`, `predicted_site_position`, `spliceai_status`, `spliceai_missing_reason`;
- provenance: annotation version, source VCF, and source manifest.

Semicolon-separated values in collapsed output represent unions, not a claim that every transcript has every listed effect. Missing scores are empty with a nonempty status/reason where determinable; a scored value of `0` is written as `0`.

`category_set` implements `TSG-SPLICE-CATEGORIES/1.1.0` without forced mutual exclusivity. It may contain `canonical`, `near_splice`, `exonic_splicing_motif`, and/or `deep_intronic` as applicable to that exact allele × transcript. `near_splice` includes VEP 115's donor-specific fifth-base consequence as well as `splice_region_variant`. `nearest_junction_distance` is the minimum whole-base distance to the flanking intron boundary for wholly intronic alleles; `nearest_junction_type` is transcript-strand-aware (`donor`, `acceptor`, or both). `category_assignment_reason` records VEP/GTF evidence and the intentional v1.0 proximal-intronic 9–100 bp gap. The collapsed candidate table retains `category_set_union` plus `primary_category`, a display-only precedence value; neither removes transcript-level assignments.

`genotype`, `read_depth`, `genotype_quality`, and `allele_depth` preserve the source normalized VCF's `GT`, `DP`, `GQ`, and `AD` values respectively. Empty values mean the relevant VCF field was absent or missing; they are not converted to zero. `vcf_qual` and `vcf_filter` retain the raw normalized VCF `QUAL` and `FILTER` values.
