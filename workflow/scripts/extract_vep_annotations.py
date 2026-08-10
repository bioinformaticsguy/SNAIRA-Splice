#!/usr/bin/env python3
"""Extract canonical and non-canonical transcript consequences from VEP TSV."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from io_utils import atomic_tsv
from splice_utils import canonical_splice_type, consequence_terms

FIELDS = [
    "variant_key",
    "chrom",
    "pos",
    "ref",
    "alt",
    "sample_id",
    "gene_symbol",
    "gene_id",
    "transcript_id",
    "transcript_biotype",
    "consequence",
    "canonical_splice_type",
    "exon",
    "intron",
    "strand",
    "hgvsc",
    "canonical_transcript",
    "mane_select",
    "mane_plus_clinical",
    "transcript_support_level",
    "appris",
    "existing_variant_id",
    "vep_impact",
    "source_annotation_version",
    "source_vcf",
    "source_manifest",
]


def parse_location(location: str) -> tuple[str, str]:
    chrom, positions = location.split(":", 1)
    return chrom, positions.split("-", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--canonical", required=True, type=Path)
    parser.add_argument("--noncanonical", required=True, type=Path)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--source-vcf", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--annotation-version", required=True)
    args = parser.parse_args()
    canonical: list[dict[str, str]] = []
    regions: list[dict[str, str]] = []
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        lines = (
            line[1:] if line.startswith("#Uploaded_variation") else line for line in handle if not line.startswith("##")
        )
        reader = csv.DictReader(lines, delimiter="\t")
        for source in reader:
            consequence = source.get("Consequence", "")
            terms = consequence_terms(consequence)
            splice_type = canonical_splice_type(consequence)
            chrom, pos = parse_location(source["Location"])
            uploaded = source.get("Uploaded_variation", "")
            ref = source.get("REF_ALLELE", "")
            alt = source.get("Allele", "")
            row = {
                "variant_key": f"{chrom}:{pos}:{ref}:{alt}",
                "chrom": chrom,
                "pos": pos,
                "ref": ref,
                "alt": alt,
                "sample_id": args.sample_id,
                "gene_symbol": source.get("SYMBOL", ""),
                "gene_id": source.get("Gene", ""),
                "transcript_id": source.get("Feature", ""),
                "transcript_biotype": source.get("BIOTYPE", ""),
                "consequence": consequence,
                "canonical_splice_type": splice_type or "",
                "exon": source.get("EXON", ""),
                "intron": source.get("INTRON", ""),
                "strand": source.get("STRAND", ""),
                "hgvsc": source.get("HGVSc", ""),
                "canonical_transcript": source.get("CANONICAL", ""),
                "mane_select": source.get("MANE_SELECT", ""),
                "mane_plus_clinical": source.get("MANE_PLUS_CLINICAL", ""),
                "transcript_support_level": source.get("TSL", ""),
                "appris": source.get("APPRIS", ""),
                "existing_variant_id": source.get("Existing_variation", uploaded),
                "vep_impact": source.get("IMPACT", ""),
                "source_annotation_version": args.annotation_version,
                "source_vcf": args.source_vcf,
                "source_manifest": args.source_manifest,
            }
            if splice_type:
                canonical.append(row)
            elif "splice_region_variant" in terms:
                regions.append(row)
    atomic_tsv(args.canonical, canonical, FIELDS, gzip_output=True)
    atomic_tsv(args.noncanonical, regions, FIELDS, gzip_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
