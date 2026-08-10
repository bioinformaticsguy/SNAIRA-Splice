from splice_utils import canonical_splice_type, collapse_rows, consequence_terms, transcript_rank


def base(**updates):
    row = {
        "variant_key": "chr1:10:A:G",
        "chrom": "chr1",
        "pos": "10",
        "ref": "A",
        "alt": "G",
        "sample_id": "S1",
        "gene_symbol": "GENE",
        "gene_id": "ENSG1",
        "transcript_id": "ENST2",
        "transcript_biotype": "protein_coding",
        "consequence": "splice_donor_variant&intron_variant",
        "canonical_splice_type": "donor",
        "canonical_transcript": "",
        "mane_select": "",
        "mane_plus_clinical": "",
        "transcript_support_level": "2",
        "appris": "",
        "vep_impact": "HIGH",
        "source_vcf": "in.vcf.gz",
        "source_manifest": "manifest.json",
    }
    row.update(updates)
    return row


def test_consequence_parsing() -> None:
    assert consequence_terms("missense_variant&splice_region_variant") == {"missense_variant", "splice_region_variant"}
    assert canonical_splice_type("splice_donor_variant&intron_variant") == "donor"
    assert canonical_splice_type("splice_acceptor_variant") == "acceptor"
    assert canonical_splice_type("splice_region_variant") is None


def test_transcript_ranking() -> None:
    mane = base(transcript_id="ENST9", mane_plus_clinical="YES")
    canonical = base(transcript_id="ENST1", canonical_transcript="YES")
    assert transcript_rank(mane) < transcript_rank(canonical)


def test_collapse_and_deterministic_representative() -> None:
    rows = [base(transcript_id="ENST2"), base(transcript_id="ENST1")]
    result = collapse_rows(rows)
    assert len(result) == 1
    assert result[0]["affected_transcript_count"] == 2
    assert result[0]["representative_transcript"] == "ENST1"
    assert result[0]["canonical_splice_candidate"] == "yes"
