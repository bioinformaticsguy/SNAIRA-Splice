"""VCF normalization rules."""

rule normalize_vcf:
    input:
        vcf=lambda wc: SAMPLE_DATA[wc.sample].input_vcf,
        reference=config["reference"]["fasta"],
        validation=f"{OUT}/{{sample}}/logs/input_validation/input_vcf.validation.json"
    output:
        vcf=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz",
        index=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz.tbi",
        stats=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalization.stats.txt"
    threads: config["resources"]["normalize"]["threads"]
    resources:
        mem_mb=config["resources"]["normalize"]["mem_mb"],
        runtime=config["resources"]["normalize"]["runtime"]
    conda: "../envs/bcftools.yaml"
    log: f"{OUT}/{{sample}}/logs/normalize_vcf.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/normalize_vcf.tsv"
    params:
        temp=config["temporary_directory"]
    shell:
        "mkdir -p {params.temp:q} && "
        "bcftools norm --threads {threads} --multiallelics -any --fasta-ref {input.reference:q} "
        "--check-ref e --output-type u {input.vcf:q} 2> {log:q} | "
        "bcftools annotate --set-id '%CHROM:%POS:%REF:%ALT' --output-type z --output {output.vcf:q} >> {log:q} 2>&1 && "
        "tabix --preset vcf {output.vcf:q} >> {log:q} 2>&1 && "
        "bcftools stats {output.vcf:q} > {output.stats:q} 2>> {log:q}"


rule extract_call_evidence:
    input: f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz"
    output: f"{OUT}/{{sample}}/01_normalized/{{sample}}.call_evidence.tsv.gz"
    resources:
        mem_mb=config["resources"]["python"]["mem_mb"],
        runtime=config["resources"]["python"]["runtime"]
    conda: "../envs/python.yaml"
    log: f"{OUT}/{{sample}}/logs/extract_call_evidence.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/extract_call_evidence.tsv"
    shell:
        "python workflow/scripts/extract_call_evidence.py --input {input:q} --output {output:q} "
        "--sample-id {wildcards.sample:q} > {log:q} 2>&1"
