#!/usr/bin/env python3
"""Create per-sample or cohort splice summary files."""

from __future__ import annotations

import argparse
import csv
import gzip
import html
from pathlib import Path

from io_utils import atomic_json, atomic_tsv


def read_tsv(path: Path) -> list[dict[str, str]]:
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--variants", nargs="+", required=True, type=Path)
    parser.add_argument("--transcripts", nargs="+", required=True, type=Path)
    parser.add_argument("--regions", nargs="+", required=True, type=Path)
    parser.add_argument("--label", required=True)
    parser.add_argument("--tsv", required=True, type=Path)
    parser.add_argument("--json", required=True, type=Path)
    parser.add_argument("--html", required=True, type=Path)
    parser.add_argument("--cohort-table", type=Path)
    args = parser.parse_args()
    variants = [row for path in args.variants for row in read_tsv(path)]
    transcripts = [row for path in args.transcripts for row in read_tsv(path)]
    regions = [row for path in args.regions for row in read_tsv(path)]
    by_key: dict[str, set[str]] = {}
    for row in transcripts:
        by_key.setdefault(row["variant_key"], set()).add(row["canonical_splice_type"])
    metrics = {
        "canonical_variants": len(variants),
        "canonical_donor_variants": sum("donor" in types or "donor_and_acceptor" in types for types in by_key.values()),
        "canonical_acceptor_variants": sum(
            "acceptor" in types or "donor_and_acceptor" in types for types in by_key.values()
        ),
        "variants_with_both_types": sum(
            ("donor" in types and "acceptor" in types) or "donor_and_acceptor" in types for types in by_key.values()
        ),
        "noncanonical_splice_region_variants": len({r["variant_key"] for r in regions}),
        "canonical_only_non_principal_transcripts": sum(
            v.get("any_mane_select") == "no" and v.get("any_canonical_transcript") == "no" for v in variants
        ),
        "canonical_transcript_rows": len(transcripts),
    }
    summary = {"scope": args.label, "metrics": metrics}
    atomic_json(args.json, summary)
    atomic_tsv(args.tsv, [{"metric": key, "value": value} for key, value in metrics.items()], ["metric", "value"])
    args.html.parent.mkdir(parents=True, exist_ok=True)
    rows = "".join(f"<tr><th>{html.escape(k)}</th><td>{v}</td></tr>" for k, v in metrics.items())
    args.html.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'><title>Splice summary</title>"
        "<style>body{font-family:sans-serif;max-width:900px;margin:2rem auto}"
        "th{text-align:left}td,th{padding:.4rem;border-bottom:1px solid #ddd}</style>"
        f"</head><body><h1>{html.escape(args.label)} splice summary</h1><table>{rows}</table></body></html>\n",
        encoding="utf-8",
    )
    if args.cohort_table:
        fields = list(variants[0]) if variants else ["variant_key", "sample_id"]
        atomic_tsv(args.cohort_table, variants, fields, gzip_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
