# The Splicing Gap splice-category specification v1.0

| Field | Value |
|---|---|
| Specification ID | `TSG-SPLICE-CATEGORIES` |
| Version | `1.0.0` |
| Status | Frozen for the SQ2 prototype |
| Frozen on | 2026-08-10 |
| Default assembly | GRCh38 |
| Default annotation | Ensembl VEP 115.2/cache release 115, Ensembl transcripts |

## 1. Purpose and normative language

This document defines the four splice-variant categories used by the SQ2 prototype of The Splicing Gap and the data contract between SNAIRA-Splice and VIPER. It defines *where a normalized allele lies relative to a transcript*. It does not, by itself, assert that the allele alters splicing or is clinically relevant.

The words **MUST**, **MUST NOT**, **SHOULD**, and **MAY** are normative. A change to a MUST/MUST NOT rule requires a new specification version.

The categories are:

1. `canonical`
2. `near_splice`
3. `exonic_splicing_motif`
4. `deep_intronic`

Category assignment is allele- and transcript-specific. Variant-level summaries are derived from, and MUST NOT replace, the complete transcript assignments.

## 2. Scientific boundary: annotation versus prediction

Two claims MUST remain separate:

- **Consequence/category annotation:** the allele occupies a defined region relative to an annotated transcript.
- **Splice-effect prediction:** a named method estimates whether or how strongly the allele changes splicing.

Membership in `canonical`, `near_splice`, `exonic_splicing_motif`, or `deep_intronic` is an applicability or consequence statement. It is not a pathogenicity assertion and MUST NOT be presented as a positive predictor result. A category may have no predictor result because a module was not run, the tool is not applicable, a resource is missing, or prediction failed; those states MUST remain distinguishable.

## 3. Common representation and coordinate rules

### 3.1 Normalized allele

Classification MUST operate on one normalized REF/ALT allele at a time after multiallelic decomposition and reference-aware left alignment. The stable prototype key is:

```text
assembly:CHROM:POS:REF:ALT
```

The current implementation uses `CHROM:POS:REF:ALT` internally; the hand-off MUST carry `assembly` separately so keys cannot be compared across assemblies accidentally.

`CHROM`, `POS`, and `REF` MUST match the declared reference FASTA. Source VCF coordinates or keys MUST NOT be silently lifted over, renamed, or compared with keys from another assembly.

### 3.2 Transcript-relative classification

Every assignment MUST contain a stable transcript identifier and, when supplied by the annotation release, its version. Boundaries are defined in transcript orientation:

```text
upstream exon | donor | intron | acceptor | downstream exon
               +1 +2           -2 -1
```

Consequently, genomic left/right is not used to infer donor or acceptor type. On a reverse-strand transcript, the same transcript-relative rules apply after strand orientation.

For substitutions, the affected reference interval is the substituted base. For deletions and delins, it is the normalized deleted/replaced reference interval after removal of the shared VCF anchor. For insertions, it is the interbase junction after removal of the shared anchor. A boundary-spanning allele overlaps every transcript region touched by that affected interval or junction. VEP consequence terms are authoritative for `canonical` and `near_splice` in v1.0 because VEP already applies these allele-aware rules.

### 3.3 Assembly awareness

An annotation run MUST declare:

- assembly name;
- reference FASTA URI/path and checksum;
- contig naming convention;
- VEP/cache release;
- transcript source (`ensembl`, `refseq`, or `merged`);
- annotation resource checksums where practical.

The SQ2 v1.0 implementation supports GRCh38 only. GRCh37 input MUST fail until a separately pinned GRCh37 reference, cache, configuration, and integration test are supplied. The category definitions are transcript-relative and can later be applied to GRCh37, but assignments from GRCh37 and GRCh38 MUST remain separate. Liftover is outside this specification and MUST NOT occur implicitly.

## 4. Category definitions

### 4.1 Canonical (`canonical`)

An allele–transcript assignment is `canonical` if and only if its VEP consequence set for that transcript contains at least one of:

- `splice_donor_variant` (`SO:0001575`); or
- `splice_acceptor_variant` (`SO:0001574`).

Ampersand-delimited terms MUST be parsed individually. The subtype is:

- `donor` when only `splice_donor_variant` is present;
- `acceptor` when only `splice_acceptor_variant` is present;
- `donor_and_acceptor` when both are present for the same assignment, or when producing a variant-level union across assignments containing both types.

