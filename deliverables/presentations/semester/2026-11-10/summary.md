---
title: "Q-TRACE · November 10, 2026 · Policy selection"
subtitle: "One-page summary · meeting 5 of 7 · Phases 5A–5C, completed October 7–8, 2026"
---

**Chronology.** Completed on Oct 7–8, 2026; the sealed test followed on Oct 8 and is the Nov 24 topic.

**Purpose.** To explain why a learned controller was originally proposed, how the 64-model benchmark and label-free probes were built, and why a simple rule emerged instead.

**Key numbers.**

| Item | Result | Source |
|---|---|---|
| Model pool | 64 VQCs = 16 structures × 4 seeds; median AUPRC 0.235 (0.047–0.538); split 8/4/4 | `p5a_pool_metrics.csv`, `p5b_split.csv` |
| Probes | 66 circuits per batch; readout probe ρ = 0.999; gate probe ρ = −0.89 (depolarizing), −0.12 (thermal) | `p5c_probe_validity.csv` |
| Phase 5B (categorical) | 4-cell rule wrong in 0.33% of validation cases (best single action wrong in 62.5%) | `p5b_metadata.json` |
| Phase 5C (continuous) | combined mitigation 67–71%, ZNE 23–27% of contexts; budget changes the choice < 3%; 3× shots never chosen | `p5c_metadata.json`, `p5c_budget_effect.csv` |
| Best rule (validation) | 9.6% disagreement, 2.0% [1.6, 2.7] material, Brier regret +0.3% | `p5c_policy_eval.csv` |
| Gates | G3B fail, G3C fail; residual detectable (MI 0.08 / 0.04 nats) but not material | `p5b_metadata.json`, `p5c_metadata.json` |

**The rule.**

- If the gate probe detects gate noise, use ZNE, and add readout mitigation when the readout probe exceeds about 0.4%.
- Otherwise use readout mitigation alone. At 256 shots, use no mitigation if the readout probe is also below its threshold.

**Takeaways.**

- As registered, no learned controller was trained.
- In our design, 16 of 17 gate settings carry gate noise, so the material decision is whether gate noise is present.

| Slide | Content | Speaker (proposed) |
|---|---|---|
| 1 | Title and message | Mayank |
| 2 | The decision we proposed to learn | Mayank |
| 3 | 64 models and two probes | Mayank |
| 4 | Categorical, then continuous noise | Tushar |
| 5 | Gates failed; a simple rule emerged | Tushar |

**Needs confirmation.**

- The presenter split.
- The meeting date and format: supplied by the team, not on a public course calendar.
