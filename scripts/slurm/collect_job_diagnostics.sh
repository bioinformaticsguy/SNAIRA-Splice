#!/usr/bin/env bash
# Collect a small, reviewable diagnostic bundle for one SNAIRA-Splice SLURM job.
set -euo pipefail

usage() {
  cat <<'EOF'
Usage: collect_job_diagnostics.sh JOB_ID [--output-dir DIR] [--tail-lines N] [--configfile FILE]

Create a compact diagnostic bundle for a failed or completed SNAIRA-Splice
controller job. The script is read-only with respect to workflow outputs: it
copies only the generated run configuration and bounded log tails. It never
copies VCFs, reference data, Conda environments, or complete large logs.

Arguments:
  JOB_ID                Numeric SLURM controller job ID
  --output-dir DIR      Bundle directory (default: diagnostics/slurm-job-JOB_ID)
  --tail-lines N        Lines retained from each matching log (default: 300)
  --configfile FILE     Generated workflow config to copy, if available
  -h, --help            Show this help
EOF
}

job_id="${1:-}"
case "$job_id" in
  -h|--help|"") usage; exit 0 ;;
esac
[[ "$job_id" =~ ^[0-9]+$ ]] || { echo "ERROR: JOB_ID must be numeric" >&2; exit 2; }
shift

output_dir="diagnostics/slurm-job-$job_id"
tail_lines=300
run_config=""
while (($#)); do
  case "$1" in
    --output-dir) output_dir="${2:?missing value for --output-dir}"; shift 2 ;;
    --tail-lines)
      tail_lines="${2:?missing value for --tail-lines}"
      [[ "$tail_lines" =~ ^[1-9][0-9]*$ ]] || { echo "ERROR: --tail-lines must be a positive integer" >&2; exit 2; }
      shift 2
      ;;
    --configfile) run_config="${2:?missing value for --configfile}"; shift 2 ;;
    -h|--help) usage; exit 0 ;;
    *) echo "ERROR: unknown argument: $1" >&2; usage >&2; exit 2 ;;
  esac
done

repository="$(cd "$(dirname "${BASH_SOURCE[0]}")/../.." && pwd)"
cd "$repository"
bundle="$(mkdir -p "$output_dir" && cd "$output_dir" && pwd)"

for command_name in sacct scontrol git; do
  command -v "$command_name" >/dev/null || {
    echo "ERROR: required command is unavailable: $command_name" >&2
    exit 2
  }
done

write_command() {
  local destination="$1"
  shift
  if "$@" > "$bundle/$destination" 2>&1; then
    return 0
  fi
  printf '\nCommand exited non-zero: %q' "$1" >> "$bundle/$destination"
}

write_command sacct.txt sacct -j "$job_id" \
  --format=JobID,JobName%40,State,ExitCode,Elapsed,Start,End,MaxRSS,ReqMem,NodeList
write_command sacct-machine.txt sacct -j "$job_id" --parsable2 --noheader \
  --format=JobID,JobName,State,ExitCode,Elapsed,Start,End,MaxRSS,ReqMem,NodeList
write_command scontrol-show-job.txt scontrol show job "$job_id"
write_command git-revision.txt git rev-parse HEAD
write_command git-status.txt git status --short
write_command git-log.txt git log -5 --oneline

{
  echo "SNAIRA-Splice SLURM diagnostic bundle"
  echo "Controller job ID: $job_id"
  echo "Collected UTC: $(date -u +%FT%TZ)"
  echo "Repository: $repository"
  echo "Tail lines per log: $tail_lines"
  echo
  echo "This bundle excludes source VCFs, references, Conda environments, and full logs."
  echo "Review paths before committing because logs can contain filesystem paths and sample IDs."
} > "$bundle/README.txt"

matching_logs="$bundle/matching-log-files.txt"
if [[ -d logs ]]; then
  find logs -type f -name "*$job_id*" -printf '%T@\t%p\n' | sort -nr > "$matching_logs"
else
  : > "$matching_logs"
fi

log_number=0
while IFS=$'\t' read -r _timestamp log_path; do
  [[ -n "${log_path:-}" && -f "$log_path" ]] || continue
  log_number=$((log_number + 1))
  safe_name="$(basename "$log_path" | tr -cs 'A-Za-z0-9._-' '_')"
  {
    echo "Original path: $log_path"
    echo "Retained tail: $tail_lines lines"
    echo
    tail -n "$tail_lines" "$log_path"
  } > "$bundle/log-${log_number}-${safe_name}.tail.txt"
done < "$matching_logs"

if [[ -z "$run_config" ]]; then
  matches=(output/*/metadata/single_sample_input/*/config.yaml)
  [[ ${#matches[@]} -eq 1 && -s "${matches[0]}" ]] && run_config="${matches[0]}"
fi
if [[ -n "$run_config" && -s "$run_config" ]]; then
  cp "$run_config" "$bundle/generated-run-config.yaml"
else
  printf 'No generated run configuration was supplied or uniquely discovered.\n' > "$bundle/generated-run-config-missing.txt"
fi

find "$bundle" -maxdepth 1 -type f -printf '%f\n' | sort > "$bundle/contents.txt"

print_screen_summary() {
  local -a log_tails=()
  local controller_row=""
  local matched_errors=""
  local recorded_job=""
  local recorded_name=""
  local recorded_state=""
  local recorded_exit=""
  local recorded_elapsed=""
  local recorded_start=""
  local recorded_end=""
  local recorded_max_rss=""
  local recorded_memory=""
  local recorded_node=""

  shopt -s nullglob
  log_tails=("$bundle"/log-*.tail.txt)
  shopt -u nullglob

  echo
  echo "SNAIRA-Splice diagnostic summary"
  echo "Controller job: $job_id"
  echo "Controller status:"
  controller_row="$(awk -F'|' -v job="$job_id" '$1 == job { print; exit }' "$bundle/sacct-machine.txt")"
  if [[ -z "$controller_row" ]]; then
    echo "  No controller row was returned by sacct."
  else
    IFS='|' read -r recorded_job recorded_name recorded_state recorded_exit \
      recorded_elapsed recorded_start recorded_end recorded_max_rss recorded_memory recorded_node \
      <<< "$controller_row"
    echo "  $recorded_job  state=$recorded_state  exit=$recorded_exit  elapsed=$recorded_elapsed"
    echo "  max_rss=${recorded_max_rss:-not_recorded}  requested_memory=${recorded_memory:-not_recorded}  node=${recorded_node:-not_recorded}"
  fi

  if [[ ${#log_tails[@]} -eq 0 ]]; then
    echo "Relevant logs: none found under $repository/logs"
    echo "Next action: wait briefly for SLURM accounting/log flush, then rerun this helper."
  else
    echo "Relevant log tails: ${#log_tails[@]} (stored in $bundle)"
    matched_errors="$(
      grep -HnE -i \
        'reference allele mismatch|error in rule|slurm-job .* failed|workflowerror|traceback|exception|^error:|^error ' \
        "${log_tails[@]}" 2>/dev/null | tail -n 20 || true
    )"
    if [[ -n "$matched_errors" ]]; then
      echo "Most relevant error lines:"
      while IFS= read -r line; do
        echo "  $line"
      done <<< "$matched_errors"
    else
      echo "No standard error signature was found in the retained tails."
      echo "Inspect: $bundle/matching-log-files.txt"
    fi
  fi

  echo "Diagnostic bundle created: $bundle"
}

print_screen_summary
