#!/usr/bin/env python3
"""Generate a portable, variant-centric SNAIRA-Splice HTML report."""

from __future__ import annotations

import argparse
import csv
import gzip
import hashlib
import html
import subprocess
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


def read_rows(path: Path) -> list[dict[str, str]]:
    """Read a gzip-compressed TSV."""
    with gzip.open(path, "rt", encoding="utf-8") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def sha256(path: Path) -> str:
    """Return a file SHA-256 or ``unavailable``."""
    if not path.is_file():
        return "unavailable"
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def git_state() -> tuple[str, str]:
    """Return commit and dirty-state strings."""
    commit = subprocess.run(["git", "rev-parse", "HEAD"], text=True, capture_output=True, check=False)
    status = subprocess.run(["git", "status", "--porcelain"], text=True, capture_output=True, check=False)
    return (
        commit.stdout.strip() if commit.returncode == 0 else "unavailable",
        "yes" if status.stdout.strip() else "no",
    )


def score(row: dict[str, str]) -> float | None:
    """Return the score while preserving missing versus zero."""
    value = row.get("spliceai_max", "")
    return float(value) if value not in {"", None} else None


def summary_metrics(
    candidates: list[dict[str, str]],
    evidence: list[dict[str, str]],
    candidate_threshold: float,
    review_threshold: float,
) -> dict[str, int]:
    """Calculate report cards from candidate and complete predictor evidence."""
    by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in evidence:
        by_variant[row["normalized_variant_id"]].append(row)
    maxima = {
        key: max((score(row) for row in rows if score(row) is not None), default=None)
        for key, rows in by_variant.items()
    }
    return {
        "total_normalized_variants": len(by_variant),
        "canonical_donor_variants": sum(
            "canonical_donor" in row.get("splice_category_union", "").split(";") for row in candidates
        ),
        "canonical_acceptor_variants": sum(
            "canonical_acceptor" in row.get("splice_category_union", "").split(";") for row in candidates
        ),
        "near_splice_variants": sum(
            "near_splice" in row.get("category_set_union", "").split(";") for row in candidates
        ),
        "spliceai_ge_candidate": sum(value is not None and value >= candidate_threshold for value in maxima.values()),
        "spliceai_ge_0_50": sum(value is not None and value >= 0.50 for value in maxima.values()),
        "spliceai_ge_0_80": sum(value is not None and value >= 0.80 for value in maxima.values()),
        "review_zone_variants": sum(
            value is not None and review_threshold <= value < candidate_threshold for value in maxima.values()
        ),
        "spliceai_not_scored_variants": sum(value is None for value in maxima.values()),
    }


def _badge(value: str, css: str = "neutral") -> str:
    return f'<span class="badge {css}">{html.escape(value or "—")}</span>'


def _call_summary(row: dict[str, str]) -> str:
    """Return compact, raw call evidence suitable for the main candidate table."""
    values = [
        ("GT", row.get("genotype", "")),
        ("DP", row.get("read_depth", "")),
        ("GQ", row.get("genotype_quality", "")),
    ]
    return " · ".join(f"{label} {value}" for label, value in values if value) or "—"


def _call_details(row: dict[str, str]) -> str:
    """Return all retained raw VCF call evidence for a candidate detail panel."""
    values = [
        ("GT", row.get("genotype", "")),
        ("DP", row.get("read_depth", "")),
        ("GQ", row.get("genotype_quality", "")),
        ("AD", row.get("allele_depth", "")),
        ("QUAL", row.get("vcf_qual", "")),
        ("FILTER", row.get("vcf_filter", "")),
    ]
    text = " · ".join(f"{label}: {value or '—'}" for label, value in values)
    return f"<p><strong>Normalized VCF call:</strong> {html.escape(text)}</p>"


