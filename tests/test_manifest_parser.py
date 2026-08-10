import json
from pathlib import Path

import pytest
from manifest_utils import ManifestError, discover_manifests, load_samples, nested_get, resolve_manifest_path


def manifest(tmp_path: Path, sample: str = "S1", mode: str = "manifest_directory") -> Path:
    (tmp_path / "input.vcf.gz").touch()
    (tmp_path / "input.vcf.gz.tbi").touch()
    value = {
        "manifest_version": "1.0",
        "sample_id": sample,
        "reference": "GRCh38",
        "path_base": mode,
        "output_directory": "outputs",
        "outputs": {"snv_pass_vcf": "input.vcf.gz", "snv_pass_vcf_index": "input.vcf.gz.tbi"},
    }
    path = tmp_path / f"{sample}.json"
    path.write_text(json.dumps(value))
    return path


def test_nested_get() -> None:
    assert nested_get({"outputs": {"snv": "x"}}, "outputs.snv") == "x"
    with pytest.raises(ManifestError):
        nested_get({}, "outputs.snv")


def test_manifest_directory_resolution(tmp_path: Path) -> None:
    path = manifest(tmp_path)
    data = json.loads(path.read_text())
    assert resolve_manifest_path(data, path, "input.vcf.gz") == (tmp_path / "input.vcf.gz").resolve()


def test_output_directory_is_joined_once(tmp_path: Path) -> None:
    path = manifest(tmp_path, mode="output_directory")
    data = json.loads(path.read_text())
    assert resolve_manifest_path(data, path, "snv/file.vcf.gz") == (tmp_path / "outputs/snv/file.vcf.gz").resolve()


def test_absolute_requires_absolute(tmp_path: Path) -> None:
    path = manifest(tmp_path, mode="absolute")
    data = json.loads(path.read_text())
    with pytest.raises(ManifestError):
        resolve_manifest_path(data, path, "relative.vcf.gz")


def test_invalid_path_base(tmp_path: Path) -> None:
    path = manifest(tmp_path, mode="wrong")
    samples, report = load_samples(path)
    assert not samples and not report["valid"]
    assert "invalid path_base" in report["errors"][0]


def test_duplicate_samples(tmp_path: Path) -> None:
    first = manifest(tmp_path, "S1")
    second_dir = tmp_path / "other"
    second_dir.mkdir()
    second = manifest(second_dir, "S1")
    listing = tmp_path / "list.txt"
    listing.write_text(f"{first}\n{second}\n")
    _, report = load_samples(listing)
    assert not report["valid"]
    assert any("duplicate sample_id" in error for error in report["errors"])


def test_missing_file(tmp_path: Path) -> None:
    path = manifest(tmp_path)
    (tmp_path / "input.vcf.gz").unlink()
    _, report = load_samples(path)
    assert any("missing input VCF" in error for error in report["errors"])


def test_discover_list_relative_to_list(tmp_path: Path) -> None:
    path = manifest(tmp_path)
    listing = tmp_path / "list.txt"
    listing.write_text(f"{path.name}\n")
    assert discover_manifests(listing) == [path.resolve()]
