# Q-TRACE semester presentation package

Seven capstone meeting presentations, one folder per date. Each folder works on its own and holds:

- an editable PowerPoint (`.pptx`) and a PDF export;
- the deck source (`source/deck.js`);
- speaker notes, embedded in the PPTX and in `speaker_notes.md`;
- a word-for-word script (`script.md` and the printable `script.pdf`);
- a short professor Q&A sheet (`QA.md`, `QA.pdf`);
- a one-page summary (`summary.md`, `summary.pdf`).

The final-defense folder also holds a comprehensive `Technical_QA_Guide`.

**Totals.** 7 presentations, 54 slides (backups included). Consolidated schedule: [`Semester_Presentation_Schedule.pdf`](Semester_Presentation_Schedule.pdf).

## Chronology (read first)

**The research was completed on October 6–8, 2026.** The repository history dates every phase, including the one-time sealed test (Oct 8).

- **Oct 13 – Nov 24 meetings:** report completed work, organized by topic. Each results slide carries a label with its phase and completion date. The later meetings deepen the analysis, limitations and dissemination; they do not stage an ongoing experiment.
- **Sep 15 and Sep 29 meetings:** *retrospective reconstructions*, prepared in October 2026 and labeled on every slide.
  - The record begins on Oct 6, 2026. It preserves the pre-October project in two places. `docs/DECISIONS.md` (Q1) records a generic QML study (Iris, QM9, WDBC) with a mitigate-or-not decision. The early-October research plan describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and "current accuracy" as an example input.
  - The decks show only those recorded elements, published background and a reconstructed plan. They contain no results.
  - The record does not say which elements were shown on Sept 15 versus Sept 29.
  - They do not present the fraud application as a September decision.

## Schedule and files

| Date | Topic | Slides | Duration* | Presenters (split) | PPTX | PDF | Script | Status | Instructor confirmation needed |
|---|---|---|---|---|---|---|---|---|---|
| September 15, 2026 | Research proposal | 5 | ≈ 3:46 | Mayank: slides 1–3 · Tushar: slides 4–5 (proposed; no presenter record exists for this date; team to confirm) | [`Q-TRACE_2026-09-15_Research-Proposal.pptx`](2026-09-15/Q-TRACE_2026-09-15_Research-Proposal.pptx) | [`Q-TRACE_2026-09-15_Research-Proposal.pdf`](2026-09-15/Q-TRACE_2026-09-15_Research-Proposal.pdf) | [`script.pdf`](2026-09-15/script.pdf) | Complete; validated (retrospective reconstruction) | Past meeting; deck is a retrospective record. Confirm whether original September slides exist. |
| September 29, 2026 | Research design | 5 | ≈ 4:10 | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed; no presenter record exists for this date; team to confirm) | [`Q-TRACE_2026-09-29_Research-Design.pptx`](2026-09-29/Q-TRACE_2026-09-29_Research-Design.pptx) | [`Q-TRACE_2026-09-29_Research-Design.pdf`](2026-09-29/Q-TRACE_2026-09-29_Research-Design.pdf) | [`script.pdf`](2026-09-29/script.pdf) | Complete; validated (retrospective reconstruction) | Past meeting; deck is a retrospective record. Confirm whether original September slides exist. |
| October 13, 2026 | Implementation progress | 5 | ≈ 4:18 | Mayank: slides 1–3 · Tushar: slides 4–5 (same first-half/second-half pattern as the committed Oct 13 script; team to confirm) | [`Q-TRACE_2026-10-13_Implementation-Progress.pptx`](2026-10-13/Q-TRACE_2026-10-13_Implementation-Progress.pptx) | [`Q-TRACE_2026-10-13_Implementation-Progress.pdf`](2026-10-13/Q-TRACE_2026-10-13_Implementation-Progress.pdf) | [`script.pdf`](2026-10-13/script.pdf) | Complete; validated | Slot length and upload format. Choose this 5-slide deck or the earlier 8-slide whole-study deck. |
| October 27, 2026 | Noise and mitigation | 5 | ≈ 4:20 | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) | [`Q-TRACE_2026-10-27_Noise-and-Mitigation.pptx`](2026-10-27/Q-TRACE_2026-10-27_Noise-and-Mitigation.pptx) | [`Q-TRACE_2026-10-27_Noise-and-Mitigation.pdf`](2026-10-27/Q-TRACE_2026-10-27_Noise-and-Mitigation.pdf) | [`script.pdf`](2026-10-27/script.pdf) | Complete; validated | Date, slot length and upload format. |
| November 10, 2026 | Policy selection | 5 | ≈ 4:28 | Mayank: slides 1–3 · Tushar: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) | [`Q-TRACE_2026-11-10_Policy-Selection.pptx`](2026-11-10/Q-TRACE_2026-11-10_Policy-Selection.pptx) | [`Q-TRACE_2026-11-10_Policy-Selection.pdf`](2026-11-10/Q-TRACE_2026-11-10_Policy-Selection.pdf) | [`script.pdf`](2026-11-10/script.pdf) | Complete; validated | Date, slot length and upload format. |
| November 24, 2026 | Final experimental findings | 5 | ≈ 4:21 | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) | [`Q-TRACE_2026-11-24_Final-Findings.pptx`](2026-11-24/Q-TRACE_2026-11-24_Final-Findings.pptx) | [`Q-TRACE_2026-11-24_Final-Findings.pdf`](2026-11-24/Q-TRACE_2026-11-24_Final-Findings.pdf) | [`script.pdf`](2026-11-24/script.pdf) | Complete; validated | Date and format. Add any author decisions (venue, author order) to slide 5. |
| December 8, 2026 | Final capstone defense | 18 + 6 backup | ≈ 13:16 | Mayank: slides 1–5, 10–11, 17–18 · Tushar: slides 6–9, 12–16 (proposed for roughly equal time; team to confirm) | [`Q-TRACE_2026-12-08_Final-Defense.pptx`](2026-12-08-final/Q-TRACE_2026-12-08_Final-Defense.pptx) | [`Q-TRACE_2026-12-08_Final-Defense.pdf`](2026-12-08-final/Q-TRACE_2026-12-08_Final-Defense.pdf) | [`script.pdf`](2026-12-08-final/script.pdf) | Complete; validated | Allowed length (the research plan records a 3–5-slide limit for biweekly meetings), date and format. |

