#!/usr/bin/env python3
"""Extract per-allele call evidence from a normalized single-sample VCF."""

from __future__ import annotations

import argparse
import gzip
from pathlib import Path

from io_utils import atomic_tsv

CALL_EVIDENCE_FIELDS = ["vcf_qual", "vcf_filter", "genotype", "read_depth", "genotype_quality", "allele_depth"]
FIELDS = ["sample_id", "chrom", "pos", "ref", "alt", "normalized_variant_id", *CALL_EVIDENCE_FIELDS]


def _value(format_keys: list[str], sample_values: list[str], name: str) -> str:
    """Return a FORMAT value, keeping absent and VCF-missing values blank."""
    try:
        value = sample_values[format_keys.index(name)]
    except ValueError:
        return ""
    return "" if value in {"", "."} else value


def parse_vcf(path: Path, sample_id: str) -> list[dict[str, str]]:
    """Read normalized VCF call fields for ``sample_id`` without changing the VCF."""
    rows: list[dict[str, str]] = []
    sample_column: int | None = None
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("##"):
                continue
            if line.startswith("#CHROM"):
                header = line.rstrip("\n").split("\t")
                try:
                    sample_column = header.index(sample_id)
                except ValueError as exc:
                    raise ValueError(f"sample {sample_id!r} is not present in normalized VCF {path}") from exc
                continue
            if line.startswith("#"):
                continue
            if sample_column is None:
                raise ValueError(f"normalized VCF {path} has no #CHROM header")
            fields = line.rstrip("\n").split("\t")
            if len(fields) <= sample_column:
                raise ValueError(f"malformed VCF row in {path}: missing sample column for {sample_id!r}")
            chrom, pos, _identifier, ref, alts, qual, filter_value, _info, format_value = fields[:9]
            format_keys = format_value.split(":") if format_value not in {"", "."} else []
            sample_values = fields[sample_column].split(":")
            call = {
                "vcf_qual": "" if qual == "." else qual,
                "vcf_filter": "" if filter_value == "." else filter_value,
                "genotype": _value(format_keys, sample_values, "GT"),
                "read_depth": _value(format_keys, sample_values, "DP"),
                "genotype_quality": _value(format_keys, sample_values, "GQ"),
                "allele_depth": _value(format_keys, sample_values, "AD"),
            }
            for alt in alts.split(","):
                rows.append(
                    {
                        "sample_id": sample_id,
                        "chrom": chrom,
                        "pos": pos,
                        "ref": ref,
                        "alt": alt,
                        "normalized_variant_id": f"{chrom}:{pos}:{ref}:{alt}",
                        **call,
                    }
                )
    return rows


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-id", required=True)
    args = parser.parse_args()
    atomic_tsv(args.output, parse_vcf(args.input, args.sample_id), FIELDS, gzip_output=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
