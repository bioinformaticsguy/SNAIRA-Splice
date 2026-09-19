"""Join VEP transcripts with SpliceAI evidence and collapse candidate alleles."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

from splice_utils import IMPACT_ORDER, canonical_splice_type, consequence_terms, transcript_rank, truthy_flag
from spliceai_utils import strongest_rows

SPLICEAI_FIELDS = [
    "spliceai_gene",
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
CALL_EVIDENCE_FIELDS = ["vcf_qual", "vcf_filter", "genotype", "read_depth", "genotype_quality", "allele_depth"]


def coarse_categories(consequence: str, exon: str = "", intron: str = "") -> tuple[str, ...]:
    """Return conservative MVP categories for one VEP transcript consequence."""
    terms = consequence_terms(consequence)
    categories: list[str] = []
    if "splice_donor_variant" in terms:
        categories.append("canonical_donor")
    if "splice_acceptor_variant" in terms:
        categories.append("canonical_acceptor")
    if not categories and "splice_region_variant" in terms:
        categories.append("splice_region")
    if not categories:
        if intron or "intron_variant" in terms:
            categories.append("intronic_noncanonical")
        elif exon:
            categories.append("exonic_noncanonical")
        else:
            categories.append("other")
    return tuple(categories)


def presentation_categories(row: dict[str, str]) -> tuple[str, ...]:
    """Return display categories while retaining the v1.0 category set on the row."""
    assigned = {value for value in row.get("category_set", "").split(";") if value}
    if not assigned:
        return coarse_categories(row.get("consequence", ""), row.get("exon", ""), row.get("intron", ""))
    if "canonical" in assigned:
        assigned.remove("canonical")
        subtype = canonical_splice_type(row.get("consequence", ""))
        if subtype:
            assigned.add(f"canonical_{subtype}")
    return tuple(sorted(assigned))


def variant_vep_flags(rows: Iterable[dict[str, str]]) -> tuple[bool, bool, bool]:
    """Return donor, acceptor, and splice-region presence across transcripts."""
    all_terms = [consequence_terms(row.get("consequence", "")) for row in rows]
    return (
        any("splice_donor_variant" in terms for terms in all_terms),
        any("splice_acceptor_variant" in terms for terms in all_terms),
        any("splice_region_variant" in terms for terms in all_terms),
    )


def retention_reasons(
    vep_rows: Iterable[dict[str, str]],
    spliceai_rows: Iterable[dict[str, str]],
    candidate_threshold: float,
    score_reason: str = "spliceai_candidate_threshold",
) -> tuple[str, ...]:
    """Return every reason an allele belongs in the main candidate set."""
    donor, acceptor, region = variant_vep_flags(vep_rows)
    reasons = []
    if donor:
        reasons.append("vep_canonical_donor")
    if acceptor:
        reasons.append("vep_canonical_acceptor")
    if region:
        reasons.append("vep_splice_region")
    if any(
        row.get("spliceai_status") == "scored"
        and row.get("spliceai_max") not in {"", None}
        and float(row["spliceai_max"]) >= candidate_threshold
        for row in spliceai_rows
    ):
        reasons.append(score_reason)
    return tuple(reasons)


def _rankable(row: dict[str, str]) -> dict[str, Any]:
    return {
        "mane_plus_clinical": row.get("mane_plus_clinical", ""),
        "mane_select": row.get("mane_select", ""),
        "canonical_transcript": row.get("canonical", ""),
        "transcript_biotype": row.get("biotype", ""),
        "transcript_support_level": row.get("tsl", ""),
        "appris": row.get("appris", ""),
        "transcript_id": row.get("transcript_id", ""),
    }


def _best_spliceai(rows: list[dict[str, str]]) -> tuple[str, str, str, str, str]:
    strongest = strongest_rows(rows)
    if not strongest:
        return "", "", "", "", ""
    maximum = strongest[0]["spliceai_max"]
    events: set[str] = set()
    deltas: set[str] = set()
    sites: set[str] = set()
    effects: set[str] = set()
    for row in strongest:
        row_events = row.get("spliceai_event", "").split(";")
        row_deltas = row.get("spliceai_delta_position", "").split(";")
        row_sites = row.get("predicted_site_position", "").split(";")
        for event, delta, site in zip(row_events, row_deltas, row_sites, strict=False):
            if event:
                events.add(event)
                deltas.add(delta)
                sites.add(site)
                effects.add(f"{row.get('gene', '')}:{event}:{maximum}:{delta}:{site}")
    return (
        maximum,
        ";".join(sorted(events)),
        ";".join(sorted(deltas)),
        ";".join(sorted(sites)),
        ";".join(sorted(effects)),
    )


def _primary_category(rows: list[dict[str, str]]) -> str:
    """Return the documented display-only category precedence without erasing overlaps."""
    categories = {category for row in rows for category in row.get("category_set", "").split(";") if category}
    for category in ("canonical", "near_splice", "exonic_splicing_motif", "deep_intronic"):
        if category in categories:
            return category
    return ""


def join_candidate_rows(
    vep_rows: list[dict[str, str]],
    spliceai_rows: list[dict[str, str]],
    candidate_threshold: float,
    score_reason: str = "spliceai_candidate_threshold",
    call_evidence_rows: list[dict[str, str]] | None = None,
) -> list[dict[str, str]]:
    """Create transcript evidence rows for alleles passing the candidate OR logic."""
    vep_by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    sai_by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    calls_by_variant = {
        row["normalized_variant_id"]: row for row in (call_evidence_rows or []) if row.get("normalized_variant_id")
    }
    for row in vep_rows:
        vep_by_variant[row["normalized_variant_id"]].append(row)
    for row in spliceai_rows:
        sai_by_variant[row["normalized_variant_id"]].append(row)
    output: list[dict[str, str]] = []
    for variant_id in sorted(set(vep_by_variant) | set(sai_by_variant)):
        variant_vep = vep_by_variant[variant_id]
        variant_sai = sai_by_variant[variant_id]
        reasons = retention_reasons(variant_vep, variant_sai, candidate_threshold, score_reason)
        if not reasons:
            continue
        used_sai: set[int] = set()
        for vep in variant_vep:
            matches = [
                (index, sai)
                for index, sai in enumerate(variant_sai)
                if sai.get("spliceai_status") != "scored" or sai.get("gene") == vep.get("symbol")
            ]
            if not matches:
                matches = [(None, None)]
            for index, sai in matches:
                row = dict(vep)
                call = calls_by_variant.get(variant_id, {})
                row.update({field: call.get(field, "") for field in CALL_EVIDENCE_FIELDS})
                row["splice_category"] = ";".join(presentation_categories(row))
                row["candidate_reasons"] = ";".join(reasons)
                for field in SPLICEAI_FIELDS:
                    row[field] = ""
                if sai is None:
                    row["spliceai_status"] = "not_scored"
                    row["spliceai_missing_reason"] = "no_gene_matched_prediction"
                else:
                    if index is not None:
                        used_sai.add(index)
                    for field in SPLICEAI_FIELDS:
                        source_field = "gene" if field == "spliceai_gene" else field
                        row[field] = sai.get(source_field, "")
                output.append(row)
        # Preserve high predictor evidence that has no corresponding VEP transcript/gene row.
        for index, sai in enumerate(variant_sai):
            if index in used_sai or sai.get("spliceai_status") != "scored":
                continue
            if float(sai.get("spliceai_max") or 0) < candidate_threshold:
                continue
            row = {key: "" for key in (vep_rows[0].keys() if vep_rows else [])}
            for identity in ("sample_id", "chrom", "pos", "ref", "alt", "normalized_variant_id"):
                row[identity] = sai.get(identity, "")
            row.update(
                {"symbol": sai.get("gene", ""), "splice_category": "other", "candidate_reasons": ";".join(reasons)}
            )
            row.update({field: calls_by_variant.get(variant_id, {}).get(field, "") for field in CALL_EVIDENCE_FIELDS})
            for field in SPLICEAI_FIELDS:
                source_field = "gene" if field == "spliceai_gene" else field
                row[field] = sai.get(source_field, "")
            output.append(row)
    return output


def collapse_variants(
    transcript_rows: list[dict[str, str]],
    all_spliceai_rows: list[dict[str, str]],
    review_threshold: float,
    review_transcript_rows: list[dict[str, str]] | None = None,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Collapse candidate transcripts and create the broader SpliceAI review set."""
    by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    sai_by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    review_by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in transcript_rows:
        by_variant[row["normalized_variant_id"]].append(row)
    for row in all_spliceai_rows:
        sai_by_variant[row["normalized_variant_id"]].append(row)
    for row in review_transcript_rows or transcript_rows:
        review_by_variant[row["normalized_variant_id"]].append(row)

    def build(variant_id: str, rows: list[dict[str, str]], candidate: bool) -> dict[str, str]:
        sai_rows = sai_by_variant.get(variant_id, [])
        scored = [row for row in sai_rows if row.get("spliceai_status") == "scored"]
        representative = min(rows, key=lambda row: transcript_rank(_rankable(row))) if rows else {}
        identity = rows[0] if rows else sai_rows[0]
        maximum, events, deltas, sites, effects = _best_spliceai(sai_rows)
        impacts = sorted({row.get("impact", "") for row in rows}, key=lambda value: IMPACT_ORDER.get(value, 99))
        return {
            "sample_id": identity.get("sample_id", ""),
            "chrom": identity.get("chrom", ""),
            "pos": identity.get("pos", ""),
            "ref": identity.get("ref", ""),
            "alt": identity.get("alt", ""),
            "normalized_variant_id": variant_id,
            **{field: identity.get(field, "") for field in CALL_EVIDENCE_FIELDS},
            "gene_symbols": ";".join(
                sorted(
                    {row.get("symbol", "") for row in rows if row.get("symbol")}
                    | {row.get("gene", "") for row in scored if row.get("gene")}
                )
            ),
            "affected_transcript_count": str(
                len({row.get("transcript_id", "") for row in rows if row.get("transcript_id")})
            ),
            "representative_transcript": representative.get("transcript_id", ""),
            "representative_gene": representative.get("symbol", ""),
            "any_mane_select": "yes" if any(row.get("mane_select") for row in rows) else "no",
            "any_mane_plus_clinical": "yes"
            if any(truthy_flag(row.get("mane_plus_clinical")) for row in rows)
            else "no",
            "any_canonical_transcript": "yes" if any(truthy_flag(row.get("canonical")) for row in rows) else "no",
            "vep_consequence_union": ";".join(
                sorted({term for row in rows for term in consequence_terms(row.get("consequence", ""))})
            ),
            "splice_category_union": ";".join(
                sorted({category for row in rows for category in row.get("splice_category", "").split(";") if category})
            ),
            "category_set_union": ";".join(
                sorted({category for row in rows for category in row.get("category_set", "").split(";") if category})
            ),
            "primary_category": _primary_category(rows),
            "highest_vep_impact": impacts[0] if impacts else "",
            "spliceai_max": maximum,
            "spliceai_event": events,
            "spliceai_delta_position": deltas,
            "predicted_site_position": sites,
            "spliceai_effects": effects,
            "spliceai_status": "scored"
            if scored
            else (sai_rows[0].get("spliceai_status", "not_scored") if sai_rows else "not_scored"),
            "spliceai_missing_reason": ""
            if scored
            else (
                sai_rows[0].get("spliceai_missing_reason", "no_prediction_returned")
                if sai_rows
                else "no_prediction_returned"
            ),
            "candidate_reasons": ";".join(
                sorted({reason for row in rows for reason in row.get("candidate_reasons", "").split(";") if reason})
            ),
            "is_main_candidate": "yes" if candidate else "no",
            "source_vcf": representative.get("source_vcf", ""),
            "source_manifest": representative.get("source_manifest", ""),
        }

    candidates = [build(key, rows, True) for key, rows in sorted(by_variant.items())]
    review: list[dict[str, str]] = []
    for key, sai_rows in sorted(sai_by_variant.items()):
        if any(
            row.get("spliceai_status") == "scored" and float(row.get("spliceai_max") or 0) >= review_threshold
            for row in sai_rows
        ):
            rows = review_by_variant.get(key, [])
            review.append(build(key, rows, key in by_variant))
    return candidates, review
