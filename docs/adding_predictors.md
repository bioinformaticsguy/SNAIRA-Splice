# Adding splice predictors

SpliceAI is the reference implementation: `workflow/rules/spliceai.smk` owns execution, `parse_spliceai_vcf.py` owns its format, and `spliceai.yaml` owns dependencies. A future predictor should add the same three boundaries (preferably under predictor subdirectories once a second implementation exists). Do not parse one predictor inside another tool's script or modify canonical consequence classification to accommodate a score.

Every adapter should emit a compressed TSV with these columns:

| Field | Meaning |
|---|---|
| `variant_key` | normalized `CHROM:POS:REF:ALT` |
| `sample_id` | manifest sample |
| `gene` / `transcript` | tool-specific mapped context, nullable |
| `variant_class` | canonical, near_splice, exonic_splicing_motif, or deep_intronic |
| `predictor_name` / `predictor_version` | provenance |
| `raw_score` / `normalized_score` | original and harmonized values |
| `prediction_label` | tool-defined categorical call |
| `applicable_variant_class` | declared supported class(es) |
| `tissue` | tissue context or empty |
| `evidence_source` | model/database/source description |
| `missing_value_reason` | explicit reason when an applicable value is absent |

Applicability belongs in configuration and metadata, not inference from missing scores. A module declares one or more of `canonical`, `near_splice`, `exonic_splicing_motif`, and `deep_intronic`; rows outside applicability should not be scored. Integration should preserve multiple predictors and contexts rather than overwriting them. The `03_categories` atomic assignment table is the natural interface for selecting category-applicable rows while retaining all transcript assignments.

An adapter must distinguish at least `scored`, `not_scored`, `unsupported_variant`, and a failed predictor job. It must preserve native fields before harmonization, define tie behavior, and document coordinate semantics. Adding Pangolin or SQUIRLS later should extend the evidence vector and report rather than replace `SpliceAI_max` or manufacture cross-tool equivalence.
