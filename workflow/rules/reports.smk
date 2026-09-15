"""Per-sample, cohort, and provenance reporting."""

rule standalone_splice_report:
    input:
        candidates=f"{OUT}/{{sample}}/04_splice_candidates/{{sample}}.splice_candidates.variants.tsv.gz",
        review=f"{OUT}/{{sample}}/04_splice_candidates/{{sample}}.splice_review.variants.tsv.gz",
        transcripts=f"{OUT}/{{sample}}/04_splice_candidates/{{sample}}.splice_candidates.transcripts.tsv.gz",
        evidence=f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai_evidence.tsv.gz",
        vep_version=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.stats.txt",
        spliceai_version=f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai.version.txt",
        reference=config["reference"]["fasta"],
        annotation=config["spliceai"]["annotation"]
    output: f"{OUT}/{{sample}}/05_report/{{sample}}.snaira_splice.html"
    resources:
        mem_mb=config["resources"]["reporting"]["mem_mb"],
        runtime=config["resources"]["reporting"]["runtime"]
    conda: "../envs/reporting.yaml"
    log: f"{OUT}/{{sample}}/logs/standalone_splice_report.log"
    params:
        assembly=config["reference"]["assembly"],
        pipeline_version=PIPELINE_VERSION,
        run_date=RUN_DATE,
        mode="local_masked" if config["spliceai"]["masked"] else "local_unmasked",
        distance=config["spliceai"]["max_distance"],
        candidate=config["spliceai"]["candidate_threshold"],
        review=config["spliceai"]["review_threshold"],
        config_checksum=CONFIG_CHECKSUM
    shell:
        "python workflow/scripts/generate_report.py --candidates {input.candidates:q} --review {input.review:q} "
        "--transcripts {input.transcripts:q} --spliceai-evidence {input.evidence:q} --output {output:q} "
        "--sample-id {wildcards.sample:q} --assembly {params.assembly:q} --pipeline-version {params.pipeline_version:q} "
        "--run-date {params.run_date:q} --vep-version-file {input.vep_version:q} "
        "--spliceai-version-file {input.spliceai_version:q} --spliceai-mode {params.mode:q} "
        "--spliceai-max-distance {params.distance} --candidate-threshold {params.candidate} "
        "--review-threshold {params.review} --reference {input.reference:q} --annotation {input.annotation:q} "
        "--config-checksum {params.config_checksum:q} > {log:q} 2>&1"

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
        vep_stats=expand(f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.stats.txt", sample=SAMPLES),
        spliceai_versions=expand(f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai.version.txt", sample=SAMPLES),
        annotation=config["spliceai"]["annotation"]
    output: f"{OUT}/metadata/run_metadata.json"
    conda: "../envs/python.yaml"
    log: f"{OUT}/metadata/run_metadata.log"
    params:
        assembly=config["reference"]["assembly"],
        cache_version=config["vep"]["cache_version"],
        snakemake_version=SNAKEMAKE_VERSION,
        pipeline_version=PIPELINE_VERSION,
        config_checksum=CONFIG_CHECKSUM,
        spliceai_mode="local_masked" if config["spliceai"]["masked"] else "local_unmasked",
        spliceai_distance=config["spliceai"]["max_distance"]
    shell:
        "python workflow/scripts/write_run_metadata.py --output {output:q} --config-checksum {params.config_checksum:q} "
        "--reference {input.reference:q} --resolved-samples {input.samples:q} --pipeline-version {params.pipeline_version:q} "
        "--assembly {params.assembly:q} --vep-cache-version {params.cache_version:q} "
        "--snakemake-version {params.snakemake_version:q} --vep-stats {input.vep_stats:q} "
        "--spliceai-version-files {input.spliceai_versions:q} --spliceai-annotation {input.annotation:q} "
        "--spliceai-mode {params.spliceai_mode:q} --spliceai-max-distance {params.spliceai_distance} "
        "> {log:q} 2>&1"
