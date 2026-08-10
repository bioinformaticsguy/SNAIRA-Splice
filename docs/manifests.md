# Manifest resolution and validation

The selected field defaults to `outputs.snv_pass_vcf`; dotted-key lookup is literal and fails if any component is absent. The corresponding index key defaults to `outputs.snv_pass_vcf_index`. If the index field is absent, `<vcf>.tbi` is inferred and its absence is a warning because source files are never modified.

Given `/data/family/manifest.json`:

| `path_base` | selected value | resolved path |
|---|---|---|
| `manifest_directory` | `snv_calls/S1.vcf.gz` | `/data/family/snv_calls/S1.vcf.gz` |
| `output_directory` with `output_directory: output/S1` | `snv_calls/S1.vcf.gz` | `/data/family/output/S1/snv_calls/S1.vcf.gz` |
| `absolute` | `/archive/S1.vcf.gz` | `/archive/S1.vcf.gz` |

An absolute selected path in the first two modes is kept absolute. `output_directory` itself may be absolute. The selected path is never prepended with both the manifest directory and output directory more than once. Under `absolute`, a relative selected value is an error.

Directory discovery is non-recursive and sorted. A list supports blank lines and `#` comments; relative entries are resolved against the list file. Supported manifest version is `1.0`. Sample IDs may contain letters, digits, hyphens, periods, and underscores, but not slashes or leading punctuation.

The resolved table includes sample/family/role/sex, manifest and VCF/index absolute paths, reference declaration, source pipeline and phase, and manifest SHA-256. Validation JSON contains all errors and warnings. Different literal `reference` declarations are treated as inconsistent; configure or standardize upstream manifests rather than coercing them.
