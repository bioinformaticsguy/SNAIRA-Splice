# Adding splice predictors

Add a rule under `workflow/rules/predictors/`, an adapter under `workflow/scripts/predictors/`, and a pinned focused environment under `workflow/envs/predictors/`. Do not modify canonical consequence classification to accommodate a score.

Every adapter should emit a compressed TSV with these columns:

| Field | Meaning |
|---|---|
| `variant_key` | normalized `CHROM:POS:REF:ALT` |
| `sample_id` | manifest sample |
| `gene` / `transcript` | tool-specific mapped context, nullable |
| `variant_class` | canonical, near_splice, exonic_motif, or deep_intronic |
| `predictor_name` / `predictor_version` | provenance |
| `raw_score` / `normalized_score` | original and harmonized values |
| `prediction_label` | tool-defined categorical call |
| `applicable_variant_class` | declared supported class(es) |
| `tissue` | tissue context or empty |
| `evidence_source` | model/database/source description |
| `missing_value_reason` | explicit reason when an applicable value is absent |

Applicability belongs in configuration and metadata, not inference from missing scores. A module declares one or more of `canonical`, `near_splice`, `exonic_motif`, and `deep_intronic`; rows outside applicability should not be scored. Integration should preserve multiple predictors and contexts rather than overwriting them. The existing noncanonical splice-region table is the natural input boundary for a near-splice module.
