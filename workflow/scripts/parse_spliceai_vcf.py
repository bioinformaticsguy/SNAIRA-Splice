#!/usr/bin/env python3
"""Parse local SpliceAI VCF annotations into allele/gene evidence rows."""

from __future__ import annotations

import argparse
import gzip
import logging
from pathlib import Path

from io_utils import atomic_tsv
from spliceai_utils import is_supported_variant, parse_spliceai_info

FIELDS = [
    "sample_id",
    "chrom",
    "pos",
    "ref",
    "alt",
    "normalized_variant_id",
    "allele",
    "gene",
    "ds_ag",
    "ds_al",
    "ds_dg",
    "ds_dl",
    "dp_ag",
    "dp_al",
    "dp_dg",
    "dp_dl",
    "spliceai_max",
    "spliceai_event",
    "spliceai_delta_position",
    "predicted_site_position",
    "predicted_site_ag",
    "predicted_site_al",
    "predicted_site_dg",
    "predicted_site_dl",
    "spliceai_status",
    "spliceai_missing_reason",
]


def _info_value(info: str, key: str) -> str | None:
    for item in info.split(";"):
        if item.startswith(f"{key}="):
            return item.split("=", 1)[1]
    return None


def missing_row(sample_id: str, chrom: str, pos: int, ref: str, alt: str, status: str, reason: str) -> dict[str, str]:
    """Create an explicit unscored evidence row without inventing zero scores."""
    row = {field: "" for field in FIELDS}
    row.update(
        {
            "sample_id": sample_id,
            "chrom": chrom,
            "pos": str(pos),
            "ref": ref,
            "alt": alt,
            "normalized_variant_id": f"{chrom}:{pos}:{ref}:{alt}",
            "allele": alt,
            "spliceai_status": status,
            "spliceai_missing_reason": reason,
        }
    )
    return row


def parse_vcf(path: Path, sample_id: str) -> tuple[list[dict[str, str]], list[str]]:
    """Parse every normalized allele in a SpliceAI-annotated VCF."""
    opener = gzip.open if path.suffix == ".gz" else open
    rows: list[dict[str, str]] = []
    errors: list[str] = []
    with opener(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("#"):
                continue
            columns = line.rstrip("\n").split("\t")
            if len(columns) < 8:
                errors.append("malformed VCF record with fewer than eight columns")
                continue
            chrom, pos_text, _, ref, alt_text, _, _, info = columns[:8]
            pos = int(pos_text)
            predictions, parse_errors = parse_spliceai_info(_info_value(info, "SpliceAI"))
            errors.extend(f"{chrom}:{pos}: {message}" for message in parse_errors)
            for alt in alt_text.split(","):
                matched = [prediction for prediction in predictions if prediction.allele == alt]
                if matched:
                    for prediction in matched:
                        row = prediction.as_row(pos)
                        row.update(
                            {
                                "sample_id": sample_id,
                                "chrom": chrom,
                                "pos": str(pos),
                                "ref": ref,
                                "alt": alt,
                                "normalized_variant_id": f"{chrom}:{pos}:{ref}:{alt}",
                            }
                        )
                        rows.append(row)
                elif not is_supported_variant(ref, alt):
                    rows.append(
                        missing_row(sample_id, chrom, pos, ref, alt, "unsupported_variant", "unsupported_allele_shape")
                    )
                elif parse_errors:
                    rows.append(
                        missing_row(sample_id, chrom, pos, ref, alt, "not_scored", "malformed_spliceai_annotation")
                    )
                else:
                    rows.append(missing_row(sample_id, chrom, pos, ref, alt, "not_scored", "no_prediction_returned"))
    return rows, errors


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-id", required=True)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    rows, errors = parse_vcf(args.input, args.sample_id)
    for error in errors:
        logging.warning(error)
    atomic_tsv(args.output, rows, FIELDS, gzip_output=True)
    logging.info("wrote %d SpliceAI evidence rows", len(rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