Operationally these consequences normally cover the invariant intronic donor `+1/+2` and acceptor `-2/-1` positions, but the pipeline MUST use VEP's explicit term instead of recreating donor/acceptor calls from strand or distance. `splice_region_variant` alone is never canonical.

**Include:** every transcript row with either canonical term, regardless of transcript biotype or principal status.

**Exclude:** rows containing only `splice_region_variant`, intronic rows without a canonical term, and predictor-only claims lacking the VEP consequence.

### 4.2 Near splice (`near_splice`)

An allele–transcript assignment is `near_splice` if and only if:

1. its consequence set contains `splice_region_variant` (`SO:0001630`); and
2. the same transcript assignment contains neither `splice_donor_variant` nor `splice_acceptor_variant`.

The Sequence Ontology boundary for `splice_region_variant` is within 1–3 bases of the exon or 3–8 bases of the intron. In transcript-relative terms, v1.0 therefore covers:

- the last 1–3 exonic bases adjacent to a donor;
- donor-side intronic positions `+3` through `+8`;
- acceptor-side intronic positions `-8` through `-3`; and
- the first 1–3 exonic bases adjacent to an acceptor.

These windows are inclusive. For an exon shorter than six bases, an exonic allele may lie within both its acceptor-side and donor-side windows; it remains one `near_splice` category assignment and MAY carry both boundary labels.

