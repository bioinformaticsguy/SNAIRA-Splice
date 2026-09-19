#!/usr/bin/env python3
"""Join VEP and SpliceAI evidence and write candidate/review tables."""

from __future__ import annotations

import argparse
import csv
import gzip
from pathlib import Path

from candidate_utils import CALL_EVIDENCE_FIELDS, SPLICEAI_FIELDS, collapse_variants, join_candidate_rows
from io_utils import atomic_tsv


def read_rows(path: Path) -> list[dict[str, str]]:
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vep", required=True, type=Path)
    parser.add_argument("--spliceai", required=True, type=Path)
    parser.add_argument("--call-evidence", required=True, type=Path)
    parser.add_argument("--candidate-threshold", required=True, type=float)
    parser.add_argument("--review-threshold", required=True, type=float)
    parser.add_argument("--transcripts", required=True, type=Path)
    parser.add_argument("--variants", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    args = parser.parse_args()
    if not 0 <= args.review_threshold <= args.candidate_threshold <= 1:
        raise SystemExit("thresholds must satisfy 0 <= review_threshold <= candidate_threshold <= 1")
    vep_rows, spliceai_rows, call_rows = read_rows(args.vep), read_rows(args.spliceai), read_rows(args.call_evidence)
    transcripts = join_candidate_rows(vep_rows, spliceai_rows, args.candidate_threshold, call_evidence_rows=call_rows)
    review_transcripts = join_candidate_rows(
        vep_rows,
        spliceai_rows,
        args.review_threshold,
        score_reason="spliceai_review_threshold",
        call_evidence_rows=call_rows,
    )
    candidates, review = collapse_variants(
        transcripts, spliceai_rows, args.review_threshold, review_transcript_rows=review_transcripts
    )
    transcript_fields = (
        list(vep_rows[0])
        if vep_rows
        else [
            "sample_id",
            "chrom",
            "pos",
            "ref",
            "alt",
            "normalized_variant_id",
            "symbol",
            "gene_id",
            "transcript_id",
            "feature_type",
            "biotype",
            "strand",
            "exon",
            "intron",
            "hgvsc",
            "hgvsp",
            "mane_select",
            "mane_plus_clinical",
            "canonical",
            "tsl",
            "appris",
            "consequence",
            "impact",
            "existing_variation",
            "annotation_version",
            "source_vcf",
            "source_manifest",
        ]
    )
    transcript_fields += [
        "category_set",
        "category_assignment_status",
        "category_assignment_reason",
        "nearest_junction_distance",
        "nearest_junction_type",
        *CALL_EVIDENCE_FIELDS,
        "splice_category",
        "candidate_reasons",
        *SPLICEAI_FIELDS,
    ]
    variant_fields = (
        list(candidates[0])
        if candidates
        else list(review[0])
        if review
        else [
            "sample_id",
            "chrom",
            "pos",
            "ref",
            "alt",
            "normalized_variant_id",
            *CALL_EVIDENCE_FIELDS,
            "gene_symbols",
            "affected_transcript_count",
            "representative_transcript",
            "representative_gene",
            "any_mane_select",
            "any_mane_plus_clinical",
            "any_canonical_transcript",
            "vep_consequence_union",
            "splice_category_union",
            "category_set_union",
            "primary_category",
            "highest_vep_impact",
            "spliceai_max",
            "spliceai_event",
            "spliceai_delta_position",
            "predicted_site_position",
            "spliceai_effects",
            "spliceai_status",
            "spliceai_missing_reason",
            "candidate_reasons",
            "is_main_candidate",
            "source_vcf",
            "source_manifest",
        ]
    )
    atomic_tsv(args.transcripts, transcripts, transcript_fields, gzip_output=True)
    atomic_tsv(args.variants, candidates, variant_fields, gzip_output=True)
    atomic_tsv(args.review, review, variant_fields, gzip_output=True)


if __name__ == "__main__":
    raise SystemExit(main())
