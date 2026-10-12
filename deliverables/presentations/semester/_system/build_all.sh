#!/usr/bin/env bash
# Rebuild the whole semester presentation package from a clean environment.
#   deliverables/presentations/semester/_system/build_all.sh
# Steps: install pinned Node deps -> regenerate semester figures -> build 7 decks (+ notes, scripts)
#        -> validate PPTX -> export deck PDFs (LibreOffice) -> render document PDFs (pandoc + tectonic)
#        -> write README.md / SCHEDULE.md -> schedule PDF -> render slide images for visual QA (_render/).
set -euo pipefail
SYS="$(cd "$(dirname "$0")" && pwd)"
SEM="$(dirname "$SYS")"
ROOT="$(cd "$SEM/../../.." && pwd)"
SOFFICE="${SOFFICE:-/Applications/LibreOffice.app/Contents/MacOS/soffice}"
PPTX_VALIDATE="${PPTX_VALIDATE:-}"   # optional: path to the pptx skill's scripts/office/validate.py

echo "== dependencies"
(cd "$SYS" && npm ci --no-audit --no-fund --silent)

echo "== figures"
(cd "$ROOT" && uv run python deliverables/presentations/semester/_system/make_semester_figures.py)

echo "== decks"
(cd "$SYS" && node build_deck.js "$SEM"/2026-*)

if [ -n "$PPTX_VALIDATE" ]; then
  echo "== PPTX validation"
  for f in "$SEM"/2026-*/*.pptx; do
    uv run --no-project --with lxml --with defusedxml --with pillow python "$PPTX_VALIDATE" "$f" | tail -1
  done
fi

echo "== deck PDFs"
for d in "$SEM"/2026-*/; do
  "$SOFFICE" --headless --convert-to pdf --outdir "$d" "$d"/*.pptx >/dev/null 2>&1
  ls "$d"/*.pdf >/dev/null
done

echo "== document PDFs"
"$SYS/build_docs.sh"

echo "== index and schedule"
python3 "$SYS/make_index.py"
log=$(pandoc "$SEM/SCHEDULE.md" --from markdown --pdf-engine=tectonic --metadata-file="$SYS/pandoc/doc.yaml" \
  -o "$SEM/Semester_Presentation_Schedule.pdf" 2>&1)
if grep -q "Missing character\|Overfull" <<<"$log"; then echo "ERROR: schedule PDF: missing glyphs or overfull lines" >&2; exit 1; fi

echo "== slide images for visual QA (gitignored)"
rm -rf "$SEM/_render" && mkdir -p "$SEM/_render"
for d in "$SEM"/2026-*/; do
  id="$(basename "$d")"
  pdftoppm -png -r 80 "$d"/Q-TRACE_*.pdf "$SEM/_render/$id"
done
echo "done: $(ls "$SEM"/_render/*.png | wc -l | tr -d ' ') slide images in _render/"
