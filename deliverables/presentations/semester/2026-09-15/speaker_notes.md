# Q-TRACE — Research proposal: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | September 15, 2026 (meeting 1 of 7): Research proposal |
| **Deck** | `Q-TRACE_2026-09-15_Research-Proposal.pptx` (5 slides) |
| **Speakers** | Mayank: slides 1–3 · Tushar: slides 4–5 (proposed; no presenter record exists for this date; team to confirm) |
| **Length** | ≈ 3:45 of speech (≈ 526 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 2:17, Tushar ≈ 1:28 |
| **Status** | Retrospective reconstruction prepared in October 2026; see the note below |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | When is quantum error mitigation worth its cost? | Mayank | 0:00–0:33 | proposal stage: no results; noise → mitigation → cost; question: when is mitigation worth its cost, and can a decision layer decide? | Why noise matters. |
| 2 | Why quantum noise matters | Mayank | 0:33–1:30 | NISQ hardware is noisy (Preskill 2018); noise shrinks expectation values, more with depth; probabilities drift toward 0.5 → threshold decisions change | Mitigation can help, but it is not free. |
| 3 | Why error mitigation is expensive | Mayank | 1:30–2:17 | ZNE: amplify noise, extrapolate to zero (Temme 2017; Kandala 2019; Giurgica-Tiron 2020); readout mitigation: calibration-based, cheaper (Bravyi 2021); benefit is platform-dependent (Russo 2023) | Hand-off to Tushar: the proposed approach. |
| 4 | Proposed approach: Q-TRACE | Tushar | 2:17–2:57 | decision layer on a QML model: mitigate only if benefit exceeds cost; mitigation: ZNE and readout; simulation: Qiskit Aer; benchmarks: Iris, WDBC, QM9; compared with Never / Always / Fixed | Which questions we will answer, and how. |
| 5 | Research questions and planned method | Tushar | 2:57–3:45 | RQ1: when is mitigation worth its cost?; RQ2: can the benefit-vs-cost decision beat never / always / fixed?; plan: simulate → measure benefit and cost → decide → compare; note: scope narrowed Oct 6 (fraud, several actions) | Questions. |

## Sources for the numbers on these slides

- **Slide 2:** Preskill (2018) Quantum 2:79. Figure: illustrative global-depolarizing model, not project data.
- **Slide 3:** Temme et al. (2017) PRL 119:180509; Kandala et al. (2019) Nature 567:491; Giurgica-Tiron et al. (2020) IEEE QCE; Bravyi et al. (2021) PRA 103:042605; Russo et al. (2023) IEEE TQE 4:1–18. Figure: illustrative.
- **Slide 4:** docs/DECISIONS.md Q1; docs/PROJECT_SPEC.md §2; docs/research/deep-research-report.md (description of the pre-October deck).
- **Slide 5:** Reconstructed from docs/DECISIONS.md Q1 and the research plan's description of the pre-October deck; wording is ours.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
