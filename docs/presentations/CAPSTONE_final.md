# Q-TRACE: final capstone presentation

| | |
|---|---|
| **Audience** | Capstone committee, instructors and peers |
| **Length** | 15 slides, about 18 minutes plus questions |
| **Evidence** | Every number cites a committed table or figure in `results/`. References are agent-checked; team confirmation is pending. |
| **Story** | We set out to show a learned controller beats fixed policies. Pre-registered experiments showed a simple probe rule is enough, and a sealed held-out test confirmed it. |

---

## 1. Title

**When is quantum error mitigation worth paying for? Selective mitigation for noisy quantum fraud classifiers.**

Mayank Kumar Pokhriyal, Tushar Poonia. Graduate AI capstone, October 2026.

> **Speaker notes:** One sentence: we asked whether a learned controller should decide when to run quantum error mitigation; the answer, tested rigorously, is no — a two-threshold rule does it.

---

## 2. The decision problem

- **Error mitigation costs resources.**
  - **Readout mitigation** inverts measurement errors; it is cheap.
  - **Zero-noise extrapolation (ZNE)** amplifies gate noise and extrapolates back; it costs 3× the shots and 9× the two-qubit-gate exposure.
- **The question per batch:** spend nothing, run readout mitigation, run ZNE, run both, or just buy more shots?
- **The original hypothesis:** a *learned* controller using only cheap observable signals makes this choice better than fixed policies.

> **Speaker notes:** The application is fraud scoring, where calibrated probabilities and fixed alert thresholds matter.

---

## 3. Setup and safeguards

