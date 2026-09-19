from category_utils import TranscriptModel, affected_reference_interval, classify_transcript, normalized_contig

MODEL = TranscriptModel("ENST1", "chr1", "+", ((100, 199), (500, 599)))
REVERSE_MODEL = TranscriptModel("ENST2", "chr1", "-", ((100, 199), (500, 599)))


def classify(position: int, consequence: str, model: TranscriptModel = MODEL) -> dict[str, str]:
    return classify_transcript(
        consequence=consequence,
        feature_type="Transcript",
        chrom="chr1",
        pos=position,
        ref="A",
        alt="G",
        model=model,
    )


def test_canonical_and_near_splice_follow_vep_terms() -> None:
    canonical = classify(200, "splice_donor_variant,intron_variant")
    near = classify(200, "splice_region_variant,intron_variant")
    assert canonical["category_set"] == "canonical"
    assert near["category_set"] == "near_splice"


def test_exonic_motif_can_overlap_near_splice() -> None:
    result = classify(199, "splice_region_variant,missense_variant")
    assert result["category_set"] == "exonic_splicing_motif;near_splice"
    assert result["category_assignment_status"] == "assigned"


def test_deep_intronic_and_proximal_gap_are_distinguished() -> None:
    deep = classify(350, "intron_variant")
    proximal = classify(250, "intron_variant")
    assert deep["category_set"] == "deep_intronic"
    assert deep["nearest_junction_distance"] == "150"
    assert proximal["category_set"] == ""
    assert proximal["category_assignment_status"] == "outside_v1_categories"
    assert proximal["category_assignment_reason"] == "proximal_intronic_9_100"


def test_nearest_junction_type_is_transcript_strand_aware() -> None:
    result = classify(250, "intron_variant", REVERSE_MODEL)
    assert result["nearest_junction_type"] == "acceptor"


def test_normalized_deletion_interval_excludes_shared_anchor() -> None:
    assert affected_reference_interval(100, "CAA", "C") == (101, 102)


def test_standard_grch38_contig_aliases_are_explicitly_supported() -> None:
    assert normalized_contig("chr1") == normalized_contig("1")
    assert normalized_contig("chrM") == normalized_contig("MT")
    model = TranscriptModel("ENST3", "1", "+", ((100, 199), (500, 599)))
    assert classify(350, "intron_variant", model)["category_set"] == "deep_intronic"


def test_exon_boundary_insertion_is_not_misclassified_as_deep_intronic() -> None:
    result = classify_transcript(
        consequence="intron_variant",
        feature_type="Transcript",
        chrom="chr1",
        pos=199,
        ref="A",
        alt="AT",
        model=MODEL,
    )
    assert result["category_set"] == "exonic_splicing_motif"
    assert result["nearest_junction_distance"] == ""
