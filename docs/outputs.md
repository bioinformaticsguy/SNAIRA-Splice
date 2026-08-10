# Output contract

All paths are beneath configured `output_root`.

- `metadata/resolved_samples.tsv`: resolved immutable inputs and manifest hashes.
- `metadata/manifest_validation.json`: cohort validation errors/warnings.
- `{sample}/logs/input_validation/`: BGZF, header, sample, and contig checks.
- `{sample}/01_normalized/`: split, left-aligned VCF, TBI, and bcftools stats.
- `{sample}/02_vep/`: retained annotated VCF/TBI, explicit transcript TSV, HTML statistics, and VEP version text.
- `{sample}/03_canonical_splice/*.transcripts.tsv.gz`: all donor/acceptor transcript rows.
- `{sample}/03_canonical_splice/*.variants.tsv.gz`: one row per qualifying normalized allele.
- `{sample}/03_canonical_splice/*.noncanonical_splice_region.tsv.gz`: region-only rows, excluded from canonical candidates.
- `{sample}/04_summary/`: static TSV, JSON, and HTML counts.
- `cohort/`: concatenated allele rows and cohort summaries.
- `metadata/run_metadata.json`: pipeline/git/software/cache/reference/config provenance.

The variant key is `CHROM:POS:REF:ALT` after normalization. Transcript tables are never deleted after collapse. Logs exist per operational rule and expensive rules have benchmark TSVs.
