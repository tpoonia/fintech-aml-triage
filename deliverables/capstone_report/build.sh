#!/usr/bin/env bash
# Build the capstone report (PDF + editable DOCX) from Q-TRACE_Capstone_Report.md.
# Requires pandoc (>= 3) and tectonic. Figures come from ../figures (PDF for print, PNG for DOCX).
set -euo pipefail
cd "$(dirname "$0")"
SRC=Q-TRACE_Capstone_Report.md
COMMON=(--from markdown --citeproc --resource-path=.:../figures --metadata link-citations=true)
pandoc "$SRC" "${COMMON[@]}" --default-image-extension=pdf --pdf-engine=tectonic -o Q-TRACE_Capstone_Report.pdf
pandoc "$SRC" "${COMMON[@]}" --default-image-extension=png -o Q-TRACE_Capstone_Report.docx
echo "built Q-TRACE_Capstone_Report.pdf and Q-TRACE_Capstone_Report.docx"
