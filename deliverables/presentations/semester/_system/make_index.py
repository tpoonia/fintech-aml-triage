# ruff: noqa: E501  (this generator emits long Markdown prose and table rows verbatim)
"""Write semester/README.md and semester/SCHEDULE.md from each meeting folder's manifest.json.

Usage (repository root): python deliverables/presentations/semester/_system/make_index.py
Slide counts, durations and speaker splits come from the build manifests, so the index cannot
drift from the decks.
"""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

SEM = Path(__file__).resolve().parents[1]

CONFIRM = {
    "2026-09-15": "Past meeting; deck is a retrospective record. Confirm whether original September slides exist.",
    "2026-09-29": "Past meeting; deck is a retrospective record. Confirm whether original September slides exist.",
    "2026-10-13": "Slot length and upload format. Choose this 5-slide deck or the earlier 8-slide whole-study deck.",
    "2026-10-27": "Date, slot length and upload format.",
    "2026-11-10": "Date, slot length and upload format.",
    "2026-11-24": "Date and format. Add any author decisions (venue, author order) to slide 5.",
    "2026-12-08": "Allowed length (the research plan records a 3–5-slide limit for biweekly meetings), date and format.",
}


def mmss(minutes: float) -> str:
    s = round(minutes * 60)
    return f"{s // 60}:{s % 60:02d}"


def main() -> int:
    rows = []
    for d in sorted(p for p in SEM.iterdir() if p.is_dir() and p.name.startswith("2026-")):
        m = json.loads((d / "manifest.json").read_text())
        rows.append((d.name, m))

    total_slides = sum(m["slides"] for _, m in rows)
    table = [
        "| Date | Topic | Slides | Duration* | Presenters (split) | PPTX | PDF | Script | Status | Instructor confirmation needed |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for name, m in rows:
        slides = f"{m['coreSlides']}" + (
            f" + {m['backupSlides']} backup" if m["backupSlides"] else ""
        )
        status = "Complete; validated" + (
            " (retrospective reconstruction)" if m["retrospective"] else ""
        )
        table.append(
            f"| {m['date']} | {m['topic']} | {slides} | ≈ {mmss(m['minutes'])} | {m['split']} ({m['splitStatus']}) "
            f"| [`{m['file']}.pptx`]({name}/{m['file']}.pptx) | [`{m['file']}.pdf`]({name}/{m['file']}.pdf) "
            f"| [`script.pdf`]({name}/script.pdf) | {status} | {CONFIRM[m['id']]} |"
        )

    readme = f"""# Q-TRACE semester presentation package

Seven capstone meeting presentations, one folder per date. Each folder works on its own and holds:

- an editable PowerPoint (`.pptx`) and a PDF export;
- the deck source (`source/deck.js`);
- speaker notes, embedded in the PPTX and in `speaker_notes.md`;
- a word-for-word script (`script.md` and the printable `script.pdf`);
- a short professor Q&A sheet (`QA.md`, `QA.pdf`);
- a one-page summary (`summary.md`, `summary.pdf`).

The final-defense folder also holds a comprehensive `Technical_QA_Guide`.

**Totals.** {len(rows)} presentations, {total_slides} slides (backups included). Consolidated schedule: [`Semester_Presentation_Schedule.pdf`](Semester_Presentation_Schedule.pdf).

## Chronology (read first)

**The research was completed on October 6–8, 2026.** The repository history dates every phase, including the one-time sealed test (Oct 8).

- **Oct 13 – Nov 24 meetings:** report completed work, organized by topic. Each results slide carries a label with its phase and completion date. The later meetings deepen the analysis, limitations and dissemination; they do not stage an ongoing experiment.
- **Sep 15 and Sep 29 meetings:** *retrospective reconstructions*, prepared in October 2026 and labeled on every slide.
  - The record begins on Oct 6, 2026. It preserves the pre-October project in two places. `docs/DECISIONS.md` (Q1) records a generic QML study (Iris, QM9, WDBC) with a mitigate-or-not decision. The early-October research plan describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and "current accuracy" as an example input.
  - The decks show only those recorded elements, published background and a reconstructed plan. They contain no results.
  - The record does not say which elements were shown on Sept 15 versus Sept 29.
  - They do not present the fraud application as a September decision.

## Schedule and files

{chr(10).join(table)}

\\* Duration = estimated speaking time at 140 words per minute, with numerals expanded, from the script. Five-minute slots leave about half a minute for transitions. The defense estimate excludes backup slides.

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
"""
    (SEM / "README.md").write_text(readme)

    sched = [
        "---",
        'title: "Q-TRACE semester presentation schedule"',
        'subtitle: "Mayank Kumar Pokhriyal · Tushar Poonia · M.S. in Artificial Intelligence capstone, Katz School of Science and Health, Yeshiva University"',
        "---",
        "",
        "**Research completed on October 6–8, 2026.**",
        "",
        "- The October and November meetings present completed results by topic.",
        "- The September decks are retrospective reconstructions, prepared in October 2026.",
        "",
        "| # | Date | Topic | Slides | Est. time | Proposed presenters | Status |",
        "|--|-------------|-------------------|--------|-------|-------------------------|-----------------|",
    ]
    for i, (_name, m) in enumerate(rows, 1):
        slides = f"{m['coreSlides']}" + (f" + {m['backupSlides']}" if m["backupSlides"] else "")
        status = "retrospective record" if m["retrospective"] else "ready for review"
        short = datetime.strptime(m["date"], "%B %d, %Y").strftime("%b %-d, %Y")
        sched.append(
            f"| {i} | {short} | {m['topic']} | {slides} | {mmss(m['minutes'])} | {m['split']} | {status} |"
        )
    sched += [
        "",
        "## Dates: confirmed versus planning",
        "",
        "- **Confirmed (public):** Fall 2026 classes end December 21, 2026 (Katz School 2026–27 academic calendar).",
        "- **Planning dates (team-supplied):** all seven meeting dates.",
        "  - October 13 – December 8 also appear in the research plan's biweekly schedule.",
        "  - None has been verified against an official course schedule.",
        "  - **Confirm each with the instructor.**",
        "",
        "## Confirmation needed",
        "",
    ]
    for _name, m in rows:
        sched.append(f"- **{m['date']}:** {CONFIRM[m['id']]}")
    sched += [
        "",
        "## Files",
        "",
        "Each date has its own folder in `deliverables/presentations/semester/`:",
        "",
        "- PPTX and PDF;",
        "- source;",
        "- speaker notes and word-for-word script;",
        "- Q&A sheet;",
        "- one-page summary.",
        "",
        "The final defense adds `Technical_QA_Guide.pdf`.",
        "",
    ]
    (SEM / "SCHEDULE.md").write_text("\n".join(sched))
    print(f"README.md and SCHEDULE.md written: {len(rows)} presentations, {total_slides} slides")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
