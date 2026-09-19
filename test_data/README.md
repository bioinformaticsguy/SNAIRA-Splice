# Quick-test dataset

SNAIRA-Splice ships a deliberately tiny, synthetic, version-controlled
quick-test fixture. Its canonical files live in [`tests/data/`](../tests/data)
and its one-sample manifest is in [`tests/manifests/`](../tests/manifests).
Keeping one source of truth prevents the test inputs and CI fixtures from
drifting apart.

Run the complete cache-free synthetic workflow from the repository root:

```bash
conda activate snaira-splice
bash scripts/run_quick_test.sh
```

It produces:

```text
tests/work/e2e/SYNTHETIC-1.snaira_splice.html
```

The fixture contains a miniature GRCh38-like reference, one four-allele VCF,
mock VEP tabular annotations, and mock SpliceAI annotations. It deliberately
includes both comma-separated and ampersand-separated VEP consequence forms.
The run validates workflow wiring, consequence parsing, candidate retention,
table generation, and HTML report generation without downloading a VEP cache
or SpliceAI model.

It does **not** validate VEP or SpliceAI biological predictions. Use the
regional smoke test with real GRCh38 resources for that integration path.
