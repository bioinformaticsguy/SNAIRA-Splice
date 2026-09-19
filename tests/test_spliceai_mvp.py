from pathlib import Path

from candidate_utils import (
    coarse_categories,
    collapse_variants,
    join_candidate_rows,
    retention_reasons,
)
from generate_report import build_report, is_masked_spliceai_mode, summary_metrics
from parse_spliceai_vcf import parse_vcf
from spliceai_utils import SpliceAIPrediction, parse_spliceai_entry, parse_spliceai_info


def prediction(
    maximum: float = 0.8,
    *,
    position: int = 100,
    gene: str = "GENE1",
    event: str = "donor_gain",
    delta: int = 5,
) -> dict[str, str]:
    scores = {"acceptor_gain": 0.01, "acceptor_loss": 0.02, "donor_gain": 0.03, "donor_loss": 0.04}
    positions = {"acceptor_gain": -2, "acceptor_loss": 3, "donor_gain": delta, "donor_loss": -4}
    scores[event] = maximum
    item = SpliceAIPrediction(
        "G",
        gene,
        scores["acceptor_gain"],
        scores["acceptor_loss"],
        scores["donor_gain"],
        scores["donor_loss"],
        positions["acceptor_gain"],
        positions["acceptor_loss"],
        positions["donor_gain"],
        positions["donor_loss"],
    ).as_row(position)
    item.update(
        {
            "sample_id": "S1",
            "chrom": "chr1",
            "pos": str(position),
            "ref": "A",
            "alt": "G",
            "normalized_variant_id": f"chr1:{position}:A:G",
            "gene": gene,
        }
    )
    return item


def vep(
    consequence: str,
    *,
    position: int = 100,
    symbol: str = "GENE1",
    exon: str = "",
    intron: str = "",
) -> dict[str, str]:
    return {
        "sample_id": "S1",
        "chrom": "chr1",
        "pos": str(position),
        "ref": "A",
        "alt": "G",
        "normalized_variant_id": f"chr1:{position}:A:G",
        "symbol": symbol,
        "gene_id": "ENSG1",
        "transcript_id": "ENST1",
        "feature_type": "Transcript",
        "biotype": "protein_coding",
        "strand": "1",
        "exon": exon,
        "intron": intron,
        "hgvsc": "",
        "hgvsp": "",
        "mane_select": "NM_1",
        "mane_plus_clinical": "",
        "canonical": "YES",
        "tsl": "1",
        "appris": "principal1",
        "consequence": consequence,
        "impact": "HIGH",
        "existing_variation": "",
        "annotation_version": "115",
        "source_vcf": "source.vcf.gz",
        "source_manifest": "manifest.json",
    }


def unscored(position: int = 100) -> dict[str, str]:
    row = prediction(0.0, position=position)
    for field in (
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
    ):
        row[field] = ""
    row["spliceai_status"] = "not_scored"
    row["spliceai_missing_reason"] = "no_prediction_returned"
    return row


def test_parse_all_spliceai_fields_and_positive_position() -> None:
    parsed = parse_spliceai_entry("G|GENE1|0.01|0.02|0.90|0.03|-2|3|5|-4")
    row = parsed.as_row(100)
    assert parsed.maximum == 0.9
    assert parsed.events == ("donor_gain",)
    assert row["spliceai_delta_position"] == "5"
    assert row["predicted_site_position"] == "105"
    assert row["ds_ag"] == "0.01" and row["dp_dl"] == "-4"


def test_negative_delta_position() -> None:
    parsed = parse_spliceai_entry("G|GENE1|0.91|0.02|0.03|0.04|-9|3|5|-4")
    assert parsed.as_row(100)["predicted_site_position"] == "91"


def test_exact_tie_preserves_events_positions_and_sites() -> None:
    parsed = parse_spliceai_entry("G|GENE1|0.8|0.8|0.1|0.0|-2|3|5|-4")
    row = parsed.as_row(100)
    assert row["spliceai_event"] == "acceptor_gain;acceptor_loss"
    assert row["spliceai_delta_position"] == "-2;3"
    assert row["predicted_site_position"] == "98;103"


def test_missing_annotation_and_zero_are_distinct(tmp_path: Path) -> None:
    path = tmp_path / "spliceai.vcf"
    path.write_text(
        "##fileformat=VCFv4.2\n#CHROM\tPOS\tID\tREF\tALT\tQUAL\tFILTER\tINFO\n"
        "chr1\t100\t.\tA\tG\t.\t.\tSpliceAI=G|GENE1|0|0|0|0|1|2|3|4\n"
        "chr1\t200\t.\tA\tT\t.\t.\t.\n"
        "chr1\t300\t.\tAT\tGC\t.\t.\t.\n"
    )
    rows, errors = parse_vcf(path, "S1")
    assert not errors
    assert rows[0]["spliceai_status"] == "scored" and rows[0]["spliceai_max"] == "0"
    assert rows[1]["spliceai_status"] == "not_scored" and rows[1]["spliceai_max"] == ""
    assert rows[2]["spliceai_status"] == "unsupported_variant"