def _transcript_details(rows: list[dict[str, str]]) -> str:
    if not rows:
        return "<p>No matching VEP transcript row was available for this SpliceAI gene prediction.</p>"
    body = []
    for row in rows:
        ds = " / ".join(row.get(field, "") or "—" for field in ("ds_ag", "ds_al", "ds_dg", "ds_dl"))
        dp = " / ".join(row.get(field, "") or "—" for field in ("dp_ag", "dp_al", "dp_dg", "dp_dl"))
        body.append(
            "<tr>"
            f"<td>{html.escape(row.get('transcript_id', '') or '—')}</td>"
            f"<td>{html.escape(row.get('symbol', '') or row.get('spliceai_gene', '') or '—')}</td>"
            f"<td>{html.escape(row.get('biotype', '') or '—')}</td>"
            f"<td>{html.escape(row.get('consequence', '') or '—')}</td>"
            f"<td>{html.escape(row.get('category_set', '') or row.get('splice_category', '') or '—')}</td>"
            f"<td>{html.escape(row.get('category_assignment_status', '') or '—')}</td>"
            f"<td>{html.escape(_junction_detail(row))}</td>"
            f"<td>{html.escape(row.get('mane_select', '') or '—')}</td>"
            f"<td>{html.escape(ds)}</td><td>{html.escape(dp)}</td>"
            f"<td>{html.escape(row.get('spliceai_status', '') or '—')}</td>"
            "</tr>"
        )
    return (
        '<div class="table-wrap"><table class="detail-table"><thead><tr><th>Transcript</th><th>Gene</th>'
        "<th>Biotype</th><th>VEP consequence</th><th>Category</th><th>Category status</th><th>Nearest junction (bp)</th><th>MANE Select</th>"
        "<th>DS AG / AL / DG / DL</th><th>DP AG / AL / DG / DL</th><th>Status</th></tr></thead>"
        f"<tbody>{''.join(body)}</tbody></table></div>"
    )


def _junction_detail(row: dict[str, str]) -> str:
    """Format a nearest-junction distance while retaining the boundary type."""
    distance = row.get("nearest_junction_distance", "")
    boundary = row.get("nearest_junction_type", "")
    if not distance:
        return "—"
    return f"{distance} ({boundary})" if boundary else distance


def _variant_rows(rows: list[dict[str, str]], transcripts: dict[str, list[dict[str, str]]], table_name: str) -> str:
    output = []
    for index, row in enumerate(rows):
        maximum = row.get("spliceai_max", "")
        mane = (
            "MANE+"
            if row.get("any_mane_plus_clinical") == "yes"
            else "MANE"
            if row.get("any_mane_select") == "yes"
            else "no"
        )
        category = row.get("category_set_union", "") or row.get("splice_category_union", "") or "other"
        search = " ".join(
            (
                row.get("normalized_variant_id", ""),
                row.get("gene_symbols", ""),
                category,
                row.get("vep_consequence_union", ""),
            )
        ).lower()
        output.append(
            f'<tr class="variant-row" data-search="{html.escape(search)}" data-gene="{html.escape(row.get("gene_symbols", "").lower())}" '
            f'data-consequence="{html.escape(row.get("vep_consequence_union", "").lower())}" data-category="{html.escape(category)}" '
            f'data-score="{html.escape(maximum)}" data-mane="{html.escape(mane)}">'
            f"<td>{html.escape(row.get('normalized_variant_id', ''))}</td>"
            f"<td>{html.escape(_call_summary(row))}</td>"
            f"<td>{html.escape(row.get('gene_symbols', '') or '—')}</td>"
            f"<td>{html.escape(row.get('representative_transcript', '') or '—')}</td>"
            f"<td>{_badge(category, 'category')}</td>"
            f"<td>{html.escape(row.get('vep_consequence_union', '') or '—')}</td>"
            f"<td>{_badge(mane, 'mane' if mane != 'no' else 'neutral')}</td>"
            f"<td data-sort-value=\"{html.escape(maximum or '-1')}\">{html.escape(maximum or 'not scored')}</td>"
            f"<td>{html.escape(row.get('spliceai_event', '') or '—')}</td>"
            f"<td>{html.escape(row.get('spliceai_delta_position', '') or '—')}</td>"
            f"<td>{html.escape(row.get('predicted_site_position', '') or '—')}</td>"
            f'<td><button type="button" class="detail-button" aria-expanded="false" data-target="{table_name}-detail-{index}">Inspect</button></td>'
            "</tr>"
            f'<tr id="{table_name}-detail-{index}" class="detail-row" hidden><td colspan="12">'
            f"<p><strong>Retention:</strong> {html.escape(row.get('candidate_reasons', '') or 'review threshold')}</p>"
            f"{_call_details(row)}"
            f"<p><strong>Strongest effects:</strong> {html.escape(row.get('spliceai_effects', '') or 'No scored prediction')}</p>"
            f"{_transcript_details(transcripts.get(row.get('normalized_variant_id', ''), []))}</td></tr>"
        )
    return "".join(output)


