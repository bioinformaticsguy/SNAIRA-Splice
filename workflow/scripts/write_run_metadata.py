#!/usr/bin/env python3
"""Record reproducibility metadata for a completed run."""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import os
import platform
import subprocess
from pathlib import Path

from io_utils import atomic_json


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", required=True, type=Path)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--resolved-samples", required=True, type=Path)
    parser.add_argument("--pipeline-version", required=True)
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--vep-cache-version", required=True)
    parser.add_argument("--snakemake-version", required=True)
    parser.add_argument("--vep-stats", nargs="+", required=True, type=Path)
    args = parser.parse_args()
    git = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
    metadata = {
        "pipeline_version": args.pipeline_version,
        "git_commit": git.stdout.strip() if git.returncode == 0 else "unavailable",
        "execution_date_utc": dt.datetime.now(dt.UTC).isoformat(),
        "snakemake_version": args.snakemake_version,
        "vep_version": args.vep_stats[0].read_text(encoding="utf-8").strip(),
        "vep_cache_version": args.vep_cache_version,
        "ensembl_release": args.vep_cache_version,
        "reference_assembly": args.assembly,
        "reference_fasta": str(args.reference),
        "reference_fasta_sha256": digest(args.reference),
        "configuration_sha256": digest(args.config),
        "resolved_samples_sha256": digest(args.resolved_samples),
        "python_version": platform.python_version(),
        "conda_environment": os.environ.get("CONDA_PREFIX", "unavailable"),
    }
    atomic_json(args.output, metadata)


if __name__ == "__main__":
    raise SystemExit(main())
