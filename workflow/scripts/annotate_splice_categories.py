#!/usr/bin/env python3
"""Add transcript-aware SQ2 v1.0 splice categories to parsed VEP rows."""

from __future__ import annotations

import argparse
import csv
import gzip
import re
from collections import defaultdict
from pathlib import Path

from category_utils import TranscriptModel, classify_transcript, normalized_transcript_id
from io_utils import atomic_tsv

CATEGORY_FIELDS = [
    "category_set",
    "category_assignment_status",
    "category_assignment_reason",
    "nearest_junction_distance",
    "nearest_junction_type",
]
ASSIGNMENT_FIELDS = [
    "sample_id", "normalized_variant_id", "chrom", "pos", "ref", "alt", "gene_id", "symbol", "transcript_id",
    "strand", "consequence", "category", "category_assignment_status", "category_assignment_reason",
    "nearest_junction_distance", "nearest_junction_type", "category_specification", "gtf_path",
]


def _attributes(value: str) -> dict[str, str]:
    return {key: item for key, item in re.findall(r'([A-Za-z_]+) "([^"]+)"', value)}


def load_models(gtf: Path, transcript_ids: set[str]) -> dict[str, TranscriptModel]:
    """Load only exons for transcripts seen in the VEP table."""
    exons: dict[str, list[tuple[int, int]]] = defaultdict(list)
    metadata: dict[str, tuple[str, str]] = {}
    opener = gzip.open if gtf.suffix == ".gz" else open
    with opener(gtf, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            fields = line.rstrip("\n").split("\t")
            if len(fields) != 9 or fields[2] != "exon":
                continue
            attributes = _attributes(fields[8])
            transcript_id = normalized_transcript_id(attributes.get("transcript_id", ""))
            if transcript_id not in transcript_ids:
                continue
            exons[transcript_id].append((int(fields[3]), int(fields[4])))
            metadata[transcript_id] = (fields[0], fields[6])
    return {
        transcript_id: TranscriptModel(
            transcript_id,
            metadata[transcript_id][0],
            metadata[transcript_id][1],
            tuple(sorted(values)),
        )
        for transcript_id, values in exons.items()
    }


def validate_gtf_assembly(gtf: Path, assembly: str) -> None:
    """Reject an Ensembl GTF whose declared genome build conflicts with config."""
    opener = gzip.open if gtf.suffix == ".gz" else open
    with opener(gtf, "rt", encoding="utf-8") as handle:
        for line in handle:
            if not line.startswith("#"):
                break
            if line.startswith("#!genome-build"):
                declared = line.split(maxsplit=1)[1].strip()
                if not declared.startswith(assembly):
                    raise SystemExit(f"GTF genome build {declared!r} does not match configured assembly {assembly!r}")


def read_rows(path: Path) -> tuple[list[dict[str, str]], list[str]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        reader = csv.DictReader(handle, delimiter="\t")
        return list(reader), reader.fieldnames or []


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--gtf", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--vep-release", required=True, type=int)
    parser.add_argument("--gtf-release", required=True, type=int)
    parser.add_argument("--assembly", required=True)
    args = parser.parse_args()
    if args.vep_release != args.gtf_release:
        raise SystemExit(f"GTF release {args.gtf_release} does not match VEP release {args.vep_release}")
    validate_gtf_assembly(args.gtf, args.assembly)
    rows, fields = read_rows(args.input)
    transcript_ids = {
        normalized_transcript_id(row.get("transcript_id", "")) for row in rows if row.get("transcript_id")
    }
    models = load_models(args.gtf, transcript_ids)
    assignments: list[dict[str, str]] = []
    for row in rows:
        result = classify_transcript(
            consequence=row.get("consequence", ""),
            feature_type=row.get("feature_type", ""),
            chrom=row.get("chrom", ""),
            pos=int(row["pos"]), ref=row.get("ref", ""), alt=row.get("alt", ""),
            model=models.get(normalized_transcript_id(row.get("transcript_id", ""))),
        )
        row.update(result)
        categories = result["category_set"].split(";") if result["category_set"] else [""]
        for category in categories:
            assignments.append({
                **{
                    field: row.get(field, "")
                    for field in ASSIGNMENT_FIELDS
                    if field not in {"category", "category_specification", "gtf_path"}
                },
                "category": category,
                "category_specification": "TSG-SPLICE-CATEGORIES/1.0.0",
                "gtf_path": str(args.gtf),
            })
    atomic_tsv(args.output, rows, [*fields, *CATEGORY_FIELDS], gzip_output=True)
    atomic_tsv(args.assignments, assignments, ASSIGNMENT_FIELDS, gzip_output=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
