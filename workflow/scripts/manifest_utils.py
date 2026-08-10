"""Manifest discovery, path resolution, and validation utilities."""

from __future__ import annotations

import hashlib
import json
import re
from collections.abc import Iterable
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

SUPPORTED_MANIFEST_VERSIONS = {"1.0"}
PATH_BASE_MODES = {"manifest_directory", "output_directory", "absolute"}
SAFE_SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


class ManifestError(ValueError):
    """Raised when one or more manifests are invalid."""


@dataclass(frozen=True)
class ResolvedSample:
    """Resolved sample information consumed by the workflow."""

    sample_id: str
    family_id: str
    role: str
    sex: str
    manifest_path: str
    input_vcf: str
    input_vcf_index: str
    reference: str
    source_pipeline: str
    source_pipeline_phase: str
    manifest_checksum: str


def sha256(path: Path) -> str:
    """Return the SHA-256 digest for *path*."""
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def nested_get(data: dict[str, Any], dotted_key: str) -> Any:
    """Read a dotted key from a nested mapping."""
    value: Any = data
    for part in dotted_key.split("."):
        if not isinstance(value, dict) or part not in value:
            raise ManifestError(f"missing manifest field: {dotted_key}")
        value = value[part]
    return value


def discover_manifests(source: Path) -> list[Path]:
    """Discover JSON manifests from a directory, JSON file, or path-list file."""
    source = source.resolve()
    if source.is_dir():
        paths = sorted(source.glob("*.json"))
    elif source.suffix.lower() == ".json":
        paths = [source]
    elif source.is_file():
        paths = []
        for raw in source.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            candidate = Path(line)
            if not candidate.is_absolute():
                candidate = source.parent / candidate
            paths.append(candidate.resolve())
    else:
        raise ManifestError(f"manifest source does not exist: {source}")
    if not paths:
        raise ManifestError(f"no manifest JSON files found from: {source}")
    return paths


def resolve_manifest_path(manifest: dict[str, Any], manifest_path: Path, value: str) -> Path:
    """Resolve a manifest-owned path according to ``path_base``."""
    path = Path(value)
    mode = manifest.get("path_base", "manifest_directory")
    if mode not in PATH_BASE_MODES:
        raise ManifestError(f"invalid path_base {mode!r} in {manifest_path}")
    if mode == "absolute":
        if not path.is_absolute():
            raise ManifestError(f"path_base=absolute requires an absolute path: {value}")
        return path.resolve()
    if path.is_absolute():
        return path.resolve()
    if mode == "manifest_directory":
        return (manifest_path.parent / path).resolve()
    output_directory = manifest.get("output_directory")
    if not output_directory:
        raise ManifestError(f"missing output_directory in {manifest_path}")
    output_base = Path(output_directory)
    if not output_base.is_absolute():
        output_base = manifest_path.parent / output_base
    return (output_base / path).resolve()


def _infer_index(vcf: Path) -> Path:
    if str(vcf).endswith(".vcf.gz"):
        return Path(f"{vcf}.tbi")
    return Path(f"{vcf}.idx")


def load_samples(
    source: Path,
    vcf_key: str = "outputs.snv_pass_vcf",
    index_key: str | None = "outputs.snv_pass_vcf_index",
    require_files: bool = True,
) -> tuple[list[ResolvedSample], dict[str, Any]]:
    """Load, resolve, and cross-validate manifests."""
    errors: list[str] = []
    warnings: list[str] = []
    samples: list[ResolvedSample] = []
    seen_ids: set[str] = set()
    seen_outputs: dict[str, str] = {}
    references: set[str] = set()
    paths = discover_manifests(source)
    for path in paths:
        if not path.is_file():
            errors.append(f"manifest does not exist: {path}")
            continue
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            for required in ("sample_id", "manifest_version", "outputs", "reference"):
                if required not in manifest:
                    raise ManifestError(f"missing required field {required!r} in {path}")
            version = str(manifest["manifest_version"])
            if version not in SUPPORTED_MANIFEST_VERSIONS:
                raise ManifestError(f"unsupported manifest_version {version!r} in {path}")
            sample_id = str(manifest["sample_id"])
            if not SAFE_SAMPLE_ID.fullmatch(sample_id):
                raise ManifestError(f"unsafe sample_id {sample_id!r} in {path}")
            if sample_id in seen_ids:
                raise ManifestError(f"duplicate sample_id {sample_id!r}")
            vcf_value = str(nested_get(manifest, vcf_key))
            vcf = resolve_manifest_path(manifest, path, vcf_value)
            if index_key:
                try:
                    index_value = str(nested_get(manifest, index_key))
                    index = resolve_manifest_path(manifest, path, index_value)
                except ManifestError:
                    index = _infer_index(vcf)
                    warnings.append(f"{sample_id}: index key absent; inferred {index}")
            else:
                index = _infer_index(vcf)
            if require_files and not vcf.is_file():
                errors.append(f"{sample_id}: missing input VCF: {vcf}")
            if require_files and not index.is_file():
                warnings.append(f"{sample_id}: source index missing; pipeline will create an output-area index")
            output_token = str(vcf)
            if output_token in seen_outputs:
                errors.append(f"duplicate input path for {sample_id} and {seen_outputs[output_token]}: {vcf}")
            seen_outputs[output_token] = sample_id
            reference = str(manifest["reference"])
            references.add(reference)
            samples.append(
                ResolvedSample(
                    sample_id=sample_id,
                    family_id=str(manifest.get("family_id", "")),
                    role=str(manifest.get("role", "NA")),
                    sex=str(manifest.get("sex", "NA")),
                    manifest_path=str(path.resolve()),
                    input_vcf=str(vcf),
                    input_vcf_index=str(index),
                    reference=reference,
                    source_pipeline=str(manifest.get("pipeline_name", "")),
                    source_pipeline_phase=str(manifest.get("pipeline_phase", "")),
                    manifest_checksum=sha256(path),
                )
            )
            seen_ids.add(sample_id)
        except (OSError, json.JSONDecodeError, ManifestError, TypeError) as exc:
            errors.append(str(exc))
    if len(references) > 1:
        errors.append(
            "reference-build inconsistency: manifests contain different reference values: "
            + ", ".join(sorted(references))
        )
    report = {
        "valid": not errors,
        "manifest_count": len(paths),
        "sample_count": len(samples),
        "errors": errors,
        "warnings": warnings,
        "supported_manifest_versions": sorted(SUPPORTED_MANIFEST_VERSIONS),
    }
    return samples, report


def samples_as_dicts(samples: Iterable[ResolvedSample]) -> list[dict[str, str]]:
    """Convert sample records to serializable dictionaries."""
    return [asdict(sample) for sample in samples]
