#!/usr/bin/env python3
"""Resolve manifests into the workflow sample table."""

from __future__ import annotations

import argparse
import logging
from pathlib import Path

from io_utils import atomic_json, atomic_tsv
from manifest_utils import load_samples, samples_as_dicts


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", required=True, type=Path)
    parser.add_argument("--vcf-key", default="outputs.snv_pass_vcf")
    parser.add_argument("--index-key", default="outputs.snv_pass_vcf_index")
    parser.add_argument("--table", required=True, type=Path)
    parser.add_argument("--report", required=True, type=Path)
    parser.add_argument("--allow-missing", action="store_true")
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    samples, report = load_samples(args.source, args.vcf_key, args.index_key, not args.allow_missing)
    atomic_json(args.report, report)
    if not report["valid"]:
        raise SystemExit("manifest validation failed:\n- " + "\n- ".join(report["errors"]))
    rows = samples_as_dicts(samples)
    fields = list(rows[0]) if rows else []
    atomic_tsv(args.table, rows, fields)
    logging.info("resolved %d sample(s)", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
