#!/usr/bin/env python3
"""Collapse canonical transcript annotations to normalized alleles."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from io_utils import atomic_tsv
from splice_utils import collapse_rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    with gzip.open(args.input, "rt", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle, delimiter="\t"))
    collapsed = collapse_rows(rows)
    fields = (
        list(collapsed[0])
        if collapsed
        else [
            "variant_key",
            "chrom",
            "pos",
            "ref",
            "alt",
            "sample_id",
            "canonical_splice_candidate",
            "affected_transcript_count",
            "affected_gene_count",
            "affected_gene_symbols",
            "affected_transcript_ids",
            "canonical_splice_types",
            "any_mane_select",
            "any_mane_plus_clinical",
            "any_canonical_transcript",
            "highest_vep_impact",
            "representative_transcript",
            "representative_gene",
            "all_consequence_terms",
            "source_vcf",
            "source_manifest",
        ]
    )
    atomic_tsv(args.output, collapsed, fields, gzip_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
