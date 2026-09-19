"""Complete VEP transcript parsing and VEP/SpliceAI evidence integration."""

rule parse_all_vep_transcripts:
    input: f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.tsv.gz"
    output: f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.transcripts.tsv.gz"
    conda: "../envs/python.yaml"
    log: f"{OUT}/{{sample}}/logs/parse_all_vep_transcripts.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/parse_all_vep_transcripts.tsv"
    params:
        source_vcf=lambda wc: SAMPLE_DATA[wc.sample].input_vcf,
        manifest=lambda wc: SAMPLE_DATA[wc.sample].manifest_path,
        version=config["vep"]["cache_version"]
    shell:
        "python workflow/scripts/parse_vep_transcripts.py --input {input:q} --output {output:q} "
        "--sample-id {wildcards.sample:q} --source-vcf {params.source_vcf:q} "
        "--source-manifest {params.manifest:q} --annotation-version {params.version:q} > {log:q} 2>&1"


rule build_splice_candidates:
    input:
        vep=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.transcripts.tsv.gz",
        spliceai=f"{OUT}/{{sample}}/03_spliceai/{{sample}}.spliceai_evidence.tsv.gz",
        calls=f"{OUT}/{{sample}}/01_normalized/{{sample}}.call_evidence.tsv.gz"
    output:
        transcripts=f"{OUT}/{{sample}}/04_splice_candidates/{{sample}}.splice_candidates.transcripts.tsv.gz",
        variants=f"{OUT}/{{sample}}/04_splice_candidates/{{sample}}.splice_candidates.variants.tsv.gz",
        review=f"{OUT}/{{sample}}/04_splice_candidates/{{sample}}.splice_review.variants.tsv.gz"
    resources:
        mem_mb=config["resources"]["python"]["mem_mb"],
        runtime=config["resources"]["python"]["runtime"]
    conda: "../envs/python.yaml"
    log: f"{OUT}/{{sample}}/logs/build_splice_candidates.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/build_splice_candidates.tsv"
    params:
        candidate=config["spliceai"]["candidate_threshold"],
        review=config["spliceai"]["review_threshold"]
    shell:
        "python workflow/scripts/build_splice_candidates.py --vep {input.vep:q} --spliceai {input.spliceai:q} --call-evidence {input.calls:q} "
        "--candidate-threshold {params.candidate} --review-threshold {params.review} "
        "--transcripts {output.transcripts:q} --variants {output.variants:q} --review {output.review:q} "
        "> {log:q} 2>&1"
