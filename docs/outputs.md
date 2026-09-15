# Output contract

All paths are beneath configured `output_root`.

- `metadata/resolved_samples.tsv`: resolved immutable inputs and manifest hashes.
- `metadata/manifest_validation.json`: cohort validation errors/warnings.
- `{sample}/logs/input_validation/`: BGZF, header, sample, and contig checks.
- `{sample}/01_normalized/`: split, left-aligned VCF, TBI, and bcftools stats.
- `{sample}/02_vep/`: retained annotated VCF/TBI, explicit transcript TSV, HTML statistics, and VEP version text.
- `{sample}/03_spliceai/{sample}.spliceai.vcf.gz`: raw local SpliceAI annotation and TBI.
- `{sample}/03_spliceai/{sample}.spliceai_evidence.tsv.gz`: one row per allele/gene prediction, including all DS/DP values, tied events, predicted positions, status, and missing reason.
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
- SpliceAI: `DS_AG`, `DS_AL`, `DS_DG`, `DS_DL`, `DP_AG`, `DP_AL`, `DP_DG`, `DP_DL`, `SpliceAI_max`, `SpliceAI_event`, `predicted_site_position`, `spliceai_status`, `spliceai_missing_reason`;
- provenance: annotation version, source VCF, and source manifest.

Semicolon-separated values in collapsed output represent unions, not a claim that every transcript has every listed effect. Missing scores are empty with a nonempty status/reason where determinable; a scored value of `0` is written as `0`.
