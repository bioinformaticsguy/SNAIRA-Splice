# SNAIRA-Splice

SNAIRA-Splice is a standalone research workflow for finding splice-relevant SNVs and small indels. It normalizes a VCF, annotates transcript consequences with Ensembl VEP, runs SpliceAI locally, and combines both evidence types in machine-readable tables and a portable, variant-centric HTML report.

Development is tracked in [`TODO.md`](TODO.md). VIPER and CALIGO integration are explicitly outside the current MVP.
The frozen SQ2 category definitions and VIPER exchange contract are documented in
[`docs/splice-category-specification-v1.0.md`](docs/splice-category-specification-v1.0.md).

## Scope and scientific definition

A normalized allele is a canonical splice candidate when VEP assigns at least one transcript the Sequence Ontology term `splice_donor_variant` or `splice_acceptor_variant`. Terms joined with `&` are parsed individually. `splice_region_variant` is broader and is **not** canonical. VEP tells us where a variant lies and its transcript consequence; SpliceAI predicts whether the DNA change may alter donor or acceptor use. A SpliceAI prediction does **not** demonstrate that an abnormal RNA transcript occurs.

The main candidate set is deliberately inclusive: VEP donor, acceptor, or splice-region consequences are retained regardless of SpliceAI, and any other supported allele is retained when `SpliceAI_max >= 0.20` by default. A review table starts at `0.05`. Missing predictions remain missing and are never converted to zero. Structural variants are out of scope.

## Quick start

Required biological inputs are a small-variant VCF, sample ID, matching GRCh38 FASTA, Ensembl VEP cache, SpliceAI installation/models, and a GRCh38 SpliceAI gene annotation. Create the development environment, then install the large resources explicitly:

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
  --download-vep-cache \
  --install-spliceai
```

Set `reference.*`, `vep.cache_dir`, and `spliceai.annotation` in `config/config.yaml`. To run one sample without writing a manifest yourself:

```bash
python scripts/run_snaira_splice.py \
  --vcf /absolute/path/sample.vcf.gz \
  --sample-id S001 \
  --outdir results \
  --config config/config.yaml
```

The final report is `results/S001/05_report/S001.snaira_splice.html`. Use `--dry-run` to inspect the DAG. Existing multi-sample manifest execution remains supported below.

The ordinary workflow never downloads large data. The restartable setup command downloads to a temporary directory, validates archive structure, builds FASTA indexes/dictionary, records SHA-256 checksums and versions, and creates completion markers last. `--force` replaces a requested installed resource. VEP and SpliceAI are pinned in focused rule environments. `--install-software` and `--install-spliceai` can materialize those environments under the resource directory. No root or system installation is used. SpliceAI 1.3.1 has non-commercial use restrictions and its upstream repository is archived; review its license before use. See [docs/spliceai.md](docs/spliceai.md).

Update `config/config.yaml` after setup. The default VEP release is 113 and the default transcript source is Ensembl. `refseq` and `merged` select VEP's corresponding modes. MANE, canonical, TSL, and APPRIS annotations are configurable. Both annotated VCF and transcript-oriented TSV are required in this milestone to preserve traceability.

## Manifests and configuration

`manifests.source` may name a directory of `*.json`, one JSON manifest, or a text file containing one manifest path per line. Relative paths in a list are relative to that list. `manifests.vcf_key` defaults to `outputs.snv_pass_vcf`; change it to `outputs.snv_gvcf` only when gVCF annotation is intentionally desired. SV keys are never selected automatically.

Path resolution is controlled per manifest. With `path_base: manifest_directory`, output paths are relative to the JSON file's directory. With `output_directory`, `output_directory` is first resolved relative to the JSON directory and the selected output path is appended exactly once. With `absolute`, selected paths must be absolute. Already absolute selected paths remain absolute in the first two modes. See [docs/manifests.md](docs/manifests.md).

The example in the request says `path_base: manifest_directory`; therefore `snv_calls/HG002.pass.vcf.gz` resolves under the manifest directory, **not** beneath `output/giab_mini_hg002/HG002`. The latter is used only if `path_base` is `output_directory`. This prevents accidental double joining.

Validation rejects missing required fields, unsupported versions, unsafe/path-containing sample IDs, duplicate sample IDs, duplicate VCF paths, invalid path modes, and inconsistent manifest reference declarations. Missing input indexes are reported but permitted because downstream normalized files receive indexes under the result root. Input inspection then validates BGZF, VCF columns, sample names, contig overlap and `chr` naming against the configured FASTA index. It reports single- versus multi-sample input. Reference builds are never silently reinterpreted.

## Running

Local execution is the normal development path and is appropriate for a laptop:

```bash
snakemake \
  --profile profiles/local \
  --configfile config/config.yaml \
  --dry-run

