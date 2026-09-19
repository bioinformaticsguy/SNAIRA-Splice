from pathlib import Path


def test_tabular_vep_uses_requested_field_options() -> None:
    """Guard against emitting placeholder values for requested VEP fields."""
    rule = (Path(__file__).parents[1] / "workflow" / "rules" / "vep.smk").read_text(encoding="utf-8")
    assert 'VEP_OUTPUT_FLAGS = "--symbol --biotype --variant_class --hgvs --numbers --hgnc"' in rule
    assert rule.count("{params.output_flags}") == 2
