#!/usr/bin/env bash
# Build the manuscript PDF from main.tex + references.bib (requires tectonic, which runs BibTeX itself).
# Figures are read from ../figures (regenerate with: uv run python deliverables/figures/make_figures.py).
set -euo pipefail
cd "$(dirname "$0")"
tectonic main.tex
mv main.pdf Q-TRACE_manuscript.pdf
echo "built Q-TRACE_manuscript.pdf"
