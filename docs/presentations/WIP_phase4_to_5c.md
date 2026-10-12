# Q-TRACE: work-in-progress deck (Phase 4 → Phase 5C)

| | |
|---|---|
| **Audience** | Capstone instructors and peers (WIP review) |
| **Length** | 12 slides, about 12 minutes |
| **Status** | Built from measured results through Phase 5C (G3C = FAIL, 2026-10-08). |
| **Sources** | Every number cites a committed table or figure in `results/`. Nothing here is cited from unverified literature (`docs/LITERATURE.md` rule 4). |

---

## Slide 1: When should a noisy quantum fraud classifier pay for error mitigation?

- **Q-TRACE:** cost-aware, *selective* quantum error mitigation for noisy variational quantum classifiers (VQCs) on credit-card fraud data.
- **Original hypothesis:** a learned controller, given only cheap observable signals, picks the right mitigation action per context better than fixed policies.
- **Today:** what mitigation actually does (Phase 4), a 64-model pool (5A), a pre-registered test of the hypothesis that **failed** (5B), and the follow-up study now running (5C).

> **Speaker notes:** Frame this as a decision problem: mitigation costs shots and circuits, so the question is when it is worth it, not whether mitigation "works". Say up front that the headline result so far is negative and that it was pre-registered.

---

## Slide 2: Pipeline and safeguards

- **Data:** ULB credit-card fraud, deduplicated (283,726 rows, 0.167% fraud). Group-aware partitions: VQC train/val, plus controller train/val/test that no model ever trained on.
- **Model:** 4-qubit VQC (ZZ feature map + RealAmplitudes). The Phase 3A encoding saturated and aliased (AUPRC 0.104); the pre-registered repair (E3 encoding) reached **0.507 AUPRC / 0.957 AUROC** on `vqc_val`. Classical models on the same inputs still do better (0.59–0.62).
- **Process:** every phase is pre-registered and pushed before outcomes; true noise parameters are never controller inputs; the controller test split is sealed.

**Figures:** `p3ar_pr_comparison.png`

> **Speaker notes:** No quantum-advantage claim. The VQC is a working weak-to-moderate classifier, which is enough to study mitigation decisions.

---

## Slide 3: Noise damages calibration, not discrimination (Phase 3B)

- At the [RR] low/medium/high anchors, exact noise changes AUPRC by at most 0.003 for gate-noise families. No condition degrades discrimination.
- Noise **contracts scores toward 0.5**. Brier rises from 0.0093 to 0.121 under comb-high, and at the frozen threshold precision falls from 0.53 to 0.03.
- Symmetric readout noise is an exact affine contraction: a negative control that passes to 1e-16.

**Figures:** `p3b_c_clean_vs_noisy.png`, `p3b_d_distribution_calibration.png`

> **Speaker notes:** This reframed the project. If noise does not hurt discrimination (AUPRC/AUROC) or the top-ranked frauds (it only reorders scores in the legitimate bulk, Kendall τ 0.96–0.99), mitigation can only help calibration and fixed-threshold decisions. That is why Brier became the primary endpoint.

---

## Slide 4: Phase 4, finding 1: mitigation does not improve fraud ranking

- Each action is compared with a **resource-matched** baseline: the same shot budget spent on extra shots (RM3).
- **No AUPRC benefit** for any action in any condition, at 1,024 or 4,096 shots.
- Extra shots *do* help ranking. Under comb-high at 1,024 shots, AUPRC rises from 0.485 to 0.506 and Spearman from 0.61 to 0.78. ZNE does not.
- **Registered gate G2:** CONDITIONAL PASS (benefits on Brier and F1, none on AUPRC).

**Figures:** `p4_a_auprc.png`

> **Speaker notes:** This matches the pre-registered theory: a uniform contraction cannot change rankings, so undoing it cannot either.

---

## Slide 5: Phase 4, finding 2: mitigation repairs calibration, and extra shots cannot

