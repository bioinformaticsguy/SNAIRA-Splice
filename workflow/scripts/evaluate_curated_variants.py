#!/usr/bin/env python3
"""Evaluate versioned public curated variants against completed workflow outputs."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from curated_evaluation_utils import evaluate_case, index_rows, normalized_variant_id
from io_utils import atomic_json, atomic_tsv


def read_tsv(path: Path, compressed: bool = False) -> list[dict[str, str]]:
    """Read a tab-separated file, optionally gzip compressed."""
    opener = gzip.open if compressed else open
    with opener(path, "rt", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--catalog", required=True, type=Path)
    parser.add_argument("--assignments", required=True, type=Path)
    parser.add_argument("--transcripts", required=True, type=Path)
    parser.add_argument("--spliceai", required=True, type=Path)
    parser.add_argument("--tsv", required=True, type=Path)
    parser.add_argument("--json", required=True, type=Path)
    args = parser.parse_args()
    catalog = read_tsv(args.catalog)
    assignments = index_rows(read_tsv(args.assignments, compressed=True))
    transcripts = index_rows(read_tsv(args.transcripts, compressed=True))
    spliceai = index_rows(read_tsv(args.spliceai, compressed=True))
    results = []
    for case in catalog:
        key = normalized_variant_id({"normalized_variant_id": case["normalized_variant_id"]})
        results.append(evaluate_case(case, assignments.get(key, []), transcripts.get(key, []), spliceai.get(key, [])))
    fieldnames = list(catalog[0]) + [
        "observed_categories",
        "observed_assignment_statuses",
        "observed_vep_terms",
        "observed_nearest_junction_distances",
        "observed_spliceai_statuses",
        "observed_spliceai_max",
        "evaluation_status",
        "evaluation_reasons",
    ]
    atomic_tsv(args.tsv, results, fieldnames)
    failed = [row for row in results if row["evaluation_status"] != "PASS"]
    atomic_json(
        args.json,
        {
            "catalog": str(args.catalog),
            "cases": len(results),
            "passed": len(results) - len(failed),
            "failed": len(failed),
            "all_passed": not failed,
            "results_tsv": str(args.tsv),
        },
    )
    if failed:
        for row in failed:
            print(f"FAIL {row['case_id']}: {row['evaluation_reasons']}")
        return 1
    print(f"PASS: {len(results)} curated cases")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
