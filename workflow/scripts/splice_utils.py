"""Pure functions for canonical splice consequence extraction and collapsing."""

from __future__ import annotations

from collections import defaultdict
from collections.abc import Iterable
from typing import Any

CANONICAL_TERMS = {"splice_donor_variant", "splice_acceptor_variant"}
IMPACT_ORDER = {"HIGH": 0, "MODERATE": 1, "LOW": 2, "MODIFIER": 3, "": 4}


def consequence_terms(value: str | None) -> set[str]:
    """Split VEP ampersand-delimited Sequence Ontology consequences."""
    return {term.strip() for term in (value or "").split("&") if term.strip()}


def canonical_splice_type(value: str | None) -> str | None:
    """Return donor, acceptor, both, or None from a consequence string."""
    terms = consequence_terms(value)
    donor = "splice_donor_variant" in terms
    acceptor = "splice_acceptor_variant" in terms
    if donor and acceptor:
        return "donor_and_acceptor"
    if donor:
        return "donor"
    if acceptor:
        return "acceptor"
    return None


def truthy_flag(value: Any) -> bool:
    """Interpret common VEP flag representations."""
    return str(value or "").strip().upper() in {"YES", "Y", "1", "TRUE"}


def _tsl_rank(value: Any) -> int:
    tokens = str(value or "").split()
    if not tokens:
        return 99
    token = tokens[0].replace("tsl", "")
    try:
        return int(token)
    except ValueError:
        return 99


def _appris_rank(value: Any) -> tuple[int, str]:
    token = str(value or "").lower()
    if token.startswith("principal"):
        suffix = token.replace("principal", "").replace(":", "")
        return (0, suffix)
    if token.startswith("alternative"):
        return (1, token)
    return (2, token)


def transcript_rank(row: dict[str, Any]) -> tuple[Any, ...]:
    """Rank a transcript deterministically according to documented priorities."""
    return (
        not truthy_flag(row.get("mane_plus_clinical")),
        not bool(str(row.get("mane_select") or "").strip()),
        not truthy_flag(row.get("canonical_transcript")),
        str(row.get("transcript_biotype") or "") != "protein_coding",
        _tsl_rank(row.get("transcript_support_level")),
        _appris_rank(row.get("appris")),
        str(row.get("transcript_id") or ""),
    )


def collapse_rows(rows: Iterable[dict[str, Any]]) -> list[dict[str, Any]]:
    """Collapse canonical transcript rows into one record per normalized allele."""
    groups: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        if canonical_splice_type(str(row.get("consequence", ""))):
            groups[str(row["variant_key"])].append(row)
    collapsed: list[dict[str, Any]] = []
    for key in sorted(groups):
        group = groups[key]
        representative = min(group, key=transcript_rank)
        types = sorted({str(row["canonical_splice_type"]) for row in group})
        impacts = sorted({str(row.get("vep_impact", "")) for row in group}, key=lambda x: IMPACT_ORDER.get(x, 99))
        collapsed.append(
            {
                "variant_key": key,
                "chrom": representative["chrom"],
                "pos": representative["pos"],
                "ref": representative["ref"],
                "alt": representative["alt"],
                "sample_id": representative["sample_id"],
                "canonical_splice_candidate": "yes",
                "affected_transcript_count": len({str(r.get("transcript_id", "")) for r in group}),
                "affected_gene_count": len({str(r.get("gene_id", "")) for r in group}),
                "affected_gene_symbols": ",".join(
                    sorted({str(r.get("gene_symbol", "")) for r in group if r.get("gene_symbol")})
                ),
                "affected_transcript_ids": ",".join(
                    sorted({str(r.get("transcript_id", "")) for r in group if r.get("transcript_id")})
                ),
                "canonical_splice_types": ",".join(types),
                "any_mane_select": "yes" if any(str(r.get("mane_select", "")).strip() for r in group) else "no",
                "any_mane_plus_clinical": "yes"
                if any(truthy_flag(r.get("mane_plus_clinical")) for r in group)
                else "no",
                "any_canonical_transcript": "yes"
                if any(truthy_flag(r.get("canonical_transcript")) for r in group)
                else "no",
                "highest_vep_impact": impacts[0] if impacts else "",
                "representative_transcript": representative.get("transcript_id", ""),
                "representative_gene": representative.get("gene_symbol", ""),
                "all_consequence_terms": ",".join(
                    sorted({t for r in group for t in consequence_terms(str(r.get("consequence", "")))})
                ),
                "source_vcf": representative.get("source_vcf", ""),
                "source_manifest": representative.get("source_manifest", ""),
            }
        )
    return collapsed
