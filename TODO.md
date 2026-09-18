# SNAIRA-Splice / SQ2 progress tracker

This file tracks the side quest:

> **Current iteration:** deliver a useful standalone VEP + SpliceAI report. VIPER/CALIGO integration is deferred and is not a completion criterion for this MVP.

It is intended to be updated through normal GitHub commits and pull requests. A checked item (`[x]`) means that the stated deliverable exists and has been verified. A parent milestone remains unchecked until all of its required items are complete.

## Progress overview

| Milestone | Status | Current result |
|---|---|---|
| SQ2.1 Conceptual workflow and categories | Complete | Category specification v1.0 is frozen in `docs/splice-category-specification-v1.0.md`. |
| SQ2.2 Tools and evidence sources | In progress | VEP and local SpliceAI are implemented; comparison predictors and other evidence classes are deferred. |
| SQ2.3 Multi-tool scoring and tissue context | In progress | A normalized predictor interface is drafted; scoring and tissue models are not implemented. |
| SQ2.4 Example-variant evaluation | In progress | Synthetic VEP/SpliceAI integration tests exist; a real resource-backed sample remains outstanding. |
| SQ2.5 Shareable HTML report | In progress | A standalone variant-centric report is implemented; real-sample review and accessibility/scale checks remain. |

## SQ2.1 — Finalize the conceptual workflow and splice-variant categories

- [x] **Complete SQ2.1**
  - [x] Separate *variant consequence annotation* from *splice-effect prediction*.
  - [x] Define canonical splice candidates as VEP `splice_donor_variant` or `splice_acceptor_variant` consequences.
  - [x] Exclude `splice_region_variant` from the canonical candidate set.
  - [x] Retain non-canonical `splice_region_variant` annotations for later use.
  - [x] Define the initial workflow boundary: manifest → small-variant VCF → normalization → VEP → transcript table → allele table → summaries.
  - [x] Write precise, assembly-aware boundaries for the **near-splice** category.
  - [x] Define the **exonic splicing-motif** category, including overlap with coding consequences.
  - [x] Define the **deep-intronic** category and its distance/exclusion rules.
  - [x] Decide how variants belonging to multiple categories are represented without forced mutual exclusivity.
  - [x] Define transcript scope for every category: all transcripts, MANE, canonical, protein coding, or configurable subsets.
  - [x] Document how category definitions map onto VIPER inputs and outputs.
  - [x] Review and freeze a versioned category specification for the prototype.

**Done when:** `docs/` contains a versioned category specification with unambiguous inclusion, exclusion, overlap, transcript, and assembly rules for all four categories, plus the VIPER hand-off contract.

## SQ2.2 — Select tools and evidence sources

- [ ] **Complete SQ2.2**
  - [x] Select bcftools for decomposition, left alignment, and REF validation.
  - [x] Select Ensembl VEP for transcript-level canonical splice consequence annotation.
  - [x] Select VEP/MANE/canonical/TSL/APPRIS fields for deterministic transcript representation.
  - [x] Pin the current implementation to VEP 115.2/cache release 115 and GRCh38.
  - [x] Provide a normalized interface for adding predictors without fabricating missing results.
  - [x] Select and implement local SpliceAI 1.3.1 as the first splice-effect predictor.
  - [x] Record SpliceAI DS/DP fields, tied events, coordinate predictions, and explicit missingness.
  - [ ] Define explicit tool-selection criteria: license, local/offline execution, reproducibility, supported assemblies, transcript model, runtime, and redistribution constraints.
  - [ ] Evaluate and select one or more **near-splice** predictors.
  - [ ] Evaluate and select one or more **exonic splicing-motif** tools or evidence sources.
  - [ ] Evaluate and select one or more **deep-intronic** predictors.
  - [ ] Select population-frequency evidence and define the source/version policy.
  - [ ] Select clinical and functional evidence sources, including update/version policies.
  - [ ] Decide whether RNA/splicing assay evidence is supported in the prototype and define its input contract.
  - [ ] Create a tool/evidence decision matrix documenting strengths, limitations, licensing, and selected use.
  - [ ] Record benchmark datasets or published truth sets for each selected predictor.

**Done when:** every category has a documented, justified tool/evidence selection, pinned version or model, resource-installation path, license assessment, and test strategy.

## SQ2.3 — Design the multi-tool scoring and tissue-context framework

- [ ] **Complete SQ2.3**
  - [x] Define a draft normalized predictor-output schema in `docs/adding_predictors.md`.
  - [x] Include predictor identity/version, raw and normalized scores, labels, applicability, tissue, evidence source, and missing-value reason.
  - [x] Keep consequence annotations separate from predictor scores.
  - [x] Preserve transcript-level evidence alongside deterministic allele-level representatives.
  - [ ] Decide the score direction and normalization contract for each selected predictor.
  - [ ] Define how multiple transcript-level scores collapse—or remain separate—at variant level.
  - [ ] Define predictor applicability rules for canonical, near-splice, exonic-motif, and deep-intronic variants.
  - [ ] Define missingness semantics: not applicable, unavailable resource, failed prediction, filtered transcript, and genuinely missing.
  - [ ] Select tissue-context evidence sources and pin their versions.
  - [ ] Define tissue selection when phenotype or disease-relevant tissue is known, unknown, or unavailable.
  - [ ] Specify how tissue expression, transcript usage, and splice-junction evidence influence ranking.
  - [ ] Decide whether the prototype uses a rule-based tier, weighted score, rank aggregation, or an evidence-vector presentation.
  - [ ] Define safeguards against double-counting correlated predictors or evidence sources.
  - [ ] Define confidence, provenance, explainability, and score-calibration outputs.
  - [ ] Specify the versioned scoring payload exchanged with VIPER.
  - [ ] Implement and unit-test the selected aggregation framework.

