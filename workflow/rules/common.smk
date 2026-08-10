"""Manifest metadata and source-input validation rules."""

rule resolve_manifests:
    input:
        lambda wc: [record.manifest_path for record in SAMPLES_RECORDS]
    output:
        table=f"{OUT}/metadata/resolved_samples.tsv",
        report=f"{OUT}/metadata/manifest_validation.json"
    conda: "../envs/python.yaml"
    log: f"{OUT}/metadata/resolve_manifests.log"
    params:
        source=str(MANIFEST_SOURCE),
        vcf_key=config["manifests"]["vcf_key"],
        index_key=config["manifests"]["index_key"]
    shell:
        "python workflow/scripts/parse_manifests.py "
        "--source {params.source:q} --vcf-key {params.vcf_key:q} --index-key {params.index_key:q} "
        "--table {output.table:q} --report {output.report:q} > {log:q} 2>&1"


rule validate_input_vcf:
    input:
        vcf=lambda wc: SAMPLE_DATA[wc.sample].input_vcf,
        fai=config["reference"]["fai"],
        manifests=f"{OUT}/metadata/manifest_validation.json"
    output:
        report=f"{OUT}/{{sample}}/logs/input_validation/input_vcf.validation.json"
    conda: "../envs/bcftools.yaml"
    log: f"{OUT}/{{sample}}/logs/input_validation/validate_input_vcf.log"
    shell:
        "python workflow/scripts/validate_vcf.py --vcf {input.vcf:q} --sample-id {wildcards.sample:q} "
        "--reference-fai {input.fai:q} --output {output.report:q} > {log:q} 2>&1"