snakemake \
  --profile profiles/local \
  --configfile config/config.yaml
```

SLURM is an optional deployment mode. A direct profile invocation is supported:

```bash
snakemake \
  --profile profiles/slurm \
  --configfile config/config.yaml
```

For unattended cluster runs, use the documented controller submission model, which keeps site-specific account, partition, email, and installation paths out of Git:

```bash
cp scripts/slurm/submit_snaira_splice_controller.local.example.sh \
  scripts/slurm/submit_snaira_splice_controller.local.sh

bash scripts/slurm/check_slurm_profile.sh config/config.yaml

bash scripts/slurm/submit_snaira_splice_controller.local.sh \
  --configfile config/config.yaml
```

See [docs/slurm.md](docs/slurm.md) for setup, logs, monitoring, shared Conda environments, and safe restart guidance.

The SLURM profile uses `snakemake-executor-plugin-slurm`, pinned with Snakemake 8 in the development environment. The controller launcher supplies site-specific values without modifying the versioned profile. Threads, memory (MB), and runtime (minutes) remain configurable per stage.

Normalization uses `bcftools norm -m -any -f ... --check-ref e`: multialleles are split, indels left-aligned, and REF mismatches stop the job. Nothing is discarded or changed at source. All derived data, indexes, logs, and benchmarks are under `output_root`.

## Outputs

Each sample retains normalized VCF, raw VEP outputs, a SpliceAI-annotated VCF, full parsed evidence, joined transcript candidates, collapsed allele candidates, a broader review table, and `{sample}.snaira_splice.html`. Legacy canonical-only tables and cohort summaries remain for compatibility. See [docs/outputs.md](docs/outputs.md).

Representative transcript ordering is: MANE Plus Clinical, MANE Select, VEP canonical, protein coding, lower TSL, APPRIS principal, then lexical transcript ID. This selects a display representative only; all transcript rows remain available.

## Testing

```bash
bash scripts/run_test.sh
```

The test suite includes manifest/path failures, nested keys, combined SO terms, ranking, SpliceAI INFO parsing and missingness, candidate thresholds, collapse, HTML structure, and a cache-free Snakemake workflow driven by explicit mock VEP and SpliceAI annotations. Synthetic fixtures validate software behavior, not SpliceAI biology. A real integration run requires the full external resources:

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
- SpliceAI's configured maximum distance is a model/reporting window, not evidence that every event in that window is biologically meaningful.
- Exact transcript-relative distance to exon boundaries is not yet calculated. Noncanonical intronic rows are therefore labelled `intronic_noncanonical`, never automatically `deep_intronic`.
- SpliceAI 1.3.1 supports SNVs and simple indels subject to its own input constraints; unsupported alleles and absent annotations are reported distinctly.
- Ensembl cache availability and MANE/TSL content depend on the pinned release and transcript set.
- This is research software, not a pathogenicity classifier or clinical diagnostic system.

To add a predictor, implement a separate rule, environment, and parser following [docs/adding_predictors.md](docs/adding_predictors.md). Pangolin is the recommended next comparison module after validating this SpliceAI MVP on curated examples; it should not replace or overwrite SpliceAI evidence.

## License and citation

Released under MIT; see `LICENSE`. Citation metadata is in `CITATION.cff`.
