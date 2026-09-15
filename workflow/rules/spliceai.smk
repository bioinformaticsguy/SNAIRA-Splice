"""Local SpliceAI prediction and evidence parsing."""

rule spliceai_predict:
    input:
        vcf=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz",
        index=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz.tbi",
        reference=config["reference"]["fasta"],
        annotation=config["spliceai"]["annotation"]
    output:
        vcf=f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai.vcf.gz",
        index=f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai.vcf.gz.tbi",
        version=f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai.version.txt"
    threads: config["resources"]["spliceai"]["threads"]
    resources:
        mem_mb=config["resources"]["spliceai"]["mem_mb"],
        runtime=config["resources"]["spliceai"]["runtime"]
    conda: "../envs/spliceai.yaml"
    log: f"{OUT}/{{sample}}/logs/spliceai_predict.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/spliceai_predict.tsv"
    params:
        distance=config["spliceai"]["max_distance"],
        masked=1 if config["spliceai"]["masked"] else 0
    shell:
        "temporary=$(mktemp {output.vcf:q}.XXXXXX.vcf) && "
        "trap 'rm -f \"$temporary\"' EXIT && "
        "spliceai -I {input.vcf:q} -O \"$temporary\" -R {input.reference:q} -A {input.annotation:q} "
        "-D {params.distance} -M {params.masked} > {log:q} 2>&1 && "
        "bgzip -c \"$temporary\" > {output.vcf:q} && "
        "tabix -f -p vcf {output.vcf:q} >> {log:q} 2>&1 && "
        "python -c 'import importlib.metadata; print(importlib.metadata.version(\"spliceai\"))' > {output.version:q}"


rule parse_spliceai:
    input: f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai.vcf.gz"
    output: f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai_evidence.tsv.gz"
    conda: "../envs/python.yaml"
    log: f"{OUT}/{{sample}}/logs/parse_spliceai.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/parse_spliceai.tsv"
    shell:
        "python workflow/scripts/parse_spliceai_vcf.py --input {input:q} --output {output:q} "
        "--sample-id {wildcards.sample:q} > {log:q} 2>&1"
