"""Canonical splice extraction and allele-level collapse."""

rule extract_canonical_splice:
    input: f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.tsv.gz"
    output:
        transcripts=f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.transcripts.tsv.gz",
        regions=f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.noncanonical_splice_region.tsv.gz"
    conda: "../envs/python.yaml"
    log: f"{OUT}/{{sample}}/logs/extract_canonical_splice.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/extract_canonical_splice.tsv"
    params:
        source_vcf=lambda wc: SAMPLE_DATA[wc.sample].input_vcf,
        manifest=lambda wc: SAMPLE_DATA[wc.sample].manifest_path,
        version=config["vep"]["cache_version"]
    shell:
        "python workflow/scripts/extract_vep_annotations.py --input {input:q} --canonical {output.transcripts:q} "
        "--noncanonical {output.regions:q} --sample-id {wildcards.sample:q} --source-vcf {params.source_vcf:q} "
        "--source-manifest {params.manifest:q} --annotation-version {params.version:q} > {log:q} 2>&1"


rule collapse_canonical_variants:
    input: f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.transcripts.tsv.gz"
    output: f"{OUT}/{{sample}}/03_canonical_splice/{{sample}}.canonical_splice.variants.tsv.gz"
    conda: "../envs/python.yaml"
    log: f"{OUT}/{{sample}}/logs/collapse_canonical_variants.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/collapse_canonical_variants.tsv"
    shell:
        "python workflow/scripts/collapse_canonical_variants.py --input {input:q} --output {output:q} > {log:q} 2>&1"
