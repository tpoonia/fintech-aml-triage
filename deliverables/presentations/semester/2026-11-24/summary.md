---
title: "Q-TRACE · November 24, 2026 · Final experimental findings"
subtitle: "One-page summary · meeting 6 of 7 · one-time sealed test of October 8, 2026"
---

**Chronology.** The sealed test was opened once on Oct 8, 2026 (21:28 UTC). The manuscript and capstone report were drafted the same day. Before presenting, update slide 5 with any author decisions made since.

**Purpose.** To report the held-out evaluation, compare the rule with learned comparators, show the reliability–resource trade-off, state the statistical limits, and outline the publication path.

**Key numbers (16 unseen models, 4 unseen structures).**

| Item | Result | Source |
|---|---|---|
| Rule R_thr, continuous noise | material errors 2.0% [1.4, 2.6]; Brier regret −0.03%; +0.6% shots vs Oracle; −3.4% vs always-combined | `final_policies_5c_test.csv` |
| Rule, categorical noise | 8.8% (registered bound 10%) | `final_policies_5b_test.csv` |
| Best learned (gradient boosting) | 2.1% material; difference +0.0005 [−0.016, +0.027]; any disagreement 6.5% vs 21.9% | `final_paired_vs_rthr_5c_test.csv` |
| Always-combined | 5.9% material = 1 gate-free setting in 17 | `final_policies_5c_test.csv`, `p5c_design.csv` |
| Hypotheses | H1–H4 supported | `final_metadata.json` |

**Limits to state.**

- Only 4 held-out structures, so the intervals are likely too narrow.
- H2 is a non-superiority result on material errors, not proof that learning cannot help.
- On raw agreement with the Oracle, learned models were closer.
- The evidence is simulation only, at 4 qubits, with a gate probe nearly blind to thermal noise.

**Contribution.**

1. Noise damaged calibration, not discrimination; mitigation repaired it, and extra shots did not.
2. A leakage-safe benchmark of 64 models.
3. A pre-registered test in which a simple probe rule performed competitively with learned comparators.

**Publication path (authors decide).** Nothing has been submitted. Recommended route: arXiv, then TMLR. Alternatives: IEEE QCE27 or Quantum Machine Intelligence (`deliverables/submission/VENUES.md`).

| Slide | Content | Speaker (proposed) |
|---|---|---|
| 1 | Title and message | Tushar |
| 2 | The one-time sealed evaluation | Tushar |
| 3 | Rule vs learned comparators | Tushar |
| 4 | Trade-offs and limits | Mayank |
| 5 | Contribution and publication path | Mayank |

**Needs confirmation.**

- The presenter split.
- The meeting date and format.
- Any venue or author decisions to add to slide 5.