def test_malformed_annotation_is_reported() -> None:
    parsed, errors = parse_spliceai_info("G|GENE1|bad")
    assert not parsed and errors


def test_coarse_categories_are_conservative() -> None:
    assert coarse_categories("splice_donor_variant&intron_variant") == ("canonical_donor",)
    assert coarse_categories("splice_region_variant&missense_variant", exon="1/2") == ("splice_region",)
    assert coarse_categories("intron_variant", intron="1/2") == ("intronic_noncanonical",)
    assert coarse_categories("synonymous_variant", exon="2/3") == ("exonic_noncanonical",)


def test_canonical_low_or_absent_spliceai_is_retained() -> None:
    rows = join_candidate_rows([vep("splice_donor_variant")], [unscored()], 0.20)
    assert len(rows) == 1
    assert "vep_canonical_donor" in rows[0]["candidate_reasons"]
    assert rows[0]["spliceai_status"] == "not_scored"


def test_intronic_and_synonymous_high_scores_are_retained() -> None:
    intronic = join_candidate_rows([vep("intron_variant", intron="1/2")], [prediction(0.7)], 0.20)
    exonic = join_candidate_rows([vep("synonymous_variant", exon="2/3")], [prediction(0.6)], 0.20)
    assert intronic[0]["splice_category"] == "intronic_noncanonical"
    assert exonic[0]["splice_category"] == "exonic_noncanonical"


def test_candidate_and_review_thresholds() -> None:
    assert retention_reasons([], [prediction(0.20)], 0.20) == ("spliceai_candidate_threshold",)
    assert retention_reasons([], [prediction(0.19)], 0.20) == ()
    review_rows = join_candidate_rows([vep("intron_variant", intron="1/2")], [prediction(0.05)], 0.05)
    assert review_rows


def test_transcript_to_variant_collapse_preserves_strongest_effect() -> None:
    transcripts = join_candidate_rows(
        [vep("intron_variant", intron="1/2"), vep("missense_variant", exon="2/3")],
        [prediction(0.8, event="donor_gain", delta=-7)],
        0.20,
    )
    variants, review = collapse_variants(transcripts, [prediction(0.8, event="donor_gain", delta=-7)], 0.05)
    assert len(variants) == len(review) == 1
    assert variants[0]["spliceai_max"] == "0.8"
    assert variants[0]["spliceai_event"] == "donor_gain"
    assert variants[0]["spliceai_delta_position"] == "-7"
    assert variants[0]["predicted_site_position"] == "93"
    assert "intronic_noncanonical" in variants[0]["splice_category_union"]


def test_html_generation_contains_controls_evidence_and_disclaimer() -> None:
    sai = prediction(0.8)
    transcripts = join_candidate_rows([vep("splice_acceptor_variant")], [sai], 0.20)
    variants, review = collapse_variants(transcripts, [sai], 0.05)
    metadata = {
        "sample_id": "S1",
        "assembly": "GRCh38",
        "pipeline_version": "test",
        "run_date": "now",
        "vep_version": "115",
        "spliceai_mode": "local_unmasked",
        "spliceai_max_distance": 4999,
    }
    report = build_report(variants, review, transcripts, [sai], metadata, 0.20, 0.05)
    assert "Computational splice predictions are research evidence" in report
    assert "Search all fields" in report
    assert "Filter VEP consequence" in report
    assert "DS AG / AL / DG / DL" in report
    assert "splice_acceptor_variant" in report
    assert "Provenance" in report


def test_spliceai_masking_mode_does_not_misclassify_unmasked() -> None:
    assert is_masked_spliceai_mode("local_masked")
    assert not is_masked_spliceai_mode("local_unmasked")


def test_summary_metrics_counts_missing_and_thresholds() -> None:
    sai = prediction(0.8)
    missing = unscored(200)
    transcripts = join_candidate_rows([vep("splice_donor_variant")], [sai], 0.20)
    variants, _ = collapse_variants(transcripts, [sai, missing], 0.05)
    metrics = summary_metrics(variants, [sai, missing], 0.20, 0.05)
    assert metrics["total_normalized_variants"] == 2
    assert metrics["spliceai_ge_0_80"] == 1
    assert metrics["spliceai_not_scored_variants"] == 1