| Condition (1,024 shots) | Brier: None | Best action | Brier after | Extra shots (RM3) |
|---|---|---|---|---|
| readout (ro-sym-high) | 0.053 | readout mitigation (A1) | 0.011 | 0.053 |
| gate (dep-high) | 0.055 | ZNE (A2) | 0.038 | 0.055 |
| combined (comb-high) | 0.122 | combined (A3) | 0.054 | 0.121 |

- F1 at the frozen threshold recovers by up to +0.30 (comb-high: 0.03 → 0.35).
- **Cost:** ZNE needs 3× the shots and 9× the CX exposure; readout calibration is about 2 circuits per batch.

**Figures:** `p4_b_calibration.png`, `p4_c_cost.png` (`p4_summary.csv`, `p4_resource_matched.csv`)

> **Speaker notes:** Bias versus variance. Extra shots reduce variance; mitigation removes bias. Brier here is dominated by bias.

---

## Slide 6: Phase 4, finding 3: the best action depends on the noise type

| Noise | Cost-aware best action (Brier) |
|---|---|
| clean | A0 none |
| readout | A1 readout mitigation |
| gate | A2 ZNE |
| combined | A3 readout + ZNE |

- The choice is identical at both shot budgets.
- **This looked like a selective decision problem**, which motivated the learned controller.

> **Speaker notes:** A controller cannot see the noise type directly, so the open question was whether it can be inferred cheaply and whether it varies across models.

---

## Slide 7: Phase 5A: 64 independently trained VQCs

- **16 structures × 4 seeds:** 3 feature sets, 3 alias-safe encodings, 2 ansatz families × 2 depths, parity and mean-Z readout.
- **All 64 qualified** on clean `vqc_val`. Median AUPRC 0.235 (range 0.047–0.538); AUROC 0.91–0.96.
- **Diversity is real:** between-structure prediction Spearman median 0.24; within-structure 0.91.
- **Frozen and hashed,** with a pre-registered structure-level split (8 / 4 / 4 structures).

**Figures:** `p5a_a_auprc.png`, `p5a_b_correlation.png`

> **Speaker notes:** Models are the independent unit for any controller claim, so a single model was not enough. The pool is weaker than the hand-picked P3A-R model, but varied.

---

## Slide 8: Phase 5B: a counterfactual dataset and a pre-registered gate

- **Grid:** 64 models × 8 noise conditions × 2 budgets × 20 replicates × 5 actions (A0–A3 plus extra shots A4) = **102,400 action outcomes** (122,880 rows including the RM9 diagnostic), each model on its own controller partition. Test outcomes are sealed.
- **Observable context only:** 16 static descriptors plus 11 cheap label-free probes (readout calibration and a fixed gate probe; about 2.4 shots per inference).
- **Oracle p\*:** the cheapest action within 10% of the best Brier.
- **G3B** asked whether there is a decision problem a learned controller could solve that a fixed probe rule cannot.

**Figures:** `p5b_d_probes_vs_benefit.png`

> **Speaker notes:** The probes really work. Readout-probe error tracks A1's benefit (Spearman −0.90), and gate-probe contraction tracks A2's (+0.85).

---

## Slide 9: Phase 5B result: G3B = FAIL

- **The best action is a lookup on noise type:** clean → A0, readout → A1, gate → A2, combined → A3.
- **A four-cell probe rule** fitted on train picks the Oracle action in **99.7% of validation replicates.** The best single action is wrong 62.5% of the time.
- **Extra shots are never best;** the shot budget never changes the choice.
- **Mitigation benefit varies strongly across models** (ICC ≈ 0.98 for A1/A3) but almost never changes *which* action wins (noise context explains 82–99% of the variance).
- **The only deviation:** one mean-Z structure that does not need readout mitigation under asymmetric readout.

**Figures:** `p5b_a_preferred_heatmap.png`, `p5b_b_delta_brier.png`

