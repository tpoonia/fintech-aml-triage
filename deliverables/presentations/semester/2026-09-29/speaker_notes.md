# Q-TRACE — Research design: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | September 29, 2026 (meeting 2 of 7): Research design |
| **Deck** | `Q-TRACE_2026-09-29_Research-Design.pptx` (5 slides) |
| **Speakers** | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed; no presenter record exists for this date; team to confirm) |
| **Length** | ≈ 4:10 of speech (≈ 584 spoken words at 140 words per minute, numerals expanded); Tushar ≈ 2:14, Mayank ≈ 1:56 |
| **Status** | Retrospective reconstruction prepared in October 2026; see the note below |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | Designing the study: model, mitigation and evaluation | Tushar | 0:00–0:30 | design stage, no results; scope as recorded, VQC template, ZNE, evaluation plan | First, the scope as recorded. |
| 2 | Scope as recorded before October 6 | Tushar | 0:30–1:20 | benchmarks: Iris, WDBC, QM9; Qiskit Aer; mitigate or not (ZNE / readout); benefit-minus-cost rule; compared with Never / Always / Fixed; fraud application + multi-action design adopted Oct 6 (not this stage) | The model template. |
| 3 | The variational quantum classifier template | Tushar | 1:20–2:14 | encoding U(x) → trainable ansatz V(θ) → measurement → score; hybrid loop: classical optimizer updates θ; output is an expectation value, the quantity noise distorts | Hand-off to Mayank: zero-noise extrapolation. |
| 4 | Mitigation strategy: zero-noise extrapolation | Mayank | 2:14–3:15 | fold gates (G G† G) to amplify noise without changing the ideal result; measure at several levels, extrapolate to zero; extra circuits = extra shots and gate exposure → the decision | How we would evaluate the decision. |
| 5 | How the decision would be evaluated | Mayank | 3:15–4:10 | per setting: with vs without mitigation → quality change and extra cost; compare Q-TRACE with Never / Always / Fixed; example input then: current accuracy (needs labels; removed Oct 6); metrics fixed later (Oct 6 onward) | Questions. |

## Sources for the numbers on these slides

- **Slide 2:** docs/DECISIONS.md Q1 (answered 2026-10-06); docs/PROJECT_SPEC.md §2; docs/research/deep-research-report.md (description of the pre-October deck).
- **Slide 3:** Havlíček et al. (2019) Nature 567:209; Schuld et al. (2020) PRA 101:032308. Figure: generic template, no project-specific choices.
- **Slide 4:** Temme et al. (2017) PRL 119:180509; Giurgica-Tiron et al. (2020) IEEE QCE 306–316. Figure: illustrative.
- **Slide 5:** docs/DECISIONS.md Q1, A12; docs/research/deep-research-report.md (pre-October deck: Never/Always/Fixed/Q-TRACE, current accuracy input); wording is ours.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
