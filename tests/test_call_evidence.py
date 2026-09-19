import gzip
from pathlib import Path

from extract_call_evidence import parse_vcf


def test_extracts_call_evidence_and_preserves_missing_values(tmp_path: Path) -> None:
    vcf = tmp_path / "calls.vcf.gz"
    with gzip.open(vcf, "wt", encoding="utf-8") as handle:
        handle.write(
            "##fileformat=VCFv4.2\n"
            "#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\tFORMAT\tS1\n"
            "chr1\t10\t.\tA\tG\t99\tPASS\t.\tGT:DP:GQ:AD\t0/1:30:80:14,16\n"
            "chr1\t20\t.\tC\tT\t.\tLowQual\t.\tGT\t1/1\n"
        )
    rows = parse_vcf(vcf, "S1")
    assert rows[0]["normalized_variant_id"] == "chr1:10:A:G"
    assert rows[0]["genotype"] == "0/1"
    assert rows[0]["read_depth"] == "30"
    assert rows[0]["genotype_quality"] == "80"
    assert rows[0]["allele_depth"] == "14,16"
    assert rows[1]["vcf_qual"] == ""
    assert rows[1]["vcf_filter"] == "LowQual"
    assert rows[1]["read_depth"] == ""