def build_report(
    candidates: list[dict[str, str]],
    review: list[dict[str, str]],
    transcripts: list[dict[str, str]],
    evidence: list[dict[str, str]],
    metadata: dict[str, Any],
    candidate_threshold: float,
    review_threshold: float,
) -> str:
    """Return a self-contained HTML report."""
    metrics = summary_metrics(candidates, evidence, candidate_threshold, review_threshold)
    by_variant: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in transcripts:
        by_variant[row["normalized_variant_id"]].append(row)
    missing_reasons = Counter(
        row.get("spliceai_missing_reason", "unspecified") or "unspecified"
        for row in evidence
        if row.get("spliceai_status") != "scored"
    )
    cards = "".join(
        f'<div class="card"><span>{html.escape(label.replace("_", " ").title())}</span><strong>{value}</strong></div>'
        for label, value in metrics.items()
    )
    reasons = (
        "".join(f"<li>{html.escape(reason)}: {count}</li>" for reason, count in sorted(missing_reasons.items()))
        or "<li>None</li>"
    )
    provenance = "".join(
        f"<tr><th>{html.escape(str(key))}</th><td>{html.escape(str(value))}</td></tr>"
        for key, value in metadata.items()
    )
    headers = "".join(
        f'<th><button class="sort" type="button">{label}</button></th>'
        for label in [
            "Variant",
            "Call",
            "Gene",
            "Representative transcript",
            "Region/category",
            "VEP consequence",
            "MANE",
            "SpliceAI max",
            "Predicted event",
            "Delta position",
            "Predicted splice position",
            "Evidence",
        ]
    )
    return f"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SNAIRA-Splice — {html.escape(str(metadata['sample_id']))}</title>
