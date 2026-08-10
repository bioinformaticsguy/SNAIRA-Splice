"""Ensembl VEP annotation rules."""

VEP_FIELDS = ",".join([
    "Uploaded_variation", "Location", "Allele", "Gene", "Feature", "Feature_type", "Consequence",
    "IMPACT", "SYMBOL", "BIOTYPE", "EXON", "INTRON", "HGVSc", "HGVSp", "cDNA_position",
    "CDS_position", "Protein_position", "Amino_acids", "Codons", "Existing_variation", "DISTANCE",
    "STRAND", "FLAGS", "VARIANT_CLASS", "SYMBOL_SOURCE", "HGNC_ID", "CANONICAL", "MANE_SELECT",
    "MANE_PLUS_CLINICAL", "TSL", "APPRIS", "REF_ALLELE"
])

VEP_ANNOTATION_FLAGS = []
if config["vep"]["transcript_set"] == "refseq":
    VEP_ANNOTATION_FLAGS.append("--refseq")
elif config["vep"]["transcript_set"] == "merged":
    VEP_ANNOTATION_FLAGS.append("--merged")
if config["vep"]["include_mane"]:
    VEP_ANNOTATION_FLAGS.append("--mane")
if config["vep"]["include_canonical"]:
    VEP_ANNOTATION_FLAGS.append("--canonical")
if config["vep"]["include_tsl"]:
    VEP_ANNOTATION_FLAGS.append("--tsl")
VEP_ANNOTATION_FLAGS.append("--appris")
VEP_ANNOTATION_FLAGS = " ".join(VEP_ANNOTATION_FLAGS)


rule vep_annotate:
    input:
        vcf=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz",
        index=f"{OUT}/{{sample}}/01_normalized/{{sample}}.normalized.vcf.gz.tbi"
    output:
        vcf=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.vcf.gz",
        index=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.vcf.gz.tbi",
        tsv=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.tsv.gz",
        html=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.summary.html",
        stats=f"{OUT}/{{sample}}/02_vep/{{sample}}.vep.stats.txt"
    threads: config["vep"]["forks"]
    resources:
        mem_mb=config["resources"]["vep"]["mem_mb"],
        runtime=config["resources"]["vep"]["runtime"]
    conda: "../envs/vep.yaml"
    log: f"{OUT}/{{sample}}/logs/vep_annotate.log"
    benchmark: f"{OUT}/{{sample}}/benchmarks/vep_annotate.tsv"
    params:
        cache=config["vep"]["cache_directory"], version=config["vep"]["cache_version"],
        species=config["vep"]["species"], assembly=config["vep"]["assembly"],
        fasta=config["reference"]["fasta"], flags=VEP_ANNOTATION_FLAGS, fields=VEP_FIELDS,
        offline="--offline" if config["vep"]["offline"] else ""
    shell:
        "vep --input_file {input.vcf:q} --output_file STDOUT --vcf --compress_output bgzip --force_overwrite "
        "{params.offline} --cache --dir_cache {params.cache:q} --cache_version {params.version} "
        "--species {params.species:q} --assembly {params.assembly:q} --fasta {params.fasta:q} --fork {threads} "
        "--symbol --biotype --variant_class --hgvs --numbers --hgnc --no_stats {params.flags} 2> {log:q} > {output.vcf:q} && "
        "tabix --preset vcf {output.vcf:q} >> {log:q} 2>&1 && "
        "vep --input_file {input.vcf:q} --output_file STDOUT --tab --compress_output gzip --force_overwrite "
        "{params.offline} --cache --dir_cache {params.cache:q} --cache_version {params.version} "
        "--species {params.species:q} --assembly {params.assembly:q} --fasta {params.fasta:q} --fork {threads} "
        "--fields {params.fields:q} --stats_file {output.html:q} {params.flags} 2>> {log:q} > {output.tsv:q} && "
        "vep --help 2>&1 | head -n 2 > {output.stats:q}"
