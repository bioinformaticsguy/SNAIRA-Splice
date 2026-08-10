"""SNAIRA-Splice: canonical splice consequence annotation workflow."""

from pathlib import Path
import sys
import snakemake
from snakemake.utils import validate

configfile: "config/config.yaml"
validate(config, "workflow/schemas/config.schema.yaml")
sys.path.insert(0, str(Path("workflow/scripts").resolve()))
from manifest_utils import load_samples

MANIFEST_SOURCE = Path(config["manifests"]["source"])
SAMPLES_RECORDS, MANIFEST_REPORT = load_samples(
    MANIFEST_SOURCE,
    config["manifests"]["vcf_key"],
    config["manifests"].get("index_key"),
    require_files=True,
)
if not MANIFEST_REPORT["valid"]:
    raise WorkflowError("Manifest validation failed:\n- " + "\n- ".join(MANIFEST_REPORT["errors"]))
SAMPLE_DATA = {record.sample_id: record for record in SAMPLES_RECORDS}
SAMPLES = sorted(SAMPLE_DATA)
OUT = config["output_root"].rstrip("/")
SNAKEMAKE_VERSION = snakemake.__version__

rule all:
    input:
        f"{OUT}/metadata/manifest_validation.json",
        f"{OUT}/metadata/resolved_samples.tsv",
        expand(f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.vcf.gz", sample=SAMPLES),
        expand(f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.tsv.gz", sample=SAMPLES),
        expand(f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.transcripts.tsv.gz", sample=SAMPLES),
        expand(f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.variants.tsv.gz", sample=SAMPLES),
        expand(f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.noncanonical_splice_region.tsv.gz", sample=SAMPLES),
        expand(f"{OUT}/{{sample}}/04_summary/{{sample}}.splice_summary.html", sample=SAMPLES),
        f"{OUT}/cohort/canonical_splice_variants.tsv.gz",
        f"{OUT}/cohort/splice_summary.html",
        f"{OUT}/metadata/run_metadata.json"

include: "workflow/rules/common.smk"
include: "workflow/rules/normalize.smk"
include: "workflow/rules/vep.smk"
include: "workflow/rules/canonical_splice.smk"
include: "workflow/rules/reports.smk"
