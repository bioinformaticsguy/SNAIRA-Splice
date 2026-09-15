#!/usr/bin/env python3
"""Convert the complete VEP tabular output into stable transcript rows."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from io_utils import atomic_tsv

FIELDS = [
    "sample_id",
    "chrom",
    "pos",
    "ref",
    "alt",
    "normalized_variant_id",
    "symbol",
    "gene_id",
    "transcript_id",
    "feature_type",
    "biotype",
    "strand",
    "exon",
    "intron",
    "hgvsc",
    "hgvsp",
    "mane_select",
    "mane_plus_clinical",
    "canonical",
    "tsl",
    "appris",
    "consequence",
    "impact",
    "existing_variation",
    "annotation_version",
    "source_vcf",
    "source_manifest",
]


def _location(value: str) -> tuple[str, str]:
    chrom, interval = value.split(":", 1)
    return chrom, interval.split("-", 1)[0]


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--source-vcf", required=True)
    parser.add_argument("--source-manifest", required=True)
    parser.add_argument("--annotation-version", required=True)
    args = parser.parse_args()
    rows: list[dict[str, str]] = []
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        lines = (
            line[1:] if line.startswith("#Uploaded_variation") else line for line in handle if not line.startswith("##")
        )
        for source in csv.DictReader(lines, delimiter="\t"):
            chrom, pos = _location(source["Location"])
            ref, alt = source.get("REF_ALLELE", ""), source.get("Allele", "")
            uploaded = source.get("Uploaded_variation", "")
            # Normalization assigns this exact ID before VEP. Fall back for old fixtures.
            variant_id = uploaded if uploaded.count(":") == 3 else f"{chrom}:{pos}:{ref}:{alt}"
            parts = variant_id.split(":", 3)
            if len(parts) == 4:
                chrom, pos, ref, alt = parts
            rows.append(
                {
                    "sample_id": args.sample_id,
                    "chrom": chrom,
                    "pos": pos,
                    "ref": ref,
                    "alt": alt,
                    "normalized_variant_id": variant_id,
                    "symbol": source.get("SYMBOL", ""),
                    "gene_id": source.get("Gene", ""),
                    "transcript_id": source.get("Feature", ""),
                    "feature_type": source.get("Feature_type", ""),
                    "biotype": source.get("BIOTYPE", ""),
                    "strand": source.get("STRAND", ""),
                    "exon": source.get("EXON", ""),
                    "intron": source.get("INTRON", ""),
                    "hgvsc": source.get("HGVSc", ""),
                    "hgvsp": source.get("HGVSp", ""),
                    "mane_select": source.get("MANE_SELECT", ""),
                    "mane_plus_clinical": source.get("MANE_PLUS_CLINICAL", ""),
                    "canonical": source.get("CANONICAL", ""),
                    "tsl": source.get("TSL", ""),
                    "appris": source.get("APPRIS", ""),
                    "consequence": source.get("Consequence", ""),
                    "impact": source.get("IMPACT", ""),
                    "existing_variation": source.get("Existing_variation", ""),
                    "annotation_version": args.annotation_version,
                    "source_vcf": args.source_vcf,
                    "source_manifest": args.source_manifest,
                }
            )
    atomic_tsv(args.output, rows, FIELDS, gzip_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
