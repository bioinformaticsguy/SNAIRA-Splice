# SNAIRA-Splice

SNAIRA-Splice is the first annotation component of **The Splicing Gap**, a future variant-prioritization framework. This release provides reproducible consequence annotation; it is not a clinical classifier and does not estimate the magnitude of a splice effect.

Development toward the VIPER-integrated SQ2 prototype is tracked in [`TODO.md`](TODO.md).

## Scope and scientific definition

A normalized allele is a canonical splice candidate when VEP assigns at least one transcript the Sequence Ontology term `splice_donor_variant` or `splice_acceptor_variant`. Terms joined with `&` are parsed individually. `splice_region_variant` is broader and is **not** canonical here; those rows are retained separately for a future near-splice module. VEP answers whether an allele overlaps an annotated consequence. A predictor such as SpliceAI would answer how strongly an allele may change splicing; no such score is fabricated by this release.

The workflow reads JSON manifests, validates inputs, normalizes small variants with bcftools, runs offline Ensembl VEP, extracts transcript rows, deterministically collapses canonical rows by allele, and creates sample/cohort summaries and provenance. Structural variants are out of scope.

## Layout

- `Snakefile` and `workflow/rules/`: modular workflow stages
- `workflow/scripts/`: testable Python command-line programs and shared pure functions
- `workflow/envs/`: focused pinned Conda environments
- `workflow/schemas/`: configuration and manifest schemas
- `config/`: defaults and examples
- `profiles/`: local and Snakemake 8 SLURM-executor profiles
- `scripts/`: explicit resource setup, validation, and CI test entry points
- `tests/`: unit fixtures and a cache-free miniature workflow
- `docs/`: detailed interfaces and operational documentation

## Installation and resources

Use Conda/Mamba on Linux:

```bash
conda env create -f environment.yaml
conda activate splicing-gap

bash scripts/setup_resources.sh \
  --assembly GRCh38 \
  --resource-dir resources \
  --vep-cache-version 113 \
  --species homo_sapiens \
  --download-reference \
  --download-vep-cache
```

The ordinary workflow never downloads large data. The restartable setup command downloads to a temporary directory, validates archive structure, builds FASTA indexes/dictionary, records SHA-256 checksums and versions, and creates completion markers last. `--force` replaces a requested installed resource. VEP itself is pinned in `workflow/envs/vep.yaml`; `--install-software` is available if a separately materialized VEP environment is desired. No root or system installation is used.

Update `config/config.yaml` after setup. The default VEP release is 113 and the default transcript source is Ensembl. `refseq` and `merged` select VEP's corresponding modes. MANE, canonical, TSL, and APPRIS annotations are configurable. Both annotated VCF and transcript-oriented TSV are required in this milestone to preserve traceability.

## Manifests and configuration

`manifests.source` may name a directory of `*.json`, one JSON manifest, or a text file containing one manifest path per line. Relative paths in a list are relative to that list. `manifests.vcf_key` defaults to `outputs.snv_pass_vcf`; change it to `outputs.snv_gvcf` only when gVCF annotation is intentionally desired. SV keys are never selected automatically.

Path resolution is controlled per manifest. With `path_base: manifest_directory`, output paths are relative to the JSON file's directory. With `output_directory`, `output_directory` is first resolved relative to the JSON directory and the selected output path is appended exactly once. With `absolute`, selected paths must be absolute. Already absolute selected paths remain absolute in the first two modes. See [docs/manifests.md](docs/manifests.md).

The example in the request says `path_base: manifest_directory`; therefore `snv_calls/HG002.pass.vcf.gz` resolves under the manifest directory, **not** beneath `output/giab_mini_hg002/HG002`. The latter is used only if `path_base` is `output_directory`. This prevents accidental double joining.

Validation rejects missing required fields, unsupported versions, unsafe/path-containing sample IDs, duplicate sample IDs, duplicate VCF paths, invalid path modes, and inconsistent manifest reference declarations. Missing input indexes are reported but permitted because downstream normalized files receive indexes under the result root. Input inspection then validates BGZF, VCF columns, sample names, contig overlap and `chr` naming against the configured FASTA index. It reports single- versus multi-sample input. Reference builds are never silently reinterpreted.

## Running

```bash
snakemake \
  --profile profiles/local \
  --configfile config/config.yaml \
  --dry-run

snakemake \
  --profile profiles/local \
  --configfile config/config.yaml

snakemake \
  --profile profiles/slurm \
  --configfile config/config.yaml
```

The SLURM profile uses `snakemake-executor-plugin-slurm`, pinned with Snakemake 8 in the development environment. Supply site-specific account/partition defaults on the command line or in a copied profile. Threads, memory (MB), and runtime (minutes) are configurable per stage.

Normalization uses `bcftools norm -m -any -f ... --check-ref e`: multialleles are split, indels left-aligned, and REF mismatches stop the job. Nothing is discarded or changed at source. All derived data, indexes, logs, and benchmarks are under `output_root`.

## Outputs

Each sample receives normalized VCF, raw VEP VCF/TSV and VEP HTML, canonical transcript and allele tables, a non-canonical splice-region table, and TSV/JSON/HTML summaries. `results/cohort/canonical_splice_variants.tsv.gz` concatenates allele-level candidates. `results/metadata/` contains resolved samples, manifest validation, and provenance including software/cache versions and SHA-256 checksums. See [docs/outputs.md](docs/outputs.md).

Representative transcript ordering is: MANE Plus Clinical, MANE Select, VEP canonical, protein coding, lower TSL, APPRIS principal, then lexical transcript ID. This selects a display representative only; all transcript rows remain available.

## Testing

```bash
bash scripts/run_test.sh
```

The test suite includes manifest/path failures, nested keys, combined SO terms, ranking, collapse, and a small Snakemake workflow driven by a mock VEP table. The mock tests parsing and reporting without suggesting VEP ran. A real VEP run requires the full cache and is an optional external integration test:

```bash
snakemake --profile profiles/local --configfile tests/config.test.yaml vep_annotate
```

That command is useful only after changing the test reference/cache to compatible full GRCh38 resources.

## Troubleshooting and limitations

- A REF mismatch is fatal by design; verify the assembly and FASTA rather than using a permissive normalization mode.
- A `chr`/non-`chr` contig mismatch is fatal. No automatic renaming occurs.
- Mixed reference declarations in one run are unsupported.
- Multi-sample VCFs are recorded and accepted, but outputs remain keyed by manifest sample; genotype-level subsetting is not performed.
- VEP is run twice (VCF and tabular modes) to keep both native trace output and explicit stable transcript columns.
- Static HTML is intentionally minimal. There is no clinical evidence model or splice-effect predictor.
- Ensembl cache availability and MANE/TSL content depend on the pinned release and transcript set.

To add a predictor, implement a rule, environment, and adapter under the `predictors/` directories and emit the normalized schema in [docs/adding_predictors.md](docs/adding_predictors.md). The recommended next module is a near-splice effect predictor consuming the separately retained `splice_region_variant` candidates.

## License and citation

Released under MIT; see `LICENSE`. Citation metadata is in `CITATION.cff`.
