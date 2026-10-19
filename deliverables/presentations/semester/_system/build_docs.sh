#!/usr/bin/env bash
# Render each meeting folder's Markdown documents to printable PDFs (pandoc + tectonic).
#   script.md -> script.pdf, QA.md -> QA.pdf, summary.md -> summary.pdf (must be one page),
#   Technical_QA_Guide.md -> Technical_QA_Guide.pdf (final defense only)
set -euo pipefail
SYS="$(cd "$(dirname "$0")" && pwd)"
SEM="$(dirname "$SYS")"
render() { # in out metadata; fails on missing glyphs or overfull lines
  local log
  log=$(pandoc "$1" --from markdown --pdf-engine=tectonic --metadata-file="$SYS/pandoc/$3" -o "$2" 2>&1) || { echo "$log" >&2; return 1; }
  if grep -q "Missing character\|Overfull" <<<"$log"; then
    echo "ERROR: $1: missing glyphs or overfull lines" >&2
    grep "Missing character\|Overfull" <<<"$log" | sort -u >&2
    return 1
  fi
}
for dir in "$SEM"/2026-*/; do
  d="${dir%/}"
  render "$d/script.md" "$d/script.pdf" doc.yaml
  render "$d/QA.md" "$d/QA.pdf" doc.yaml
  render "$d/summary.md" "$d/summary.pdf" onepage.yaml
  [ -f "$d/Technical_QA_Guide.md" ] && render "$d/Technical_QA_Guide.md" "$d/Technical_QA_Guide.pdf" doc.yaml
  pages=$(pdfinfo "$d/summary.pdf" | awk '/^Pages:/{print $2}')
  if [ "$pages" != "1" ]; then echo "ERROR: $(basename "$d")/summary.pdf has $pages pages (must be 1)" >&2; exit 1; fi
  echo "$(basename "$d"): script.pdf QA.pdf summary.pdf (1 page)$( [ -f "$d/Technical_QA_Guide.pdf" ] && echo ' Technical_QA_Guide.pdf')"
done
