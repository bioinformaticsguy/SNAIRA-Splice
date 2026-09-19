from curated_evaluation_utils import evaluate_case, normalized_variant_id


def case(**updates: str) -> dict[str, str]:
    result = {
        "case_id": "case1",
        "expected_gene": "GENE1",
        "expected_category": "deep_intronic",
        "expected_assignment_status": "assigned",
        "expected_vep_term": "intron_variant",
        "expected_spliceai_status": "scored",
        "minimum_nearest_junction_distance": "101",
        "maximum_nearest_junction_distance": "",
    }
    result.update(updates)
    return result


def test_evaluate_case_accepts_expected_category_distance_and_predictor_status() -> None:
    result = evaluate_case(
        case(),
        [
            {
                "symbol": "GENE1",
                "category": "deep_intronic",
                "category_assignment_status": "assigned",
                "nearest_junction_distance": "120",
            }
        ],
        [{"symbol": "GENE1", "consequence": "intron_variant"}],
        [{"gene": "GENE1", "spliceai_status": "scored", "spliceai_max": "0.87"}],
    )
    assert result["evaluation_status"] == "PASS"
    assert result["observed_spliceai_max"] == "0.87"


def test_evaluate_case_reports_multiple_failed_expectations() -> None:
    result = evaluate_case(case(), [], [], [])
    assert result["evaluation_status"] == "FAIL"
    assert "no_assignment_for_gene:GENE1" in result["evaluation_reasons"]
    assert "missing_category:deep_intronic" in result["evaluation_reasons"]
    assert "missing_spliceai_status:scored" in result["evaluation_reasons"]


def test_evaluation_variant_identity_accepts_standard_contig_aliases() -> None:
    assert normalized_variant_id({"normalized_variant_id": "chr8:86605416:C:T"}) == "8:86605416:C:T"
    assert normalized_variant_id({"chrom": "8", "pos": "86605416", "ref": "C", "alt": "T"}) == "8:86605416:C:T"