- **Data:** European credit-card fraud data (283,726 rows after deduplication; 0.17% fraud), with group-aware partitions that keep controller data disjoint from model training.
- **Models:** 4-qubit VQCs. The first encoding aliased and saturated (AUPRC 0.10); a pre-registered repair reached **0.51 AUPRC / 0.96 AUROC**. Classical models on the same inputs still do better (0.59–0.62; point estimates, and only logistic regression's gap is interval-supported), so **we claim no quantum advantage**.
- **Process:**
  - every phase pre-registered and pushed before its outcomes;
  - true noise parameters never enter controller inputs (a feature-registry guard with tests); the probes estimate the noise by design;
  - the controller-test split sealed until the end.

**Figures:** `p3ar_pr_comparison.png`

---

## 4. Finding 1: noise breaks calibration, not discrimination

- Simulated depolarizing, thermal and readout noise at standard low/medium/high anchors.
- **AUPRC moves by ≤ 0.003.** **Brier rises from 0.009 to 0.121**, and precision at the alert threshold falls from 0.53 to 0.03.
- Scores contract toward 0.5: discrimination (AUPRC/AUROC) and the top-ranked frauds survive, the probabilities don't. Scores in the legitimate bulk are reordered (Kendall τ 0.96–0.99).

**Figures:** `p3b_c_clean_vs_noisy.png`, `p3b_d_distribution_calibration.png`

---

## 5. Finding 2: mitigation repairs calibration, and extra shots cannot

| Noise (1,024 shots) | Brier, none | After mitigation | With 3× shots |
|---|---|---|---|
| readout | 0.053 | **0.011** (readout mitigation) | 0.053 |
| gate | 0.055 | **0.038** (ZNE) | 0.055 |
| combined | 0.122 | **0.054** (both) | 0.121 |

- **No action improves AUPRC** over a shot-matched baseline.
- **The best action depends on the noise type.**

**Figures:** `p4_b_calibration.png`, `p4_a_auprc.png`

---

## 6. 64 independent models

- **Pool:** 16 structures × 4 seeds, covering feature sets, encodings, ansatz families and depths, and parity versus mean-Z readout.
- **All 64 qualified.** Median AUPRC 0.24 (range 0.05–0.54).
- **Held out:** the split is by *structure*. 4 structures were sealed for the final test.

**Figures:** `p5a_a_auprc.png`, `p5a_b_correlation.png`

---

## 7. Counterfactual benchmark: every action for every context

- **Grid:** every model × noise context × shot budget × 20 replicates × 5 actions, each model on its own controller partition.
- **What the controller sees:** 16 static descriptors and 11 cheap label-free probes (readout calibration plus a fixed 32-binding gate probe). Probe cost: 66·S shots per batch.
- **Oracle:** the cheapest action within 10% of the best Brier. A *mistake* (failure) is any disagreement with the Oracle; it is *material* when its Brier is beyond 2× that tolerance, or it costs ≥ 1 extra shot-set (S) per inference.
- **Brier regret** is measured against the Oracle's action, which may sit up to 10% above the best Brier, so a policy that overspends can have *negative* regret.

---

## 8. Test 1 (Phase 5B): categorical noise, G3B = FAIL

- The best action is a **lookup on noise family**: none → none, readout → readout mitigation, gate → ZNE, both → both.
- A **four-cell probe rule** is correct in **99.7%** of validation cases.
- Extra shots are never best. Mitigation benefit varies by model (ICC 0.98 for the readout-based actions A1/A3), but the winner doesn't change.
- **The registered gate failed, so no controller was trained.**

**Figures:** `p5b_a_preferred_heatmap.png`

---

## 9. Self-critique, and the response

- **Was 5B too easy?** Its noise came in clean categories. Real devices have readout *and* gate noise, continuously.
- **Phase 5C (pre-registered):** 68 continuous joint noise points (split-plot Latin hypercube within the validated ranges), 256–4,096 shots.
- A stricter gate: the residual must be material, model-dependent across several structures, and beyond replicate noise.

**Figures:** `p5c_a_design.png`

---

## 10. Test 2 (Phase 5C): continuous joint noise, G3C = FAIL

- Joint noise **removes** most of the choice: combined mitigation in 67–71% of contexts, ZNE in 23–27%, extra shots never. The budget matters in < 3% of cases.
- The best simple rule (**two probe thresholds per budget**): material mistakes in **2.0%** of validation cases, Brier within 0.3% of the Oracle.
- **The gate failed again: no controller.**

**Figures:** `p5c_b_preferred_map.png`, `p5c_c_policies.png`

---

## 11. Test 3: the sealed held-out evaluation (opened once)

| Policy | Material mistakes, continuous noise | Brier vs Oracle | Shots vs Oracle | Material mistakes, categorical noise |
|---|---|---|---|---|
| **Simple rule (R_thr)** | **2.0%** | **−0.03%** | **+0.6%** | **8.8%** |
| Gradient boosting, L_gbt (best learned on continuous test) | 2.1% | +0.3% | +0.9% | 36% |
| Depth-3 tree, L_tree3 (best learned on categorical test) | 2.6% | +0.7% | +0.8% | 11.8% |
| Always combined | 5.9% | −1.4% | +4.1% | 50% |
| Never mitigate | 96% | +93% | −65% | 81% |

All four pre-registered hypotheses are supported: the rule is near-Oracle, learning adds nothing on material mistakes (a non-superiority test), the rule beats fixed policies, and it transfers across noise types.

- "Shots vs Oracle" includes probe shots; the cost regret (+0.02 S) and the overspend test count action shots only. Paired differences are R_thr − comparator (negative favours the rule).
- Always combined's 5.9% is exactly the 1/17 share of gate-free contexts in the design, so the rule's margin and its 3.4% shot saving scale with the share of gate-free batches.
- **Caveats:** the intervals rest on only 4 held-out structures and are likely too narrow. On *any* disagreement with the Oracle, L_gbt, L_tree3 and R_obs were significantly closer to the Oracle than R_thr (paired R_thr − L_gbt 0.154 [0.028, 0.391]), but the rule's extra disagreements were not material. The learned comparators were much worse on validation than on test (L_gbt 10.7% → 2.1%; L_tree3 17.5% → 2.6%); R_thr was 2.0% on both. On categorical noise, the 5B category rule (6.4%) beat R_thr (8.8%) significantly.

**Figures:** `final_a_policies.png`

---

## 12. Why learning doesn't help

- **Bias, not variance:** mitigation fixes a calibration bias, so the shot budget is irrelevant.
- **In our continuous joint-noise design (16 of 17 gate settings carry gate noise)**, the main decision is "ZNE or not", and the **gate probe alone** recovers the rule's performance (on material mistakes).
- **Model differences change magnitudes, not the ranking of actions.** The one exception is the readout type: learned models trained on one mean-Z structure fail on a new one (up to 30% material mistakes); the rule doesn't.

**Figures:** `final_b_structures.png`

---

## 13. Practical recipe

1. Run the gate probe. If gate noise is present, use **ZNE**, plus readout mitigation when readout error is above about 0.4%.
2. Without gate noise, use **readout mitigation** alone.
3. **Never** buy extra shots to fix calibration.
4. For batches under ≈ 645–685 transactions (budget-dependent; ≈ 80 under categorical noise), skip probing and always use combined mitigation. The 66·S probe cost includes the 2 calibration circuits always-combined already pays, and this break-even scales with the share of gate-free batches in the design.

The thresholds are specific to this simulated 4-qubit setting and would need refitting for another device or circuit family.

---

## 14. Limitations

- **Simulation only:** no hardware run, and the asymmetric readout is synthetic.
- **Narrow scope:** 4 qubits, one dataset, VQCs weaker than classical models, **no quantum advantage**.
- **Methods:** two mitigation techniques only; the gate probe is insensitive to thermal noise; per-model thresholds are optimistic.
- **Power:** the held-out test spans 4 structures, so cluster-bootstrap intervals are likely too narrow; the ≈ 0.70 SD detectable effect assumed 16 independent models.

---

## 15. Conclusion

- **Selective quantum error mitigation here is a simple rule, not a learning problem.**
- **Negative results were pre-registered and are reported as results:**
  - noise did not degrade discrimination (AUPRC/AUROC) or the top-ranked frauds;
  - mitigation did not improve AUPRC;
  - the learned-controller hypothesis failed two registered gates, and fixed learned comparators did not beat the rule on the sealed test; no controller was trained.
- **Next:** hardware validation, richer mitigation (PEC, CDR), larger circuits.

> **Speaker notes:** Close on the method: two registered gates and one sealed test turned "Q-TRACE wins" into a well-supported "the rule wins", which is the more useful result for practitioners.
