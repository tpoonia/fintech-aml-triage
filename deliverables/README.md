# Q-TRACE academic submission package

Final documents for professor review and later submission. They report the completed, pre-registered study as recorded in the repository: Phases 0–5C, the Phase 7 validation comparison, the one-time sealed held-out evaluation and the validation-only ablations.

**Status (2026-10-08):**
- Ready for professor review.
- Not peer reviewed and not submitted anywhere.
- References were checked by an AI assistant; the authors must confirm them before any external submission.

## Contents

| Folder | File | What it is |
|---|---|---|
| [`paper/`](paper/) | `Q-TRACE_manuscript.pdf` | Publication-formatted manuscript (generic article format, 18 pages) |
| | `main.tex`, `references.bib`, `build.sh` | Editable LaTeX source and the verified BibTeX file. `build.sh` builds the PDF with tectonic. |
| | `REFERENCES_VERIFICATION.md` | Per-reference verification against Crossref, arXiv, DataCite, OpenAlex, PMLR and Kaggle, with the wording corrections that were applied |
| [`capstone_report/`](capstone_report/) | `Q-TRACE_Capstone_Report.pdf` | Final capstone report (23 pages): executive summary, methodology, verified results, limitations, reproducibility instructions, project record |
| | `Q-TRACE_Capstone_Report.docx` | Editable Word version of the same report |
| | `Q-TRACE_Capstone_Report.md`, `build.sh` | Source (pandoc Markdown with citations). `build.sh` produces both the PDF and the DOCX. |
| [`presentations/`](presentations/) | `Q-TRACE_Oct13_Progress.pptx` | October 13, 2026 progress talk: 8 slides, about 5 minutes, speaker notes embedded |
| | `Q-TRACE_Final_Capstone.pptx` | Final capstone talk: 16 slides plus 2 backup slides, about 14 minutes, speaker notes embedded |
| | `*.pdf` | PDF exports of both decks, rendered by LibreOffice with Carlito and Caladea, which are metric-compatible with Calibri and Cambria |
| | `build/` | Deck sources (pptxgenjs, Node). Rebuild with `npm ci && node build_oct13.js && node build_final.js`. |
| [`presentations/semester/`](presentations/semester/) | `README.md`, `Semester_Presentation_Schedule.pdf` | **Semester package:** seven meeting decks (Sep 15 – Dec 8; 54 slides), each with PPTX, PDF, source, speaker notes, word-for-word script (with printable PDF), Q&A sheet and one-page summary. The September decks are labeled retrospective reconstructions. These supersede the two decks above for the meeting schedule; those are kept unchanged. |
| [`speaker_notes/`](speaker_notes/) | `Oct13_presentation_script.md` | Word-for-word 5-minute script split between Mayank (slides 1–4) and Tushar (slides 5–8) |
| | `Final_presentation_speaker_notes.md` | Per-slide speaker, timing, key points, transitions and phrasing rules |
| | `Final_QA.md` | 27 anticipated professor questions with accurate, sourced answers |
| [`figures/`](figures/) | `fig1`–`fig9` (`.pdf` + `.png`) | Publication figures (Okabe–Ito palette) |
| | `make_figures.py`, `FIGURES.md` | Generator, and the provenance of every figure and quoted number |
| [`submission/`](submission/) | `SUBMISSION_PLAN.md` | Checklist and timeline; dates that need confirmation are flagged |
| | `VENUES.md` | Researched venue options with recommendations. Nothing has been submitted. |

## Rebuild everything

Run from the repository root:

```bash
uv run python deliverables/figures/make_figures.py
deliverables/paper/build.sh
deliverables/capstone_report/build.sh
(cd deliverables/presentations/build && npm ci && node build_oct13.js && node build_final.js)
```

**Requirements:**
- `uv` (Python 3.12, locked);
- tectonic;
- pandoc ≥ 3;
- Node ≥ 18.

LibreOffice and poppler (`pdftoppm`) are optional; they are used only for visual checks.

## Integrity notes

- **Traceability.** Every quantitative figure and number comes from committed tables in `results/tables/`; see `figures/FIGURES.md`.
- **Pre-package audit.** Before packaging, an independent claims audit checked 186 claims and a bibliography check verified 35 entries. Their corrections were applied here and in `docs/`.
- **Nothing re-run or modified.** No experiment was re-run. No frozen artifact, sealed result or registered hypothesis was modified. The sealed test was not re-opened.
- **What the package does not claim.** It makes no claim of quantum advantage, hardware validation, publication acceptance or universal generalization.
