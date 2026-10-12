---
title: "Q-TRACE · December 8, 2026 · Final capstone defense"
subtitle: "One-page summary · meeting 7 of 7 · complete study (October 6–8, 2026)"
---

**Research question.** When should a noisy quantum fraud classifier spend extra quantum resources on error mitigation, and is learning that decision better than a simple observable rule?

**Design.**

- 64 independently trained 4-qubit VQCs on the public European credit-card fraud data (283,726 rows, 0.17% fraud).
- Exact density-matrix noise simulation.
- Five actions: none, readout mitigation, ZNE, both, 3× shots.
- Label-free probes only.
- Cost-aware Oracle: the cheapest action within 10% of the best Brier score.
- Pre-registered gates, then a one-time sealed test on 16 unseen models from 4 unseen structures.

**Findings.**

| Finding | Evidence |
|---|---|
| Noise damaged calibration, not discrimination | ΔAUPRC ≤ 0.003; Brier 0.0093 → 0.121 |
| Mitigation repaired calibration; extra shots did not | Brier 0.122 → 0.054 (combined); 3× shots 0.121 |
| No material residual for a learned controller | G3B and G3C failed; no controller trained |
| Probe rule near-Oracle on unseen models | material errors 2.0% [1.4, 2.6]; Brier −0.03%; +0.6% shots; 8.8% under categorical noise |
| Learned comparators did not reduce material errors | best 2.1% (difference +0.0005 [−0.016, +0.027]); but raw disagreement 6.5% vs 21.9% |

**Limits.**

- Simulation only; 4 qubits; one dataset; two mitigation techniques.
- 4 held-out structures, so the intervals are likely too narrow.
- H2 is non-superiority.
- The gate-free design share drives the saving over always-combined.
- The gate probe is nearly blind to thermal noise.
- No quantum advantage.

**Contribution.**

1. A characterization: calibration, not discrimination.
2. A leakage-safe 64-model counterfactual benchmark.
3. A pre-registered, held-out test of learned selection against simple rules.

**Structure.** 18 core slides plus backups B1–B6, about 13 minutes.

**Proposed split.** Mayank: slides 1–5, 10–11, 17–18. Tushar: slides 6–9, 12–16. The team should confirm it.

**Needs confirmation.**

- The allowed length: the research plan records a 3–5-slide limit for the biweekly meetings.
- The presentation date and format.
- Author confirmation of the references.
- The AI-use disclosure policy for the course.
