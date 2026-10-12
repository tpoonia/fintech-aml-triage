---
title: "Q-TRACE · September 15, 2026 · Research proposal"
subtitle: "One-page summary · meeting 1 of 7 · retrospective reconstruction, prepared October 2026"
---

**Status.** This is a retrospective reconstruction. The repository record begins on Oct 6, 2026. It preserves the pre-October project in two places:

- `docs/DECISIONS.md`, Q1: a generic QML study (Iris, QM9, WDBC) with a mitigate-or-not decision.
- The early-October research plan, which describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, and a Never/Always/Fixed/Q-TRACE comparison.

No results existed on this date. The original September materials, if any, take precedence.

**Purpose.** To propose the research question: when is quantum error mitigation worth its cost for a quantum machine-learning model, and can a cost-aware decision layer (Q-TRACE) decide?

**Key messages.**

- **Noise matters.** NISQ hardware is noisy (Preskill 2018). Noise shrinks the expectation values QML models output, pulling probabilities toward 0.5, so threshold decisions can flip.
- **Mitigation is expensive.** ZNE runs several noise-amplified circuits (Temme 2017; Kandala 2019; Giurgica-Tiron 2020). Readout mitigation needs calibration circuits (Bravyi 2021). The benefit is platform-dependent (Russo 2023).
- **Proposed approach.** Q-TRACE mitigates only when the expected benefit outweighs the extra cost. It is tested on Iris, WDBC and QM9 with Qiskit Aer, against never, always and a fixed rule.
- **Research questions.**
  - RQ1: When does mitigation improve output enough to justify its cost?
  - RQ2: Can the benefit-versus-cost decision beat never, always or a fixed rule?

| Slide | Content | Speaker (proposed) |
|---|---|---|
| 1 | Title and question | Mayank |
| 2 | Why quantum noise matters (illustrative) | Mayank |
| 3 | Why mitigation is expensive | Mayank |
| 4 | Proposed approach: Q-TRACE | Tushar |
| 5 | Research questions and planned method | Tushar |

**What happened next (added October 2026).** On Oct 6 the scope was narrowed to credit-card fraud detection, with several mitigation actions, label-free decision inputs and pre-registered phases. The study was completed Oct 6–8, 2026.

**Needs confirmation.**

- The presenter split.
- Whether any original September slides exist.
- The meeting date itself: it was supplied by the team and is not confirmed by a public course calendar.
