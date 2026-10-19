---
title: "Q-TRACE · October 27, 2026 · Noise and mitigation"
subtitle: "One-page summary · meeting 4 of 7 · Phases 3B and 4, completed October 7, 2026"
---

**Chronology.** This meeting presents two completed phases (Oct 7, 2026) in more depth than the Oct 13 overview.

**Purpose.** To explain what simulated noise does to the frozen fraud classifier, how readout mitigation and zero-noise extrapolation work and what they cost, and what a resource-matched comparison shows.

**Key numbers (frozen P3A-R model, validation partition).**

| Question | Result | Source |
|---|---|---|
| Does noise hurt discrimination? | ΔAUPRC ≤ 0.003, every CI contains 0; at least 46 of 47 top frauds kept | `p3b_exact_metrics.csv` |
| Does noise hurt calibration? | Brier 0.0093 → 0.121; ECE 0.083 → 0.346; precision 0.53 → 0.03 | `p3b_exact_metrics.csv`, `p4_exact_diagnostics.csv` |
| Negative control | symmetric readout: ranking metrics unchanged (Δ = 0) | `p3b_negative_control.csv` |
| Readout mitigation | Brier 0.053 → 0.011 (high readout noise; 1,024 shots) | `p4_summary.csv` |
| ZNE | Brier 0.055 → 0.038 (high depolarizing noise) | `p4_summary.csv` |
| Combined | Brier 0.122 → 0.054 (combined-high); 3× shots: 0.121 | `p4_summary.csv` |
| Costs | ZNE: 3× shots, 9× two-qubit-gate exposure; readout ≈ 2 circuits per batch | `p4_costs.csv` |

**Takeaways.**

- Noise damaged calibration and threshold decisions, not discrimination.
- Mitigation removed a bias that extra shots could not.
- No action improved AUPRC over its resource-matched comparator.
- The best action depended on the noise type, which set up the selection question for Nov 10.

| Slide | Content | Speaker (proposed) |
|---|---|---|
| 1 | Title and message | Tushar |
| 2 | How we simulated noise | Tushar |
| 3 | Calibration, not discrimination | Tushar |
| 4 | Two mitigation tools and costs | Mayank |
| 5 | Resource-matched comparison | Mayank |

**Needs confirmation.**

- The presenter split.
- The meeting date and format: supplied by the team, not on a public course calendar.
