"""Tests for exact Ensembl GTF genome-build header handling."""

from __future__ import annotations

import gzip
from pathlib import Path

import pytest
from annotate_splice_categories import validate_gtf_assembly


def write_gtf(path: Path, build: str) -> None:
    """Write the relevant minimal Ensembl-style GTF header."""
    with gzip.open(path, "wt", encoding="utf-8") as handle:
        handle.write(f"#!genome-build {build}\n")
        handle.write("#!genome-build-accession NCBI:GCA_000001405.29\n")
        handle.write("1\tensembl\texon\t1\t2\t.\t+\t.\tgene_id \"ENSG1\";\n")


def test_grch38_build_header_is_not_confused_with_assembly_accession(tmp_path: Path) -> None:
    gtf = tmp_path / "Homo_sapiens.GRCh38.115.gtf.gz"
    write_gtf(gtf, "GRCh38.p14")
    validate_gtf_assembly(gtf, "GRCh38")


def test_mismatched_gtf_build_is_rejected(tmp_path: Path) -> None:
    gtf = tmp_path / "Homo_sapiens.GRCh37.115.gtf.gz"
    write_gtf(gtf, "GRCh37.p13")
    with pytest.raises(SystemExit, match="does not match"):
        validate_gtf_assembly(gtf, "GRCh38")
