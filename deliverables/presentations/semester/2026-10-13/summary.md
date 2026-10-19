---
title: "Q-TRACE · October 13, 2026 · Implementation progress"
subtitle: "One-page summary · meeting 3 of 7 · reports Phases 1–3B, completed October 6–7, 2026"
---

**Chronology.** These milestones were completed on Oct 6–7, 2026. The full study, including the one-time sealed test, was completed on Oct 8. Nothing is still running; later meetings present the remaining results in depth.

**Purpose.** To show how the project went from raw data to a working, frozen quantum classifier, and what the first noise characterization found.

**Key messages and numbers.**

| Milestone | Result | Source |
|---|---|---|
| Data (Phase 1) | 284,807 → 283,726 rows after deduplication; 473 frauds (0.17%); 5 group-aware partitions; 0 groups cross partitions | `ulb_v1_*` |
| Baselines (Phase 2) | AUPRC 0.805 (random forest, 30 features); 0.59–0.62 on the VQC's 4 inputs | `phase2_classical_metrics.csv`, `p3ar_validation_comparison.csv` |
| Frozen VQC (3A-R) | 4 qubits; ZZ feature map + RealAmplitudes (2 layers); parity readout; 12 parameters; 18 CX | `configs/repair/p3ar_v1.yaml`, `p5a_pool_metrics.csv` |
| Encoding repair | AUPRC 0.104 → 0.507 (AUROC 0.957); distinct fraud inputs 91 → 212 of 213 | `p3ar_*` |
| First noise result (3B) | ΔAUPRC ≤ 0.003; Brier 0.0093 → 0.121; precision 0.53 → 0.03 (combined-high) | `p3b_exact_metrics.csv` |

**Takeaways.**

- The data pipeline is leakage-safe.
- Classical models set the bar, so there is no quantum-advantage claim.
- A pre-registered, training-only repair made the VQC work.
- Noise damages calibration, not discrimination.

| Slide | Content | Speaker |
|---|---|---|
| 1 | Title and chronology | Mayank |
| 2 | Leakage-safe data and baselines | Mayank |
| 3 | The frozen quantum classifier | Mayank |
| 4 | Encoding repair | Tushar |
| 5 | First noise result and project status | Tushar |

**Speaker split.** Mayank takes the first half and Tushar the second, the same pattern as the committed Oct 13 script. The team should confirm it.

**Related file.** An earlier 8-slide whole-study version, `deliverables/presentations/Q-TRACE_Oct13_Progress.pptx`, is kept unchanged. Choose one deck for the meeting.

**Needs confirmation.**

- The meeting date, slot length and upload format.
- Whether the 5-slide milestone version or the earlier 8-slide whole-study version fits the session.
