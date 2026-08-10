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
        "--check-ref e --output-type z --output {output.vcf:q} {input.vcf:q} > {log:q} 2>&1 && "
        "tabix --preset vcf {output.vcf:q} >> {log:q} 2>&1 && "
        "bcftools stats {output.vcf:q} > {output.stats:q} 2>> {log:q}"
