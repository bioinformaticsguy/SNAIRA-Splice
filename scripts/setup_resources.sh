#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: setup_resources.sh [options]
  --assembly GRCh38             Assembly (currently GRCh38 only)
  --resource-dir DIR            Destination (default: resources)
  --vep-cache-version N         Ensembl/VEP cache release (default: 113)
  --species NAME                Species (default: homo_sapiens)
  --download-reference          Install reference FASTA, faidx, and dictionary
  --download-vep-cache          Install the offline VEP cache
  --install-software            Create the pinned VEP Conda environment separately
  --install-spliceai            Install pinned SpliceAI software and copy its GRCh38 annotation
  --force                       Replace an existing completed requested resource
  -h, --help                    Show this help
EOF
}

assembly="GRCh38"
resource_dir="resources"
vep_version="113"
species="homo_sapiens"
download_reference=false
download_cache=false
install_software=false
install_spliceai=false
force=false
while (($#)); do
  case "$1" in
    --assembly) assembly="${2:?missing value}"; shift 2 ;;
    --resource-dir) resource_dir="${2:?missing value}"; shift 2 ;;
    --vep-cache-version) vep_version="${2:?missing value}"; shift 2 ;;
    --species) species="${2:?missing value}"; shift 2 ;;
    --download-reference) download_reference=true; shift ;;
    --download-vep-cache) download_cache=true; shift ;;
    --install-software) install_software=true; shift ;;
    --install-spliceai) install_spliceai=true; shift ;;
    --force) force=true; shift ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done
[[ "$assembly" == "GRCh38" ]] || { echo "ERROR: only GRCh38 is supported" >&2; exit 2; }
$download_reference || $download_cache || $install_software || $install_spliceai || { echo "ERROR: select at least one action" >&2; usage >&2; exit 2; }
command -v sha256sum >/dev/null || { echo "ERROR: required command not found: sha256sum" >&2; exit 1; }
if $download_reference || $download_cache; then
  for command in curl sum; do command -v "$command" >/dev/null || { echo "ERROR: required command not found: $command" >&2; exit 1; }; done
fi

mkdir -p "$resource_dir"
resource_dir="$(cd "$resource_dir" && pwd)"
temporary_dir="$(mktemp -d "${TMPDIR:-/tmp}/snaira-splice-resources.XXXXXX")"
trap 'rm -rf "$temporary_dir"' EXIT
manifest_tsv="$resource_dir/resource_manifest.tsv"
[[ -f "$manifest_tsv" ]] || printf 'resource\tversion\tpath\tsha256\tsource\n' > "$manifest_tsv"

record_resource() {
  local name="$1" version="$2" path="$3" source="$4" checksum
  checksum="$(sha256sum "$path" | cut -d' ' -f1)"
  local filtered="$temporary_dir/manifest.filtered.tsv"
  awk -F '\t' -v resource="$name" 'NR == 1 || $1 != resource' "$manifest_tsv" > "$filtered"
  printf '%s\t%s\t%s\t%s\t%s\n' "$name" "$version" "$path" "$checksum" "$source" >> "$filtered"
  mv "$filtered" "$manifest_tsv"
}

verify_ensembl_checksum() {
  local source_url="$1" downloaded="$2" filename checksum_url expected actual
  filename="$(basename "$source_url")"
  checksum_url="${source_url%/*}/CHECKSUMS"
  if curl --fail --silent --show-error --location --retry 3 --output "$temporary_dir/CHECKSUMS" "$checksum_url"; then
    expected="$(awk -v file="$filename" '$3 == file {print $1 " " $2; exit}' "$temporary_dir/CHECKSUMS")"
    if [[ -n "$expected" ]]; then
      actual="$(sum "$downloaded" | awk '{print $1 " " $2}')"
      [[ "$actual" == "$expected" ]] || { echo "ERROR: authoritative Ensembl checksum failed for $filename" >&2; exit 1; }
      echo "Verified Ensembl CHECKSUMS entry for $filename"
    else
      echo "WARNING: $filename is absent from Ensembl CHECKSUMS; retaining recorded SHA-256" >&2
    fi
  else
    echo "WARNING: Ensembl CHECKSUMS unavailable; retaining recorded SHA-256" >&2
  fi
}

if $install_software; then
  command -v conda >/dev/null || { echo "ERROR: conda is required for --install-software" >&2; exit 1; }
  software_prefix="$resource_dir/software/vep-${vep_version}"
  if [[ -e "$software_prefix/.complete" ]] && ! $force; then
    echo "VEP software already complete: $software_prefix"
  else
    mkdir -p "$resource_dir/software"
    if [[ -d "$software_prefix" ]]; then
      conda env update --prefix "$software_prefix" --file workflow/envs/vep.yaml --prune --yes
    else
      conda env create --prefix "$software_prefix" --file workflow/envs/vep.yaml --yes
    fi
    "$software_prefix/bin/vep" --help >/dev/null
    date -u +%FT%TZ > "$software_prefix/.complete"
  fi
fi

