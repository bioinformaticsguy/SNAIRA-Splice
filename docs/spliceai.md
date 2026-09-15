# SpliceAI in the standalone MVP

SNAIRA-Splice runs SpliceAI locally against the normalized VCF. It does not silently substitute a precomputed lookup database. The pinned workflow environment uses SpliceAI 1.3.1 and records the executable version, annotation checksum, masking mode, and maximum distance.

## Required resource

Set `spliceai.annotation` to a SpliceAI gene annotation matching GRCh38. The resource setup command `--install-spliceai` creates a project-local environment and copies the package's bundled GRCh38 annotation to `resources/spliceai/grch38.txt`. Large resources are never downloaded by ordinary Snakemake jobs.

The configured defaults are:

```yaml
spliceai:
  enabled: true
  annotation: resources/spliceai/grch38.txt
  max_distance: 5000
  masked: false
  candidate_threshold: 0.20
  review_threshold: 0.05
```

`max_distance` controls SpliceAI's reporting window. It is not evidence that every predicted site within 5 kb is functional. Unmasked mode retains raw predictions for research/discovery review; masking can be enabled explicitly. Changing either setting changes interpretation and is recorded in provenance.

## Parsed evidence

For every returned allele/gene prediction the parser preserves `DS_AG`, `DS_AL`, `DS_DG`, `DS_DL`, `DP_AG`, `DP_AL`, `DP_DG`, and `DP_DL`. `SpliceAI_max` is the maximum delta score. All event names tied at that maximum are retained in a stable order. Each corresponding delta position and genomic coordinate (`variant POS + DP`) is retained; no strand-based sign inversion is applied because DP is already defined relative to the variant coordinate.

Alleles without an INFO prediction are `not_scored`; allele shapes outside SpliceAI's supported simple SNV/indel interface are `unsupported_variant`. A genuine all-zero prediction is `scored` with value `0`. A process-level failure stops the Snakemake job and therefore cannot be confused with successful per-allele missingness.

## Licensing and maintenance

The official SpliceAI code/model distribution has non-commercial restrictions and its upstream GitHub repository was archived in 2026. Users must review the upstream license for their use case. Pinning and an isolated adapter reduce replacement cost, but do not remove scientific or licensing obligations.

Computational splice predictions are research evidence and do not prove that an RNA splicing event occurs.