**Done when:** a versioned scoring specification, tissue-context model, missingness contract, and tested implementation can combine real outputs from at least two tools without hiding the underlying evidence.

## SQ2.4 — Test on example variants and document results

- [ ] **Complete SQ2.4**
  - [x] Add a tiny normalized synthetic VCF fixture.
  - [x] Test combined consequence terms and canonical/non-canonical separation.
  - [x] Test transcript ranking and allele-level collapse.
  - [x] Run a cache-free end-to-end Snakemake test using clearly identified mock VEP annotations.
  - [x] Exercise canonical-low-score, splice-region, noncanonical-intronic-high-score, zero, and missing SpliceAI software behavior in synthetic tests.
  - [ ] Assemble a versioned example-variant set containing positive and negative examples for every category.
  - [ ] Include donor, acceptor, near-splice, exonic-motif, deep-intronic, multiallelic, indel, and multi-transcript cases.
  - [ ] Add examples where predictors disagree or are not applicable.
  - [ ] Define expected results and acceptance criteria before running the evaluation.
  - [ ] Run a real VEP integration test using the pinned GRCh38 cache.
  - [ ] Run each selected splice-effect predictor on its applicable examples.
  - [ ] Compare outputs with published, clinical, or experimental evidence where available.
  - [ ] Document false positives, false negatives, disagreements, missing results, and transcript-dependent interpretations.
  - [ ] Test the complete hand-off to and from VIPER.
  - [ ] Record exact commands, configuration, resource versions, checksums, runtime, and environment hashes.
  - [ ] Write a concise results document with tables and interpretation caveats.

**Done when:** a reproducible example dataset exercises every category and the VIPER integration, with expected-versus-observed results and limitations checked into the repository.

## SQ2.5 — Generate a shareable HTML report

- [ ] **Complete SQ2.5**
  - [x] Generate static per-sample HTML count summaries.
  - [x] Generate a static cohort HTML count summary.
  - [x] Retain TSV and JSON companions for traceability.
  - [x] Define the report audience and minimum interpretation disclaimer.
  - [x] Design a standalone variant-centric report combining VEP consequence and SpliceAI evidence.
  - [x] Add filtering/navigation by gene, category, consequence, score threshold, and MANE status.
  - [x] Show native DS/DP scores, explicit missingness, and provenance rather than a pathogenicity rank.
  - [x] Link allele summaries to expandable full transcript evidence.
  - [x] Add resource/software versions and reproducibility metadata to the visible report.
  - [x] Ensure the report is self-contained with embedded CSS and JavaScript.
  - [ ] Check accessibility, readable print/PDF output, and behavior with zero, small, and large result sets.
  - [ ] Add snapshot or structural tests for report generation.
  - [ ] Generate and review a representative shareable report from the SQ2.4 example set.

**Done when:** the example run produces a reviewed, portable HTML report that communicates evidence and limitations clearly and can be shared without access to the execution environment.

## Deferred cross-cutting VIPER integration

- [ ] Define the supported VIPER version and pin it in integration tests.
- [ ] Agree on stable input/output schemas and ownership boundaries between SNAIRA-Splice and VIPER.
- [ ] Implement schema validation at both sides of the hand-off.
- [ ] Add a minimal end-to-end command that runs the splice workflow and imports its results into VIPER.
- [ ] Decide how sample, family, phenotype, role, and transcript identifiers are reconciled.
- [ ] Preserve provenance across the integration boundary.
- [ ] Add failure-mode tests for missing, partial, duplicated, and incompatible VIPER inputs.
- [ ] Document installation and execution of the combined prototype.
- [ ] Run the combined prototype from a clean environment.
- [ ] Tag the working SQ2 prototype release.

## Maintenance and progress-tracking conventions

- Update checkboxes in the same pull request that adds the corresponding implementation or document.
- Add a short link after a completed item when the evidence is not obvious, for example `([PR #12](...))`.
- Do not check a parent milestone until all items required by its **Done when** statement are complete.
- Add newly discovered work beneath the relevant milestone rather than hiding it in issue comments.
- Use GitHub issues for detailed discussion; keep this file as the stable, repository-level progress summary.
- When scope changes, update the milestone definition and explain the change in `CHANGELOG.md`.

## Suggested next three tasks

- [x] Draft the versioned category specification for near-splice, exonic-motif, and deep-intronic variants.
- [ ] Build the SQ2.2 tool/evidence decision matrix.
- [ ] Validate the standalone SpliceAI report on one real sample before selecting a second predictor.