\* Duration = estimated speaking time at 140 words per minute, with numerals expanded, from the script. Five-minute slots leave about half a minute for transitions. The defense estimate excludes backup slides.

**Dates.**

- **Confirmed public university date:** Fall 2026 classes end Dec 21, 2026 (Katz School 2026–27 academic calendar; see `deliverables/submission/VENUES.md`).
- **Meeting dates:** supplied by the team.
  - The research plan (`docs/research/deep-research-report.md`) also lists Oct 13, Oct 27, Nov 10, Nov 24 and Dec 8 as biweekly presentations, and records that "your professor requests only 3–5 slides".
  - None of these dates has been verified against an official course schedule.
  - Treat them as planning dates until the instructor confirms them.

**Presenter assignments.**

- **Oct 13:** the first-half/second-half split of the committed Oct 13 script.
- **All other meetings:** proposed. Openers alternate between meetings, and the final defense splits time roughly equally.
- **Status:** every split needs team confirmation. No slide or note claims who did which part of the research.

## How the decks were built

- **Design system:** `_system/design.js` (pptxgenjs).
  - Palette and fonts: navy, teal and amber; Cambria headings, Calibri body.
  - Every title slide carries a seven-meeting tracker.
  - Every content slide carries a chronology label and a sources line; results slides state when the work was completed.
- **Figures:**
  - publication figures from `deliverables/figures/`;
  - phase figures from `results/figures/`;
  - semester figures from `_system/figures/`.
  - Provenance for all of them is in [`FIGURES.md`](FIGURES.md).
- **Single source per deck:** `source/deck.js` defines each slide together with its speaker, word-for-word script and key points. The build writes the PPTX speaker notes, `script.md` and `speaker_notes.md` from that one source, so they always match.

**Rebuild from a clean environment:**

```bash
deliverables/presentations/semester/_system/build_all.sh
```

**Requirements:**
- Node ≥ 18 (with `npm ci`);
- `uv` (Python 3.12);
- LibreOffice (for the PDF exports);
- pandoc ≥ 3 and tectonic (for the script, Q&A and summary PDFs);
- poppler (`pdftoppm`, `pdfinfo`).

The build validates every PPTX, checks that each summary is one page and fails on missing glyphs or overfull lines.

## Integrity

- **Sources:** every number traces to committed tables in `results/tables/`. The source line on each slide names them.
- **Scope of claims:** no quantum advantage, no hardware validation, no publication acceptance and no general applicability.
- **Statistics:** the held-out test has only four model structures. Slides that show its intervals say so.
- **Nothing changed or sent:** no experiment was re-run, no frozen or sealed result was modified, and nothing was submitted to the university or published.
- **Existing decks kept:** `deliverables/presentations/Q-TRACE_Oct13_Progress.pptx` (8 slides) and `Q-TRACE_Final_Capstone.pptx` (16 + 2) are unchanged. They are earlier whole-study versions; this package supersedes them for the semester schedule.