<style>
:root{{--ink:#172033;--muted:#5c677d;--line:#dce2ea;--bg:#f4f7fb;--panel:#fff;--accent:#3157a4;--warn:#8a4b08}}
*{{box-sizing:border-box}} body{{margin:0;background:var(--bg);color:var(--ink);font:14px/1.45 system-ui,sans-serif}}
header,main{{max-width:1500px;margin:auto;padding:24px}} header{{background:#14294f;color:#fff;max-width:none}}
header>div{{max-width:1452px;margin:auto}} h1{{margin:0;font-size:30px}} h2{{margin-top:32px}} .meta{{display:flex;gap:18px;flex-wrap:wrap;color:#dce7ff}}
.notice{{background:#fff3cd;color:#563b00;border-left:5px solid #d39b00;padding:12px 16px;margin:20px 0}}
.cards{{display:grid;grid-template-columns:repeat(auto-fit,minmax(170px,1fr));gap:12px}} .card{{background:var(--panel);padding:14px;border:1px solid var(--line);border-radius:8px}}
.card span{{display:block;color:var(--muted);min-height:40px}} .card strong{{font-size:26px}} .controls{{display:flex;gap:10px;flex-wrap:wrap;background:#fff;padding:12px;border:1px solid var(--line)}}
input,select{{padding:8px;border:1px solid #aeb8c8;border-radius:4px}} .table-wrap{{overflow:auto;background:#fff;border:1px solid var(--line)}} table{{width:100%;border-collapse:collapse}}
th,td{{padding:8px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}} th{{background:#eef2f8;white-space:nowrap}} .sort{{border:0;background:none;font-weight:700;cursor:pointer}}
.badge{{display:inline-block;padding:2px 7px;border-radius:10px;background:#e5e9ef;white-space:nowrap}} .category{{background:#dce8ff;color:#173d82}} .mane{{background:#dff3e4;color:#155d2a}}
.detail-button{{color:#fff;background:var(--accent);border:0;border-radius:4px;padding:5px 9px;cursor:pointer}} .detail-row td{{background:#f8faff;padding:16px}} .detail-table{{font-size:12px}}
.empty{{padding:16px;color:var(--muted)}} details{{background:#fff;border:1px solid var(--line);padding:12px;margin-top:14px}} footer{{color:var(--muted);margin:30px 0}} @media print{{.controls,.detail-button{{display:none}}}}
</style></head><body>
<header><div><h1>SNAIRA-Splice</h1><div class="meta"><span>Sample: <strong>{html.escape(str(metadata['sample_id']))}</strong></span><span>Assembly: {html.escape(str(metadata['assembly']))}</span><span>Pipeline: {html.escape(str(metadata['pipeline_version']))}</span><span>Run: {html.escape(str(metadata['run_date']))}</span><span>VEP: {html.escape(str(metadata['vep_version']))}</span><span>SpliceAI mode: {html.escape(str(metadata['spliceai_mode']))}</span><span>Max distance: {metadata['spliceai_max_distance']} bp</span></div></div></header>
<main><div class="notice"><strong>Research use:</strong> Computational splice predictions are research evidence and do not demonstrate that an RNA splicing event occurs. Scores are not pathogenic/benign classifications.</div>
<h2>Summary</h2><div class="cards">{cards}</div>
<h2>Main candidates</h2><p>Retained by VEP donor/acceptor/splice-region consequence or SpliceAI ≥ {candidate_threshold:g}.</p>
<div class="controls" data-for="candidate-table"><input class="search" type="search" placeholder="Search all fields"><input class="gene-filter" type="search" placeholder="Filter gene"><input class="consequence-filter" type="search" placeholder="Filter VEP consequence"><select class="category-filter"><option value="">All categories</option><option>canonical</option><option>near_splice</option><option>exonic_splicing_motif</option><option>deep_intronic</option></select><label>Minimum SpliceAI <input class="threshold" type="number" min="0" max="1" step="0.05" value="0"></label><label><input class="mane-filter" type="checkbox"> MANE only</label></div>
<div class="table-wrap"><table id="candidate-table"><thead><tr>{headers}</tr></thead><tbody>{_variant_rows(candidates, by_variant, 'candidate')}</tbody></table><p class="empty" hidden>No variants match these filters.</p></div>
<h2>Review dataset</h2><p>All scored variants with SpliceAI ≥ {review_threshold:g}; this includes main candidates and the lower review zone.</p>
<div class="controls" data-for="review-table"><input class="search" type="search" placeholder="Search all fields"><input class="gene-filter" type="search" placeholder="Filter gene"><input class="consequence-filter" type="search" placeholder="Filter VEP consequence"><label>Minimum SpliceAI <input class="threshold" type="number" min="0" max="1" step="0.05" value="{review_threshold:g}"></label></div>
<div class="table-wrap"><table id="review-table"><thead><tr>{headers}</tr></thead><tbody>{_variant_rows(review, by_variant, 'review')}</tbody></table><p class="empty" hidden>No variants match these filters.</p></div>
<h2>SpliceAI coverage</h2><p>{metrics['spliceai_not_scored_variants']} normalized variant(s) had no usable SpliceAI score. Missing is never converted to zero.</p><ul>{reasons}</ul>
<details><summary><strong>Provenance</strong></summary><table>{provenance}</table></details>
<footer>Generated by SNAIRA-Splice. Full machine-readable transcript, variant, review, and raw predictor evidence tables accompany this report.</footer></main>
<script>
document.querySelectorAll('.detail-button').forEach(b=>b.addEventListener('click',()=>{{const r=document.getElementById(b.dataset.target);r.hidden=!r.hidden;b.setAttribute('aria-expanded',String(!r.hidden));}}));
function filterControls(c){{const t=document.getElementById(c.dataset.for), rows=[...t.querySelectorAll('.variant-row')];function apply(){{const q=(c.querySelector('.search')?.value||'').toLowerCase(),gene=(c.querySelector('.gene-filter')?.value||'').toLowerCase(),consequence=(c.querySelector('.consequence-filter')?.value||'').toLowerCase(),cat=c.querySelector('.category-filter')?.value||'',min=parseFloat(c.querySelector('.threshold')?.value||'0'),mane=c.querySelector('.mane-filter')?.checked;let shown=0;rows.forEach(r=>{{const s=r.dataset.score===''?null:parseFloat(r.dataset.score),scoreOK=min<=0||s!==null&&s>=min;const ok=r.dataset.search.includes(q)&&r.dataset.gene.includes(gene)&&r.dataset.consequence.includes(consequence)&&(!cat||r.dataset.category.split(';').includes(cat))&&scoreOK&&(!mane||r.dataset.mane!=='no');r.hidden=!ok;const detail=document.getElementById(r.nextElementSibling?.id);if(!ok&&detail)detail.hidden=true;if(ok)shown++;}});t.parentElement.querySelector('.empty').hidden=shown!==0;}}c.querySelectorAll('input,select').forEach(x=>x.addEventListener('input',apply));apply();}}
document.querySelectorAll('.controls').forEach(filterControls);
document.querySelectorAll('table').forEach(table=>table.querySelectorAll('th .sort').forEach((button,index)=>button.addEventListener('click',()=>{{const body=table.tBodies[0], rows=[...body.querySelectorAll('.variant-row')],dir=button.dataset.dir==='asc'?'desc':'asc';button.dataset.dir=dir;rows.sort((a,b)=>{{const av=a.cells[index]?.dataset.sortValue??a.cells[index]?.innerText??'',bv=b.cells[index]?.dataset.sortValue??b.cells[index]?.innerText??'';return (av.localeCompare(bv,undefined,{{numeric:true}}))*(dir==='asc'?1:-1);}});rows.forEach(row=>{{const detail=row.nextElementSibling?.classList.contains('detail-row')?row.nextElementSibling:null;body.append(row);if(detail)body.append(detail);}});}})));
</script></body></html>"""


def is_masked_spliceai_mode(mode: str) -> bool:
    """Return whether a known local SpliceAI execution mode used masking."""
    return mode.strip().lower() == "local_masked"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--candidates", required=True, type=Path)
    parser.add_argument("--review", required=True, type=Path)
    parser.add_argument("--transcripts", required=True, type=Path)
    parser.add_argument("--spliceai-evidence", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--sample-id", required=True)
    parser.add_argument("--assembly", required=True)
    parser.add_argument("--pipeline-version", required=True)
    parser.add_argument("--run-date", required=True)
    parser.add_argument("--vep-version-file", required=True, type=Path)
    parser.add_argument("--spliceai-version-file", required=True, type=Path)
    parser.add_argument("--spliceai-mode", required=True)
    parser.add_argument("--spliceai-max-distance", required=True, type=int)
    parser.add_argument("--candidate-threshold", required=True, type=float)
    parser.add_argument("--review-threshold", required=True, type=float)
    parser.add_argument("--reference", required=True, type=Path)
    parser.add_argument("--annotation", required=True)
    parser.add_argument("--category-gtf", required=True, type=Path)
    parser.add_argument("--category-release", required=True, type=int)
    parser.add_argument("--category-specification", required=True)
    parser.add_argument("--config-checksum", required=True)
    args = parser.parse_args()
    commit, dirty = git_state()
    annotation_path = Path(args.annotation)
    metadata = {
        "sample_id": args.sample_id,
        "assembly": args.assembly,
        "pipeline_version": args.pipeline_version,
        "run_date": args.run_date,
        "git_commit": commit,
        "git_dirty": dirty,
        "vep_version": args.vep_version_file.read_text(encoding="utf-8").strip(),
        "spliceai_version": args.spliceai_version_file.read_text(encoding="utf-8").strip(),
        "spliceai_mode": args.spliceai_mode,
        "spliceai_max_distance": args.spliceai_max_distance,
        "spliceai_masked": is_masked_spliceai_mode(args.spliceai_mode),
        "spliceai_annotation": args.annotation,
        "spliceai_annotation_sha256": sha256(annotation_path),
        "category_gtf": str(args.category_gtf),
        "category_gtf_sha256": sha256(args.category_gtf),
        "category_annotation_release": args.category_release,
        "category_specification": args.category_specification,
        "reference_path": str(args.reference),
        "reference_sha256": sha256(args.reference),
        "config_sha256": args.config_checksum,
        "candidate_threshold": args.candidate_threshold,
        "review_threshold": args.review_threshold,
    }
    report = build_report(
        read_rows(args.candidates),
        read_rows(args.review),
        read_rows(args.transcripts),
        read_rows(args.spliceai_evidence),
        metadata,
        args.candidate_threshold,
        args.review_threshold,
    )
    args.output.parent.mkdir(parents=True, exist_ok=True)
    temporary = args.output.with_name(f".{args.output.name}.tmp")
    temporary.write_text(report, encoding="utf-8")
    temporary.replace(args.output)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
