"""Regression checks for the committed public curated-variant panel."""

from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CATALOG = ROOT / "tests" / "curated" / "curated_splice_variants.tsv"
VCF = ROOT / "tests" / "curated" / "curated_splice_variants.grch38.vcf"


def read_vcf_cases() -> dict[str, str]:
    """Return panel case identifiers mapped to their genomic allele IDs."""
    cases: dict[str, str] = {}
    for line in VCF.read_text(encoding="utf-8").splitlines():
        if not line or line.startswith("#"):
            continue
        chrom, position, _identifier, ref, alt, _qual, _filter, info, *_rest = line.split("\t")
        case_id = next(
            field.removeprefix("CURATED_CASE=")
            for field in info.split(";")
            if field.startswith("CURATED_CASE=")
        )
        cases[case_id] = f"{chrom}:{position}:{ref}:{alt}"
    return cases


def read_catalog_cases() -> dict[str, str]:
    """Return catalog case identifiers mapped to their normalized genomic IDs."""
    with CATALOG.open(encoding="utf-8", newline="") as handle:
        return {
            row["case_id"]: row["normalized_variant_id"]
            for row in csv.DictReader(handle, delimiter="\t")
        }


def test_curated_vcf_and_catalog_have_matching_case_alleles() -> None:
    assert read_vcf_cases() == read_catalog_cases()


def test_curated_vcf_uses_verified_forward_reference_alleles() -> None:
    assert read_vcf_cases() == {
        "exonic_motif_pkhd1": "chr6:51903693:G:A",
        "near_splice_klhl7": "chr7:23144030:G:C",
        "deep_intronic_cngb3": "chr8:86605416:C:T",
        "proximal_intronic_hbb": "chr11:5226820:C:T",
        "canonical_donor_brca1": "chr17:43115724:A:T",
    }
