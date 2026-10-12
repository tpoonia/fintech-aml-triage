---
title: "Professor Q&A sheet — October 13, 2026 (Implementation progress)"
subtitle: "Phases 1–3B, completed October 6–7, 2026"
---

**1. Is the project still running?**
No. Every experimental phase was completed by Oct 8, 2026, including the one-time sealed held-out test. This meeting covers the implementation milestones (Phases 1–3B); later meetings cover the rest in depth.

**2. Why group the near-duplicate rows?**
4,383 groups of rows are identical apart from the timestamp, all of them legitimate. Splitting them across partitions would leak near-copies into evaluation. After grouping, zero groups cross partitions.

**3. Why does the quantum model score lower than classical models?**
It uses only four features and a small circuit. Classical models on the same four inputs reach AUPRC 0.59–0.62 against the repaired VQC's 0.507. Only the logistic-regression gap (+0.113 [0.021, 0.214]) has an interval excluding zero. We make no quantum-advantage claim. The VQC is the noisy workload whose mitigation decisions we study.

**4. Was the encoding repair tuned on the validation data?**
No. The repair was pre-registered and selected by cross-validation on the training partition only. The validation partition was used once, to evaluate the frozen choice.

**5. What went wrong with the first encoding?**
Clipping at ±3 IQR with a [−π, π] angle range saturated most fraud values: 123 of 213 training frauds were clipped on all four features, leaving only 91 distinct fraud inputs. The wide range also caused phase aliasing. The repaired encoding (±15 IQR, [−π/4, π/4]) keeps 212 distinct.

**6. Why AUPRC, and why did noise barely change it?**
Fraud prevalence is 0.17%, so AUPRC is the informative ranking metric. Noise mostly contracts scores toward 0.5. That leaves discrimination almost unchanged (ΔAUPRC ≤ 0.003; every interval contains 0) but damages calibration: Brier 0.0093 → 0.121 under combined-high noise.

**7. What comes next?**
In-depth presentation of the completed noise and mitigation results (Oct 27), the policy study (Nov 10) and the final sealed-test findings (Nov 24), plus manuscript review.

**Sources:** `ulb_v1_dataset_summary.csv`, `ulb_v1_phase1_metadata.json`, `phase2_classical_metrics.csv`, `p3ar_validation_comparison.csv`, `p3ar_encoding_diagnostics.csv`, `p3b_exact_metrics.csv`.
