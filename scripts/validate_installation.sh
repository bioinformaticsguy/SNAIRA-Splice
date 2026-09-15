#!/usr/bin/env bash
set -euo pipefail
config_file="${1:-config/config.yaml}"
for command in snakemake conda; do command -v "$command" >/dev/null || { echo "ERROR: missing $command" >&2; exit 1; }; done
[[ -f "$config_file" ]] || { echo "ERROR: missing config: $config_file" >&2; exit 1; }
python - "$config_file" <<'PY'
import sys
import yaml
from pathlib import Path

cfg = yaml.safe_load(Path(sys.argv[1]).read_text())
for dotted in ("reference.fasta", "reference.fasta_index", "spliceai.annotation"):
    value = cfg
    for part in dotted.split("."):
        value = value[part]
    if not Path(value).exists():
        print(f"WARNING: configured external resource is absent: {dotted}={value}")
PY
snakemake --configfile "$config_file" --lint
snakemake --configfile "$config_file" --dry-run
