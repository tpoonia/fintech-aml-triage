# Submission plan, checklist and timeline

**Prepared:** 2026-10-08.

**Nothing has been submitted.** Every external submission is a decision for Mayank Kumar Pokhriyal and Tushar Poonia.

**Dates are planning targets, not confirmed deadlines.** The dates below come from the authors' plan. None has been confirmed against the Katz School course calendar or a venue's call for papers. Each date marked **CONFIRM** needs checking before anyone relies on it.

## 1. Timeline

**Meeting presentations.** The full per-meeting deck schedule (Sep 15 – Dec 8, 2026) is in `deliverables/presentations/semester/README.md` and `Semester_Presentation_Schedule.pdf`. Those meeting dates are planning dates supplied by the team, and each needs confirmation with the instructor.

| Date (2026) | Day | Milestone | Package item | Status | Confirmation needed |
|---|---|---|---|---|---|
| Oct 12 | Mon | Freeze the results and figures for the progress talk | `figures/`; `presentations/Q-TRACE_Oct13_Progress.pptx` | **Ready now.** The results are final, and the sealed test was opened on Oct 8. | **CONFIRM** that the course expects slides to be uploaded before the talk, and in which format (PPTX or PDF) |
| Oct 13 | Tue | Capstone progress presentation, about 5 minutes | Oct 13 deck plus `speaker_notes/Oct13_presentation_script.md` | Ready; rehearse to time | **CONFIRM** the date, time, slot length and Q&A length with the instructor. The original Oct 13 scope (decision F24) was one clean VQC; the deck now reports the completed study. Check that this suits the session. |
| Oct 20 | Tue | Polished research manuscript | `paper/Q-TRACE_manuscript.pdf` + `main.tex` | Draft complete; authors still need to review it and confirm the references | **CONFIRM** whether the course expects a specific template, page limit or citation style |
| Oct 27 | Tue | Updated capstone presentation | `presentations/Q-TRACE_Final_Capstone.pptx` | Draft complete; update it after the Oct 13 feedback | **CONFIRM** that this is a course deliverable and how it is submitted |
| Nov 10–24 | Tue–Tue | Revisions from professor feedback; a Nov 24 deck was planned in the original roadmap | all sources are editable | Not started; depends on feedback | **CONFIRM** the review window and whether Nov 24 is a presentation date |
| Dec 8 | Tue | Final presentation package | final deck, report, paper | Ready for review; finalize after the revisions | **CONFIRM** the final-presentation date, length and required submission items (report format, code, video, poster) |

**Course calendar context.** Fall 2026 classes end **Dec 21, 2026**, according to the public Katz 2026–27 calendar, so the Dec 8 target falls inside the term. No public AIM 5008 rubric, report format or presentation length exists. **CONFIRM** all of these with the instructor.

### External dates (estimates only; see `VENUES.md`)

| Date | Item | Status |
|---|---|---|
| Oct 16, 2026 | AAAI-27 accepted workshop list published | **CONFIRM.** Only relevant if a fitting, *non-archival* workshop appears. |
| Nov 20, 2026 | AAAI-27 workshop paper deadline (AAAI default) | **CONFIRM** |
| Nov 29, 2026 | ICLR 2027 accepted workshop list | **CONFIRM** |
| Nov–Dec 2026 | arXiv preprint (Plan A), after the capstone revisions; needs an arXiv endorser | Authors' decision |
| Dec 2026 – Jan 2027 | TMLR submission (rolling; recommended first venue) | Authors' decision |
| Feb 1, 2027 | Suggested ICLR 2027 workshop contribution deadline | **CONFIRM** |
| ~Apr 2027 | IEEE QCE27 technical papers (QCE26 was Apr 20/27, 2026); posters ~Jun 2027 | **CONFIRM**: the QCE27 call is not published |

## 2. Readiness checklist

### Science and integrity

- [x] Central conclusions checked against the recorded outputs. The independent claims audit found every headline number correct; 23 wording, scope and rounding mismatches were fixed.
- [x] Statistics, intervals, cost accounting, the Oracle definition and the held-out comparisons were re-derived from `results/tables/`.
- [x] Observed findings are separated from interpretation (paper §13 "Observed versus interpreted").
- [x] Statistical caveats are disclosed in the paper, the report and the decks:
  - only 4 held-out structures;
  - the raw-failure advantage of the learned comparators;
  - the gate-free design share;
  - instability between validation and test.
