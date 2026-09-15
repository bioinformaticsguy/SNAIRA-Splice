#!/usr/bin/env python3
"""Run one sample through the existing Snakemake workflow."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import tempfile
from pathlib import Path

import yaml

SAFE_SAMPLE_ID = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_.-]*$")


def atomic_yaml(path: Path, value: dict) -> None:
    """Write a YAML file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        yaml.safe_dump(value, handle, sort_keys=False)
        temporary = Path(handle.name)
    temporary.replace(path)


def atomic_json(path: Path, value: dict) -> None:
    """Write a JSON file atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", dir=path.parent, delete=False, encoding="utf-8") as handle:
        json.dump(value, handle, indent=2)
        handle.write("\n")
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--vcf", required=True, type=Path, help="Input SNV/small-indel VCF or VCF.gz")
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--outdir", required=True, type=Path, help="Pipeline output root; sample is added beneath it")
    parser.add_argument("--config", default=Path("config/config.yaml"), type=Path)
    parser.add_argument("--profile", default=Path("profiles/local"), type=Path)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    repository = Path(__file__).resolve().parents[1]
    config_path = args.config if args.config.is_absolute() else (Path.cwd() / args.config)
    profile_path = args.profile if args.profile.is_absolute() else (Path.cwd() / args.profile)
    vcf = args.vcf.resolve()
    outdir = args.outdir.resolve()
    if not SAFE_SAMPLE_ID.fullmatch(args.sample_id):
        parser.error("sample ID must contain only letters, numbers, periods, underscores, and hyphens")
    if not vcf.is_file():
        parser.error(f"input VCF does not exist: {vcf}")
    if not config_path.is_file():
        parser.error(f"configuration does not exist: {config_path}")
    config = yaml.safe_load(config_path.read_text(encoding="utf-8"))
    runtime = outdir / "metadata" / "single_sample_input" / args.sample_id
    manifest_path = runtime / "manifest.json"
    generated_config = runtime / "config.yaml"
    outputs = {"snv_pass_vcf": str(vcf)}
    for suffix in (".tbi", ".csi"):
        index = Path(f"{vcf}{suffix}")
        if index.is_file():
            outputs["snv_pass_vcf_index"] = str(index)
            break
    manifest = {
        "manifest_version": "1.0",
        "sample_id": args.sample_id,
        "family_id": "",
        "role": "NA",
        "sex": "NA",
        "path_base": "absolute",
        "outputs": outputs,
        "reference": config["reference"]["assembly"],
        "pipeline_name": "SNAIRA-Splice single-sample wrapper",
        "pipeline_phase": "standalone_splice_analysis",
    }
    atomic_json(manifest_path, manifest)
    config["manifests"]["source"] = str(manifest_path)
    config["output_root"] = str(outdir)
    atomic_yaml(generated_config, config)
    command = [
        "snakemake",
        "--snakefile",
        str(repository / "Snakefile"),
        "--directory",
        str(repository),
        "--profile",
        str(profile_path.resolve()),
        "all",
        "--configfile",
        str(generated_config),
    ]
    if args.dry_run:
        command.append("--dry-run")
    print("Running:", " ".join(command))
    subprocess.run(command, check=True)
    print(f"Report: {outdir / args.sample_id / '05_report' / f'{args.sample_id}.snaira_splice.html'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