This definition follows the published Sequence Ontology definition of [`splice_region_variant`](https://www.sequenceontology.org/miso/current_svn/term/SO%3A0001630). Extended donor, polypyrimidine-tract, and branchpoint regions are not silently added: Ensembl documents wider regions as distinct optional plugin consequences, including donor positions 3–6 and acceptor-side polypyrimidine positions 3–17 ([VEP plugin documentation](https://plants.ensembl.org/info/docs/tools/vep/script/vep_plugins.html)). A later specification may add explicit subcategories after tool selection.

**Include:** VEP `splice_region_variant` rows satisfying the canonical exclusion above, including coding or UTR exonic rows with a combined consequence such as `missense_variant&splice_region_variant`.

**Exclude:** canonical rows on the same transcript; intronic positions beyond 8 bases without a `splice_region_variant` term; variants annotated only by an unconfigured extended-region plugin.

### 4.3 Exonic splicing motif (`exonic_splicing_motif`)

This is an *applicability category* for future exonic splicing-regulatory prediction. An allele–transcript assignment is `exonic_splicing_motif` when the affected interval or insertion junction overlaps sequence retained in the mature exon of that transcript, including coding sequence and untranslated exonic sequence.

For v1.0, exon overlap MUST come from the same versioned transcript annotation used by VEP. Implementations SHOULD use explicit exon coordinates from that annotation. Until the dedicated module is implemented, a VEP transcript row with a populated `EXON` field is an acceptable operational indicator of exon overlap. A reported `Feature_type` other than `Transcript` MUST NOT create this assignment.

Category membership says only that an exonic motif predictor may be applicable. It MUST NOT create a score, motif-disruption label, or evidence record unless a named predictor was actually run.

Coding consequences are orthogonal annotations, not exclusions. For example:

- `missense_variant&splice_region_variant` may be `exonic_splicing_motif` + `near_splice` + coding consequence `missense_variant`;
- a synonymous variant may be `exonic_splicing_motif` + coding consequence `synonymous_variant`;
- an exonic indel may be `exonic_splicing_motif` + its frameshift/in-frame consequence;
- UTR and non-coding-transcript exons may be included when their transcript is in scope.

**Include:** normalized SNVs and small indels overlapping an annotated mature exon for the transcript.

**Exclude:** purely intronic assignments, intergenic/upstream/downstream assignments, and alleles overlapping only a regulatory feature rather than a transcript exon.

### 4.4 Deep intronic (`deep_intronic`)

An allele–transcript assignment is `deep_intronic` if and only if all of the following hold:

1. the entire affected reference interval, or the insertion junction, is inside an annotated intron of that transcript;
2. its minimum distance to either bounding exon–intron junction is **greater than 100 bases** (at least 101 bases);
3. its consequence set contains neither canonical splice term nor `splice_region_variant`; and
4. it does not overlap an exon of that transcript.

The threshold is inclusive on the excluded side: distance 100 is not deep; distance 101 is deep. The distance is computed independently for each transcript and intron using that transcript's strand-aware exon structure. An allele spanning or touching a boundary is not deep.

The >100-base operational definition is supported by reviews describing deep-intronic variants more than 100 bases from exon–intron junctions ([Vaz-Drago et al., 2017](https://pubmed.ncbi.nlm.nih.gov/28497172/)). It is a prototype categorization threshold, not a statement that positions closer than 101 bases cannot alter splicing.

**Include:** small variants wholly within an intron and at least 101 bases from both bounding junctions for the transcript.

**Exclude:** canonical, near-splice, exonic, boundary-spanning, non-transcript, and short-intron assignments that cannot satisfy the distance rule.

### 4.5 Explicitly unassigned intronic interval

Intronic positions 9–100 bases from their nearest junction are neither `near_splice` nor `deep_intronic` in v1.0. They MUST be retained with:

```text
category_assignment_status = outside_v1_categories
category_assignment_reason = proximal_intronic_9_100
```

This deliberate gap prevents a scientifically broad `deep_intronic` label and makes future expansion explicit. Such variants remain available to predictors whose applicability extends into this interval.

## 5. Non-exclusive category model

### 5.1 Unit of assignment

The atomic record is:

```text
normalized allele × transcript × category
```

The hand-off uses one row per category assignment rather than a single mutually exclusive category column. A single allele–transcript pair may therefore produce multiple rows.

### 5.2 Allowed overlaps

Within one allele–transcript pair:

- `canonical` and `near_splice` are mutually exclusive by rule;
- `near_splice` and `deep_intronic` are mutually exclusive;
- `exonic_splicing_motif` and `deep_intronic` are mutually exclusive;
- `exonic_splicing_motif` MAY overlap `near_splice` in the first/last three exonic bases;
- `exonic_splicing_motif` MAY coexist with coding consequences;
- `canonical` takes precedence over a co-reported generic `splice_region_variant` term, but coding consequences remain attached.

Across different transcripts, no category is globally exclusive. The same genomic allele may be canonical for one transcript, exonic for another, and deep intronic for a third. Variant-level category sets MUST be the sorted union of transcript assignments and MUST retain pointers/counts back to the contributing transcripts.

### 5.3 No forced precedence at variant level

A `primary_category` MAY be calculated only for display, using this fixed order:

```text
canonical > near_splice > exonic_splicing_motif > deep_intronic
```

If used, it MUST be labeled as a presentation field, MUST NOT erase `category_set`, and MUST NOT be treated as evidence strength. Predictor applicability is evaluated against the complete category set.

## 6. Transcript scope

### 6.1 Evidence-preserving scope

Category assignment MUST initially consider **all transcript consequences returned by the configured VEP transcript source**. Principal-transcript flags affect ranking and display, not whether evidence is retained.

The default SQ2 configuration is:

```yaml
transcript_source: ensembl
assignment_scope: all_annotated_transcripts
reporting_scope: all_with_representative
```

The configurable transcript source may be:

- `ensembl`;
- `refseq`; or
- `merged`.

Runs using different transcript sources or releases MUST record those values and MUST NOT silently merge assignments as if their transcript universes were identical.

### 6.2 Transcript tiers

Every assignment SHOULD carry zero or more transcript-selection attributes:

- MANE Plus Clinical;
- MANE Select;
- Ensembl/VEP canonical;
- protein-coding biotype;
- transcript support level;
- APPRIS annotation.

The deterministic representative order remains:

1. MANE Plus Clinical;
2. MANE Select;
3. VEP canonical;
4. protein coding;
5. better (lower) transcript support level;
6. APPRIS principal;
7. lexical transcript identifier.

This order chooses a representative only. It MUST NOT delete other assignments or change their categories.

### 6.3 Optional views

VIPER or a report MAY request views such as `mane_only`, `principal_only`, `protein_coding_only`, or an explicit transcript allow-list. These are derived views. The unfiltered assignment table MUST remain available, and every view MUST record its filter. `deep_intronic` and exonic categories MUST NOT default to protein-coding-only because non-coding transcripts can have biologically meaningful splicing.

## 7. SNAIRA-Splice ↔ VIPER hand-off contract

### 7.1 Contract identity

The prototype contract is:

```text
contract_name: splicing_gap_viper_handoff
contract_version: 1.0.0
category_specification: TSG-SPLICE-CATEGORIES/1.0.0
```

Backward-incompatible field or semantic changes require a new major contract version. Additive optional fields require a minor version. The producer MUST fail on an unsupported requested major version.

### 7.2 VIPER/source → SNAIRA-Splice

The current manifest remains the invocation boundary. Required inputs are:

- `sample_id`;
- manifest version;
- selected small-variant VCF path (default `outputs.snv_pass_vcf`);
- input reference declaration;
- source pipeline name and phase when available.

Family, role, sex, and phenotype identifiers MAY be passed through but MUST NOT alter category assignment. SNAIRA-Splice MUST never modify the source manifest or VCF.

### 7.3 SNAIRA-Splice → VIPER bundle

The hand-off is a directory containing:

```text
handoff/
├── handoff_manifest.json
├── splice_category_assignments.tsv.gz
├── splice_variant_summary.tsv.gz
├── splice_predictor_evidence.tsv.gz       # only when ≥1 predictor ran
└── run_metadata.json
```

`splice_predictor_evidence.tsv.gz` MUST be absent—not an empty table suggesting completed analysis—when no predictor module ran. The hand-off manifest declares which modules ran and their statuses.

### 7.4 `handoff_manifest.json`

Required fields:

| Field | Type | Meaning |
|---|---|---|
| `contract_name` | string | Must equal `splicing_gap_viper_handoff`. |
| `contract_version` | semver string | Contract used to serialize the bundle. |
| `category_specification` | string | Must equal `TSG-SPLICE-CATEGORIES/1.0.0` for this version. |
| `pipeline_version` | string | SNAIRA-Splice version or commit. |
| `run_id` | string | Unique immutable run identifier. |
| `created_at` | ISO-8601 string | UTC creation time. |
| `assembly` | string | Assembly for all variant keys in the bundle. |
| `reference_fasta_sha256` | string | Reference identity. |
| `annotation_source` | string | Ensembl, RefSeq, or merged. |
| `annotation_release` | string | VEP/cache and transcript release. |
| `samples` | array | Sample IDs present in the bundle. |
| `modules` | array | Named modules with version and `completed`, `failed`, or `not_run`. |
| `files` | array | Relative path, media type, row count, byte count, and SHA-256 for each file. |

All paths in the manifest MUST be relative to the hand-off directory and MUST NOT contain `..` components.

### 7.5 `splice_category_assignments.tsv.gz`

One row represents one normalized allele × transcript × category assignment. Required columns are:

| Column | Requirement |
|---|---|
| `assembly` | Declared reference assembly. |
| `variant_key` | `assembly:CHROM:POS:REF:ALT`. |
| `chrom`, `pos`, `ref`, `alt` | Normalized allele fields. |
| `sample_id` | Manifest sample identifier. |
| `gene_id`, `gene_symbol` | Annotation identifiers; symbol may be empty. |
| `transcript_id`, `transcript_version` | Transcript identity; version may be empty only if unavailable. |
| `transcript_source`, `transcript_biotype`, `strand` | Transcript provenance/context. |
| `category` | One of the four category identifiers. |
| `category_subtype` | Donor/acceptor/boundary subtype or empty when not applicable. |
| `boundary_distance` | Minimum transcript-relative distance, or empty when not applicable. |
| `consequence_terms` | Complete sorted SO-term set for this transcript row. |
| `coding_consequence_terms` | Coding terms retained independently of category. |
| `mane_select`, `mane_plus_clinical`, `canonical_transcript`, `tsl`, `appris` | Transcript-ranking fields. |
| `category_specification` | Exact specification identifier/version. |
| `source_annotation_release` | Annotation release used for the assignment. |

Boolean values MUST be serialized consistently as `true`/`false`; unavailable values are empty, not `false`. Multi-value fields use a documented sorted delimiter and MUST NOT depend on input order.

### 7.6 `splice_variant_summary.tsv.gz`

This derived table contains one row per sample and normalized allele. Required fields are:

- assembly-aware variant key and allele fields;
- `sample_id`;
- sorted `category_set`;
- optional display-only `primary_category`;
- contributing transcript and gene counts/IDs;
- deterministic representative transcript and gene;
- principal-transcript flags;
- complete consequence-term union;
- predictor modules completed for the allele;
- pointers or stable join keys to transcript assignments and predictor evidence;
- source VCF and manifest identifiers.

VIPER MUST use `category_set`, not `primary_category`, for applicability and evidence integration.

### 7.7 Predictor evidence

When present, `splice_predictor_evidence.tsv.gz` follows the normalized schema in `docs/adding_predictors.md`. It joins through `variant_key`, `sample_id`, and optionally transcript ID. Category assignment and predictor evidence MUST remain separate rows/tables so a missing score cannot change a positional category.

### 7.8 Validation and failures

Before import, VIPER MUST validate:

- supported contract major version;
- exact category-specification identifier;
- checksums and row counts;
- one assembly per bundle;
- safe relative paths;
- uniqueness of atomic assignment rows;
- valid category and module-status enumerations;
- referential integrity between summary, transcript, and predictor tables.

Unsupported assembly, mixed assemblies, checksum failure, duplicate atomic records, or unsupported contract versions are fatal. A failed module MUST be declared and MUST NOT be treated as `not_run` or as a negative prediction.

## 8. Classification decision procedure

For each normalized allele and each configured transcript row:

1. Parse the complete VEP consequence set.
2. If donor and/or acceptor canonical terms are present, emit `canonical`; do not emit `near_splice` for that row.
3. Otherwise, if `splice_region_variant` is present, emit `near_splice`.
4. Independently, if the affected interval/junction overlaps a mature exon, emit `exonic_splicing_motif`.
5. Otherwise, if it is wholly intronic and more than 100 bases from both boundaries, emit `deep_intronic`.
6. If wholly intronic and 9–100 bases from the nearest boundary, retain it with the explicit `proximal_intronic_9_100` non-assignment reason.
7. Retain all consequence terms, coding terms, transcript-ranking attributes, annotation versions, and provenance.
8. Form the variant-level category set as the sorted union of all transcript assignments.

## 9. Worked examples

| Transcript-relative example | Assignment(s) for that transcript | Notes |
|---|---|---|
| `c.100+1G>A`, VEP donor | `canonical:donor` | Canonical term is authoritative. |
| `c.100+5G>A`, VEP splice region | `near_splice` | Donor-side intronic +3…+8. |
| Last exonic base, `missense_variant&splice_region_variant` | `near_splice`, `exonic_splicing_motif` | Coding term retained independently. |
| Synonymous variant 40 bases from both exon edges | `exonic_splicing_motif` | Category does not claim motif disruption. |
| Intronic variant 50 bases from nearest junction | no v1 category; `proximal_intronic_9_100` | Retained, not mislabeled as deep. |
| Intronic variant 101 bases from nearest junction | `deep_intronic` | Threshold is >100. |
| Canonical in ENST-A, exonic in ENST-B | corresponding rows for both categories | Variant summary category set contains both. |

## 10. Versioning and change control

This document is frozen as `1.0.0` for SQ2 prototype development. “Frozen” means implementations and tests may target it; it does not imply clinical validation.

Changes follow semantic versioning:

- **patch:** wording or examples that do not alter classification;
- **minor:** backward-compatible additive categories, fields, or optional subtypes;
- **major:** changed boundaries, exclusions, precedence, transcript universe semantics, or required hand-off fields.

Every change MUST update the document version and date, `CHANGELOG.md`, category fixtures, expected assignments, and hand-off validation tests. A future review SHOULD include clinical/splicing expertise before any clinical-facing release.

## 11. v1.0 review checklist

- [x] Canonical definition is explicit and excludes region-only consequences.
- [x] Near-splice exonic and intronic windows are inclusive and strand-independent through transcript orientation.
- [x] Exonic motif applicability and coding-consequence overlap are explicit.
- [x] Deep-intronic threshold and the 9–100-base gap are explicit.
- [x] Same-transcript and cross-transcript overlaps are specified.
- [x] Transcript inclusion, ranking, and derived filters are separated.
- [x] Assembly/resource identity and mixed-assembly failure behavior are specified.
- [x] VIPER input, output, provenance, module-state, and validation rules are specified.
- [x] No category is presented as a predictor result or clinical classification.

## 12. Known implementation gap

The current SNAIRA-Splice milestone implements canonical extraction and separately retains VEP `splice_region_variant` rows. It does not yet emit the complete v1.0 hand-off bundle, exon-overlap category rows, deep-intronic distances, or predictor evidence. This specification defines those next implementation targets without claiming that they have run.
