"""Shared atomic and compressed-table I/O helpers."""

from __future__ import annotations

import csv
import gzip
import json
import os
import tempfile
from collections.abc import Iterable
from pathlib import Path
from typing import Any


def atomic_json(path: Path, value: Any) -> None:
    """Write JSON atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as handle:
            json.dump(value, handle, indent=2, sort_keys=True)
            handle.write("\n")
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise


def atomic_tsv(path: Path, rows: Iterable[dict[str, Any]], fields: list[str], gzip_output: bool = False) -> None:
    """Write a TSV (optionally gzip compressed) atomically."""
    path.parent.mkdir(parents=True, exist_ok=True)
    suffix = ".gz" if gzip_output else ""
    fd, temporary = tempfile.mkstemp(dir=path.parent, prefix=f".{path.name}.", suffix=suffix)
    os.close(fd)
    try:
        opener = gzip.open if gzip_output else open
        with opener(temporary, "wt", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(
                handle, fieldnames=fields, delimiter="\t", extrasaction="ignore", lineterminator="\n"
            )
            writer.writeheader()
            writer.writerows(rows)
        os.replace(temporary, path)
    except BaseException:
        Path(temporary).unlink(missing_ok=True)
        raise