if $install_spliceai; then
  command -v conda >/dev/null || { echo "ERROR: conda is required for --install-spliceai" >&2; exit 1; }
  spliceai_prefix="$resource_dir/software/spliceai-1.3.1"
  spliceai_dir="$resource_dir/spliceai"
  spliceai_marker="$spliceai_dir/.spliceai-1.3.1.complete"
  if [[ -f "$spliceai_marker" ]] && ! $force; then
    echo "SpliceAI resources already complete: $spliceai_dir"
  else
    mkdir -p "$resource_dir/software" "$spliceai_dir"
    if [[ ! -x "$spliceai_prefix/bin/spliceai" ]] || $force; then
      if [[ -d "$spliceai_prefix" ]]; then
        conda env update --prefix "$spliceai_prefix" --file workflow/envs/spliceai.yaml --prune --yes
      else
        conda env create --prefix "$spliceai_prefix" --file workflow/envs/spliceai.yaml --yes
      fi
    fi
    annotation_source="$(find "$spliceai_prefix/lib" -path '*/spliceai/annotations/grch38.txt' -print -quit)"
    [[ -f "$annotation_source" ]] || { echo "ERROR: bundled SpliceAI GRCh38 annotation not found" >&2; exit 1; }
    cp "$annotation_source" "$temporary_dir/grch38.txt"
    mv "$temporary_dir/grch38.txt" "$spliceai_dir/grch38.txt"
    "$spliceai_prefix/bin/spliceai" --help >/dev/null
    record_resource spliceai_grch38_annotation "1.3.1" "$spliceai_dir/grch38.txt" "spliceai Python package"
    date -u +%FT%TZ > "$spliceai_marker"
  fi
fi

if $download_reference; then
  for command in bgzip samtools; do command -v "$command" >/dev/null || { echo "ERROR: $command is required; install workflow/envs/bcftools.yaml" >&2; exit 1; }; done
  reference_dir="$resource_dir/reference"
  fasta="$reference_dir/GRCh38.fa"
  marker="$reference_dir/.GRCh38.complete"
  reference_url="https://ftp.ensembl.org/pub/release-${vep_version}/fasta/homo_sapiens/dna/Homo_sapiens.GRCh38.dna.primary_assembly.fa.gz"
  if [[ -f "$marker" ]] && ! $force; then
    echo "Reference already complete: $fasta"
  else
    mkdir -p "$reference_dir"
    compressed="$temporary_dir/reference.fa.gz"
    curl --fail --location --retry 5 --output "$compressed" "$reference_url"
    verify_ensembl_checksum "$reference_url" "$compressed"
    gzip -t "$compressed"
    gzip -dc "$compressed" > "$temporary_dir/GRCh38.fa"
    samtools faidx "$temporary_dir/GRCh38.fa"
    samtools dict -o "$temporary_dir/GRCh38.dict" "$temporary_dir/GRCh38.fa"
    mv "$temporary_dir/GRCh38.fa" "$fasta"
    mv "$temporary_dir/GRCh38.fa.fai" "$fasta.fai"
    mv "$temporary_dir/GRCh38.dict" "$reference_dir/GRCh38.dict"
    record_resource reference_fasta "$vep_version" "$fasta" "$reference_url"
    date -u +%FT%TZ > "$marker"
  fi
fi

if $download_cache; then
  command -v tar >/dev/null || { echo "ERROR: tar is required" >&2; exit 1; }
  cache_root="$resource_dir/vep"
  marker="$cache_root/.${species}_${vep_version}_${assembly}.complete"
  cache_url="https://ftp.ensembl.org/pub/release-${vep_version}/variation/indexed_vep_cache/${species}_vep_${vep_version}_${assembly}.tar.gz"
  if [[ -f "$marker" ]] && ! $force; then
    echo "VEP cache already complete: $cache_root"
  else
    mkdir -p "$cache_root"
    archive="$temporary_dir/vep-cache.tar.gz"
    curl --fail --location --retry 5 --output "$archive" "$cache_url"
    verify_ensembl_checksum "$cache_url" "$archive"
    tar -tzf "$archive" >/dev/null
    tar -xzf "$archive" -C "$temporary_dir"
    extracted="$temporary_dir/$species"
    [[ -d "$extracted/$vep_version" ]] || { echo "ERROR: unexpected VEP cache archive layout" >&2; exit 1; }
    if [[ -d "$cache_root/$species/$vep_version" ]]; then
      $force || { echo "ERROR: incomplete cache exists; use --force" >&2; exit 1; }
      rm -rf "$cache_root/$species/$vep_version"
    fi
    mkdir -p "$cache_root/$species"
    mv "$extracted/$vep_version" "$cache_root/$species/$vep_version"
    archive_checksum="$(sha256sum "$archive" | cut -d' ' -f1)"
    printf '%s  %s\n' "$archive_checksum" "$(basename "$cache_url")" > "$cache_root/$species/$vep_version/archive.sha256"
    record_resource vep_cache_archive "$vep_version" "$cache_root/$species/$vep_version/archive.sha256" "$cache_url"
    date -u +%FT%TZ > "$marker"
  fi
fi

json_tmp="$temporary_dir/resource_manifest.json"
printf '{\n  "assembly": "%s",\n  "species": "%s",\n  "vep_cache_version": %s,\n  "manifest_tsv": "%s",\n  "completed_at_utc": "%s"\n}\n' \
  "$assembly" "$species" "$vep_version" "$manifest_tsv" "$(date -u +%FT%TZ)" > "$json_tmp"
mv "$json_tmp" "$resource_dir/resource_manifest.json"
echo "Resource setup completed: $resource_dir/resource_manifest.json"
