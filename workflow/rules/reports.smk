"""Per-sample, cohort, and provenance reporting."""

rule sample_summary:
    input:
        variants=f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.variants.tsv.gz",
        transcripts=f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.transcripts.tsv.gz",
        regions=f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.noncanonical_splice_region.tsv.gz"
    output:
        tsv=f"{OUT}/{{sample}}/04_summary/{{sample}}.splice_summary.tsv",
        json=f"{OUT}/{{sample}}/04_summary/{{sample}}.splice_summary.json",
        html=f"{OUT}/{{sample}}/04_summary/{{sample}}.splice_summary.html"
    conda: "../envs/reporting.yaml"
    log: f"{OUT}/{{sample}}/logs/sample_summary.log"
    shell:
        "python workflow/scripts/summarize_results.py --variants {input.variants:q} --transcripts {input.transcripts:q} "
        "--regions {input.regions:q} --label {wildcards.sample:q} --tsv {output.tsv:q} --json {output.json:q} "
        "--html {output.html:q} > {log:q} 2>&1"


rule cohort_summary:
    input:
        variants=expand(f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.variants.tsv.gz", sample=SAMPLES),
        transcripts=expand(f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.transcripts.tsv.gz", sample=SAMPLES),
        regions=expand(f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.noncanonical_splice_region.tsv.gz", sample=SAMPLES)
    output:
        variants=f"{OUT}/cohort/canonical_splice_variants.tsv.gz",
        tsv=f"{OUT}/cohort/splice_summary.tsv",
        json=f"{OUT}/cohort/splice_summary.json",
        html=f"{OUT}/cohort/splice_summary.html"
    conda: "../envs/reporting.yaml"
    log: f"{OUT}/cohort/cohort_summary.log"
    shell:
        "python workflow/scripts/summarize_results.py --variants {input.variants:q} --transcripts {input.transcripts:q} "
        "--regions {input.regions:q} --label cohort --tsv {output.tsv:q} --json {output.json:q} "
        "--html {output.html:q} --cohort-table {output.variants:q} > {log:q} 2>&1"


rule run_metadata:
    input:
        cohort=f"{OUT}/cohort/splice_summary.json",
        samples=f"{OUT}/metadata/resolved_samples.tsv",
        reference=config["reference"]["fasta"],
        vep_stats=expand(f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.stats.txt", sample=SAMPLES)
    output: f"{OUT}/metadata/run_metadata.json"
    conda: "../envs/python.yaml"
    log: f"{OUT}/metadata/run_metadata.log"
    params:
        assembly=config["reference"]["assembly"],
        cache_version=config["vep"]["cache_version"],
        snakemake_version=SNAKEMAKE_VERSION
    shell:
        "python workflow/scripts/write_run_metadata.py --output {output:q} --config config/config.yaml "
        "--reference {input.reference:q} --resolved-samples {input.samples:q} --pipeline-version 0.1.0 "
        "--assembly {params.assembly:q} --vep-cache-version {params.cache_version:q} "
        "--snakemake-version {params.snakemake_version:q} --vep-stats {input.vep_stats:q} > {log:q} 2>&1"