> **Speaker notes:** The registered rule makes "a fixed rule is sufficient" a FAIL condition, so we stopped: no controller was trained. This is the honest result.

---

## Slide 10: Why the learned-controller hypothesis failed

1. **The conditions were near-categorical:** none, readout-only, gate-only, combined. A cheap probe effectively reads the category.
2. **The decision is bias-dominated.** Brier is not limited by shot noise, so extra shots and budget never matter.
3. **Model heterogeneity changes magnitudes, not decisions.** Benefits scale per model but keep their order.
4. **The residual is a single-structure exception** (mean-Z readout). A rule can absorb it with one static descriptor.

**Open question:** is this an artefact of categorical noise? Real devices have readout *and* gate errors at continuously varying levels.

> **Speaker notes:** A self-critique slide. Our own design may have made the problem easy, and 5C tests exactly that.

---

## Slide 11: Phase 5C: does continuous mixed noise create a real decision problem?

- **Continuous joint noise**, interpolating the validated anchors (no stronger noise): readout magnitude and asymmetry, depolarizing, thermal.
- **Split-plot space-filling design:** 17 gate settings × 4 readout settings = **68 noise points**. Shot budgets 256 / 1,024 / 4,096; 20 replicates; the same models, split, probes and actions.
- **Gate G3C** passes to controller training only if *all* of the following hold:
  1. several actions matter;
  2. the best pre-registered simple rule fails at least 15% of the time;
  3. the residual depends on the model at a fixed noise point, across several structures;
  4. it exceeds replicate noise;
  5. its errors are material (reliability or ≥ 1× shot cost);
  6. it has enough independent-model support.
- Pre-registered and pushed before any outcome (`PREREG_P5C.md`, `39b584a`). The run is about 7 h.

**Figures:** `p5c_a_design.png`

> **Speaker notes:** Stress the decision tree. **PASS** means Phase 6 trains the simplest competitive controller, then a frozen one-time test. **FAIL** means the simple rule is the answer, still confirmed once on the sealed test split.

---

## Slide 12: What comes next

- **Phase 5C results (G3C = FAIL):** in the continuous joint-noise design (16 of 17 gate settings carry gate noise), combined mitigation is almost always within tolerance (67–71% of contexts; ZNE alone 23–27%; extra shots never chosen).
  - A one-threshold probe rule makes material mistakes in **2%** of validation cases, at Oracle-level mean Brier (+0.3%, CI includes 0) and +0.02 S extra action shots (excluding probes).
  - A learned controller is therefore **not** justified, in either noise environment (figures `p5c_b_preferred_map.png`, `p5c_c_policies.png`).
- **Then, either:**
  - **(A)** Phase 6–7: train and compare a controller against Never/Always policies, the best simple rule, a decision tree, logistic regression and the Oracle; **or**
  - **(B)** finalize the simple probe rule.
- **Either way:** a frozen final-test protocol, then the sealed controller test is opened **once**.
- **Deliverables:** final report, paper-style manuscript, capstone presentation.
- **Limitations:** simulation only (no hardware), 4 qubits, one dataset, synthetic asymmetric readout, optimistic thresholds tuned on `vqc_val`.

> **Speaker notes:** Either outcome answers the capstone question: when to spend quantum resources on mitigation, and whether learning that decision beats a simple observable rule.

---

## Addendum (2026-10-08): the final held-out test is done

- The sealed held-out test was opened **once**, under a pre-registered protocol.
- **The simple probe rule:** 2.0% material mistakes on unseen structures, Brier within 0.03% of the Oracle, 0.6% more shots.
- **Learned comparators:** none is meaningfully better on material mistakes. All four hypotheses are supported.
- **Conclusion:** *use the simple rule; a learned controller is unnecessary.*
- The full story is in `CAPSTONE_final.md` (figures `final_a_policies.png`, `final_b_structures.png`).
