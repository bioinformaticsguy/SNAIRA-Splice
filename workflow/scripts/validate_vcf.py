#!/usr/bin/env python3
"""Validate an input VCF without modifying it."""

from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

from io_utils import atomic_json


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcf", required=True, type=Path)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--reference-fai", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    args = parser.parse_args()
    errors: list[str] = []
    warnings: list[str] = []
    if not args.vcf.is_file():
        errors.append(f"VCF is not readable: {args.vcf}")
    if str(args.vcf).endswith(".gz"):
        with args.vcf.open("rb") as handle:
            magic = handle.read(18)
        if len(magic) < 18 or magic[:2] != b"\x1f\x8b" or not (magic[3] & 4) or magic[12:14] != b"BC":
            errors.append("compressed input is not BGZF")
    samples: list[str] = []
    contigs: list[str] = []
    if not errors:
        proc = subprocess.run(["bcftools", "view", "-h", str(args.vcf)], text=True, capture_output=True, check=False)
        if proc.returncode:
            errors.append(f"bcftools could not read VCF: {proc.stderr.strip()}")
        else:
            columns = next((line for line in proc.stdout.splitlines() if line.startswith("#CHROM")), "")
            parts = columns.split("\t")
            if len(parts) < 8:
                errors.append("VCF lacks required #CHROM through INFO columns")
            samples = parts[9:]
            if samples and args.sample_id not in samples:
                warnings.append(f"manifest sample_id {args.sample_id!r} is not a VCF sample name: {samples}")
            contigs = [
                line.split("ID=", 1)[1].split(",", 1)[0].rstrip(">")
                for line in proc.stdout.splitlines()
                if line.startswith("##contig=<ID=")
            ]
    ref_contigs = []
    if args.reference_fai.is_file():
        ref_contigs = [line.split("\t", 1)[0] for line in args.reference_fai.read_text().splitlines() if line]
        if contigs and not set(contigs).intersection(ref_contigs):
            errors.append("VCF and reference have no contig names in common")
        vcf_chr = any(c.startswith("chr") for c in contigs)
        ref_chr = any(c.startswith("chr") for c in ref_contigs)
        if contigs and vcf_chr != ref_chr:
            errors.append("VCF/reference contig naming mismatch (chr-prefixed versus unprefixed)")
    else:
        errors.append(f"reference FASTA index is missing: {args.reference_fai}")
    report = {
        "valid": not errors,
        "vcf": str(args.vcf),
        "sample_id": args.sample_id,
        "vcf_samples": samples,
        "sample_count": len(samples),
        "multi_sample": len(samples) > 1,
        "contig_count": len(contigs),
        "reference_contig_count": len(ref_contigs),
        "errors": errors,
        "warnings": warnings,
    }
    atomic_json(args.output, report)
    print(json.dumps(report, indent=2))
    return 0 if not errors else 1


if __name__ == "__main__":
    raise SystemExit(main())