- [x] No claims of quantum advantage, hardware validation, publication acceptance or universal generalization.
- [x] No experiment was re-run. No frozen artifact, sealed result or registered hypothesis was changed. The sealed test was not re-opened.
- [ ] **Authors:** read the paper and the report end to end and sign off on every claim.

### References

- [x] All 35 bibliography entries were verified against Crossref, arXiv, DataCite, OpenAlex, PMLR or Kaggle (`paper/REFERENCES_VERIFICATION.md`).
- [x] Wording corrections M1–M9 and F1–F4 are applied, so that each source is described as it actually reports.
- [ ] **Authors:** confirm each reference yourselves. This is decision E61; the current status is AGENT-CHECKED. Pay particular attention to:
  - 2026 arXiv preprints that may have changed version or been published since: Szachara, Majid, Scavino, Zhang, Mingue Njiki;
  - name spellings: Dinuț (t-comma) and Mckay/McKay.

### Manuscript

- [x] LaTeX source compiles with no warnings; all citations and cross-references resolve; 18 pages.
- [x] Every figure traces to committed tables (`figures/FIGURES.md`).
- [ ] **Authors:** decide author order, affiliations and contact emails. Emails are deliberately left out.
- [ ] **Authors:** confirm the AI-assistance statement is acceptable to the course and to the target venue.
- [ ] Convert to the chosen venue's template (for example the IEEE conference class or Quantum's template) and fit its page limit. This needs the venue decision first.
- [ ] Decide whether to make the repository public, or to provide an anonymized artifact, so the "Reproducibility and Data Availability" statement can give a link. The repository is currently private.

### Capstone report

- [x] PDF (23 pages) and editable DOCX, consistent with the manuscript.
- [ ] **Authors:** complete the team-contribution statement. `docs/contribution_log.md` has no entries yet from Tushar Poonia.
- [ ] **CONFIRM** any required Katz School report template, cover page or length.

### Presentations

- [x] Both decks pass PPTX validation and were rendered slide by slide with no clipped text. Speaker notes are embedded.
- [x] The Oct 13 script is split 4/4 slides and runs about 5 minutes; the final notes run about 14 minutes with timings.
- [x] `speaker_notes/Final_QA.md` covers 27 anticipated questions.
- [ ] Rehearse both talks with a timer. Check the decks in PowerPoint itself; the QA renders used LibreOffice.

## 3. Decisions needed from Mayank and Tushar

1. **Author order and contribution statement.** Who is the corresponding author? Tushar's contributions need to be recorded.
2. **References.** Confirm the agent-checked references (E61) before anything leaves the course.
3. **Venue.** Choose a target from `VENUES.md`, considering timeline, cost, travel and whether the course needs a submission at all.
4. **Repository visibility.** Make the repository public, release an artifact snapshot, or keep it private and say "available on request".
5. **AI-assistance disclosure.** Accept or edit the statement in the paper and the report against the course and venue policies.
6. **Course format requirements.** Confirm templates, page limits and the submission format for each date above.
7. **Compliance.** Confirm that both authors have completed YU's required CITI Responsible Conduct of Research training. Also confirm whether YU wants a "not human-subjects research" determination; the data are public, de-identified and used in simulation only.
8. **arXiv endorser.** Since January 2026, new arXiv submitters need prior arXiv authorship in the field or a personal endorsement. Ask the faculty mentor.
9. **AI disclosure at venues.** QCE26 desk-rejected "generated papers". IEEE requires disclosure in the acknowledgments and Springer in the Methods section. Make sure the final text is clearly your own writing and that the disclosure matches each venue's policy.

## 4. Pre-submission run-through (once a venue is chosen)

1. Re-read the venue's current call, its formatting rules and its AI policy.
2. Port `main.tex` to the venue class.
3. Re-run `deliverables/paper/build.sh` and check the page limit.
4. Anonymize the paper if the review is double-blind: remove names, the repository link and any self-identifying text.
5. Re-check each 2026 preprint reference for a published version.
6. Freeze a tagged artifact. The project currently creates no tags or releases, so ask first.
7. Submit only after both authors have explicitly agreed.
