"""Transcript-aware splice-category utilities for TSG-SPLICE-CATEGORIES/1.1.0."""

from __future__ import annotations

from dataclasses import dataclass

from splice_utils import canonical_splice_type, consequence_terms

NEAR_SPLICE_VEP_TERMS = frozenset({"splice_region_variant", "splice_donor_5th_base_variant"})


@dataclass(frozen=True)
class TranscriptModel:
    """Minimal transcript exon model using 1-based inclusive genomic coordinates."""

    transcript_id: str
    chrom: str
    strand: str
    exons: tuple[tuple[int, int], ...]


def normalized_transcript_id(value: str) -> str:
    """Remove an optional Ensembl transcript version suffix."""
    return value.split(".", 1)[0]


def normalized_contig(value: str) -> str:
    """Normalize only standard GRCh38 ``chr`` aliases for GTF/VCF comparison."""
    contig = value.strip()
    if contig.lower().startswith("chr"):
        contig = contig[3:]
    return "MT" if contig.upper() == "M" else contig


def affected_reference_interval(pos: int, ref: str, alt: str) -> tuple[int, int] | None:
    """Return the non-anchor reference interval, or ``None`` for an insertion junction."""
    prefix = 0
    while prefix < min(len(ref), len(alt)) and ref[prefix] == alt[prefix]:
        prefix += 1
    ref_remainder = ref[prefix:]
    alt_remainder = alt[prefix:]
    suffix = 0
    while (
        suffix < min(len(ref_remainder), len(alt_remainder))
        and ref_remainder[-(suffix + 1)] == alt_remainder[-(suffix + 1)]
    ):
        suffix += 1
    if suffix:
        ref_remainder = ref_remainder[:-suffix]
    if not ref_remainder:
        return None
    start = pos + prefix
    return start, start + len(ref_remainder) - 1


def insertion_left_coordinate(pos: int, ref: str, alt: str) -> int:
    """Return the genomic base immediately left of a normalized insertion junction."""
    prefix = 0
    while prefix < min(len(ref), len(alt)) and ref[prefix] == alt[prefix]:
        prefix += 1
    return pos + prefix - 1


def _intron_context(
    model: TranscriptModel, interval: tuple[int, int] | None, insertion_left: int | None
) -> tuple[int, str] | None:
    """Return nearest junction distance/type when wholly within one transcript intron."""
    for upstream, downstream in zip(model.exons, model.exons[1:], strict=False):
        intron_start, intron_end = upstream[1] + 1, downstream[0] - 1
        if interval is not None:
            start, end = interval
            if not (intron_start <= start <= end <= intron_end):
                continue
            left_distance, right_distance = start - upstream[1], downstream[0] - end
        else:
            assert insertion_left is not None
            if not (intron_start <= insertion_left < intron_end):
                continue
            left_distance, right_distance = insertion_left - upstream[1], downstream[0] - insertion_left
        left_type, right_type = ("donor", "acceptor") if model.strand == "+" else ("acceptor", "donor")
        distance = min(left_distance, right_distance)
        pairs = ((left_type, left_distance), (right_type, right_distance))
        types = sorted(boundary for boundary, value in pairs if value == distance)
        return distance, ";".join(types)
    return None


def _overlaps_exon(model: TranscriptModel, interval: tuple[int, int] | None, insertion_left: int | None) -> bool:
    """Return whether an allele affects retained exonic sequence for this transcript."""
    if interval is not None:
        return any(start <= interval[1] and interval[0] <= end for start, end in model.exons)
    assert insertion_left is not None
    # An insertion is an interbase event.  A junction adjacent to either exon
    # edge touches that retained exon; this also prevents a boundary insertion
    # from being incorrectly called wholly intronic.
    return any(start <= insertion_left <= end for start, end in model.exons)


def classify_transcript(
    *, consequence: str, feature_type: str, chrom: str, pos: int, ref: str, alt: str, model: TranscriptModel | None
) -> dict[str, str]:
    """Classify one normalized allele × transcript under specification v1.1.0."""
    terms = consequence_terms(consequence)
    canonical_type = canonical_splice_type(consequence)
    categories: set[str] = set()
    reasons: list[str] = []
    if canonical_type:
        categories.add("canonical")
        reasons.append(f"vep_canonical_{canonical_type}")
    near_splice_terms = terms & NEAR_SPLICE_VEP_TERMS
    if near_splice_terms and not canonical_type:
        categories.add("near_splice")
        reasons.extend(f"vep_{term}" for term in sorted(near_splice_terms))
    if feature_type != "Transcript":
        return {
            "category_set": ";".join(sorted(categories)),
            "category_assignment_status": "not_applicable",
            "category_assignment_reason": ";".join(reasons + ["non_transcript_feature"]),
            "nearest_junction_distance": "",
            "nearest_junction_type": "",
        }
    if model is None or normalized_contig(model.chrom) != normalized_contig(chrom):
        return {
            "category_set": ";".join(sorted(categories)),
            "category_assignment_status": "annotation_unavailable",
            "category_assignment_reason": ";".join(reasons + ["transcript_not_found_in_gtf"]),
            "nearest_junction_distance": "",
            "nearest_junction_type": "",
        }
    interval = affected_reference_interval(pos, ref, alt)
    insertion_left = insertion_left_coordinate(pos, ref, alt) if interval is None else None
    if _overlaps_exon(model, interval, insertion_left):
        categories.add("exonic_splicing_motif")
        reasons.append("gtf_exon_overlap")
    intron = _intron_context(model, interval, insertion_left)
    distance, junction_type = (intron if intron is not None else (None, ""))
    intronic_only = intron is not None and not _overlaps_exon(model, interval, insertion_left)
    if intronic_only and not canonical_type and not near_splice_terms:
        if distance is not None and distance > 100:
            categories.add("deep_intronic")
            reasons.append("gtf_intronic_distance_gt_100")
        elif distance is not None:
            reason = "proximal_intronic_9_100" if distance >= 9 else "boundary_adjacent_without_vep_near_splice_term"
            reasons.append(reason)
    if categories:
        status = "assigned"
    elif intron is not None and distance is not None:
        status = "outside_v1_categories"
    else:
        status = "outside_v1_categories"
        reasons.append("not_exonic_or_wholly_intronic")
    return {
        "category_set": ";".join(sorted(categories)),
        "category_assignment_status": status,
        "category_assignment_reason": ";".join(dict.fromkeys(reasons)),
        "nearest_junction_distance": "" if distance is None else str(distance),
        "nearest_junction_type": junction_type,
    }
