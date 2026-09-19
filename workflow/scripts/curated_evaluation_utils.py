"""Pure helpers for comparing a curated catalog against SNAIRA-Splice output."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable

from category_utils import normalized_contig
from splice_utils import consequence_terms


def normalized_variant_id(row: dict[str, str]) -> str:
    """Return a contig-alias-stable normalized allele identity for comparison."""
    chrom = row.get("chrom", "")
    if not chrom:
        value = row.get("normalized_variant_id", "")
        fields = value.split(":", maxsplit=3)
        if len(fields) == 4:
            chrom, position, ref, alt = fields
            return f"{normalized_contig(chrom)}:{position}:{ref}:{alt}"
        return value
    return f"{normalized_contig(chrom)}:{row.get('pos', '')}:{row.get('ref', '')}:{row.get('alt', '')}"


def index_rows(rows: Iterable[dict[str, str]]) -> dict[str, list[dict[str, str]]]:
    """Index annotation rows by contig-alias-stable allele identity."""
    indexed: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in rows:
        indexed[normalized_variant_id(row)].append(row)
    return indexed


def _categories(rows: Iterable[dict[str, str]]) -> set[str]:
    return {row.get("category", "") for row in rows if row.get("category", "")}


def _consequences(rows: Iterable[dict[str, str]]) -> set[str]:
    return {term for row in rows for term in consequence_terms(row.get("consequence", ""))}


def _numeric_distances(rows: Iterable[dict[str, str]]) -> list[int]:
    return [int(row["nearest_junction_distance"]) for row in rows if row.get("nearest_junction_distance", "")]


def evaluate_case(
    case: dict[str, str],
    assignment_rows: list[dict[str, str]],
    transcript_rows: list[dict[str, str]],
    spliceai_rows: list[dict[str, str]],
) -> dict[str, str]:
    """Evaluate one catalog case and retain observations plus every failure reason."""
    reasons: list[str] = []
    expected_gene = case["expected_gene"]
    matching_assignments = [row for row in assignment_rows if row.get("symbol") == expected_gene]
    matching_transcripts = [row for row in transcript_rows if row.get("symbol") == expected_gene]
    matching_spliceai = [row for row in spliceai_rows if row.get("gene") == expected_gene]
    if not matching_assignments:
        reasons.append(f"no_assignment_for_gene:{expected_gene}")
    if case["expected_category"] and case["expected_category"] not in _categories(matching_assignments):
        reasons.append(f"missing_category:{case['expected_category']}")
    if case["expected_assignment_status"] and not any(
        row.get("category_assignment_status") == case["expected_assignment_status"] for row in matching_assignments
    ):
        reasons.append(f"missing_assignment_status:{case['expected_assignment_status']}")
    if case["expected_vep_term"] and case["expected_vep_term"] not in _consequences(matching_transcripts):
        reasons.append(f"missing_vep_term:{case['expected_vep_term']}")
    expected_spliceai_status = case["expected_spliceai_status"]
    if expected_spliceai_status and not any(
        row.get("spliceai_status") == expected_spliceai_status for row in matching_spliceai
    ):
        reasons.append(f"missing_spliceai_status:{expected_spliceai_status}")
    distances = _numeric_distances(matching_assignments)
    minimum = case.get("minimum_nearest_junction_distance", "")
    maximum = case.get("maximum_nearest_junction_distance", "")
    if minimum and not any(value >= int(minimum) for value in distances):
        reasons.append(f"nearest_distance_below_minimum:{minimum}")
    if maximum and not any(value <= int(maximum) for value in distances):
        reasons.append(f"nearest_distance_above_maximum:{maximum}")
    scores = [float(row["spliceai_max"]) for row in matching_spliceai if row.get("spliceai_max", "")]
    return {
        **case,
        "observed_categories": ";".join(sorted(_categories(matching_assignments))),
        "observed_assignment_statuses": ";".join(
            sorted(
                {
                    row.get("category_assignment_status", "")
                    for row in matching_assignments
                    if row.get("category_assignment_status", "")
                }
            )
        ),
        "observed_vep_terms": ";".join(sorted(_consequences(matching_transcripts))),
        "observed_nearest_junction_distances": ";".join(str(value) for value in sorted(set(distances))),
        "observed_spliceai_statuses": ";".join(
            sorted({row.get("spliceai_status", "") for row in matching_spliceai if row.get("spliceai_status", "")})
        ),
        "observed_spliceai_max": "" if not scores else f"{max(scores):g}",
        "evaluation_status": "PASS" if not reasons else "FAIL",
        "evaluation_reasons": ";".join(reasons),
    }
