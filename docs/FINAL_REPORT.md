# Q-TRACE: Cost-Aware Selective Quantum Error Mitigation for Noisy Variational Quantum Fraud Classifiers

## Final research report

| | |
|---|---|
| **Project** | Graduate AI capstone. Mitigation decision study with a pre-registered test of a learned controller. |
| **Team** | Mayank Kumar Pokhriyal (PI), Tushar Poonia. Engineering and analysis assisted by Claude Code (see `ai_tool_log.md`). |
| **Status** | FINAL (2026-10-08). The research is complete; the sealed test was opened once under a pre-registered protocol. |
| **Evidence standard** | Every number cites a committed table in `results/tables/` or a section of `docs/EXPERIMENT_PROTOCOL.md`. Every experiment was pre-registered and pushed before its outcomes. Simulation only. **No quantum-advantage claim.** |

---

## 1. Summary

**Question.** When should a noisy quantum fraud classifier spend extra quantum resources on error mitigation, and is *learning* that decision better than a simple observable rule?

**What we did.**
- **Models and data:** 64 independently trained 4-qubit VQC fraud classifiers on the European credit-card dataset.
- **Noise:** simulated noise both as categorical families and as continuous joint readout, depolarizing and thermal noise, with shot budgets of 256–4,096.
- **Actions:** none, readout mitigation, ZNE, both, or 3× extra shots.
- **Choice rule:** each context's cost-aware best action was found from its counterfactual outcomes.
- **Process:** every phase was pre-registered before its outcomes, and a sealed test of 16 unseen models was opened once.

**What we found.**
1. **Noise damages calibration, not discrimination.** Under the studied noise, VQC discrimination (AUPRC/AUROC) and the top-ranked frauds are essentially unchanged while Brier and threshold decisions degrade; scores within the legitimate bulk are reordered (Kendall τ 0.96–0.99).
2. **Mitigation repairs calibration only.** It restores calibration and fixed-threshold decisions but does not improve AUPRC beyond a shot-matched baseline. Extra shots never substitute for mitigation.
3. **The best action is set by which noise is present.** None → no mitigation; readout → readout mitigation; gate → ZNE; both → combined. In our continuous joint-noise design (16 of 17 gate settings carry gate noise) the choice reduces almost entirely to "is gate noise present?"
4. **A two-threshold probe rule matches the Oracle on unseen models.** The rule reads cheap label-free probes. Material mistakes: 2.0% under continuous noise, 8.8% under categorical noise. It sits within 0.03% of the Oracle's Brier at 0.6% more shots.
5. **Learned controllers are unnecessary.** Two pre-registered gates (G3B, G3C) found no material residual (a small but statistically significant structure association, driven by the mean-Z readout). On held-out models, fixed learned comparators at best tie the rule on material failure and generalize worse to an unseen readout type; §14 lists the statistical caveats.

**Answer.** *Use the simple rule; a learned controller (Q-TRACE) is unnecessary in this setting.* This is simulation evidence on 4-qubit circuits, with no quantum-advantage claim (§16).

## 2. Motivation

Near-term quantum classifiers run on noisy hardware. Error-mitigation techniques can partly undo noise:
- **readout mitigation**, which inverts measurement confusion;
- **zero-noise extrapolation (ZNE)**, which amplifies gate noise and extrapolates back to zero.

Both cost extra circuits, shots and two-qubit-gate exposure. For a deployed classifier, the operational question is therefore not "does mitigation work?" but **"when is it worth paying for, and which technique?"**

Q-TRACE (originally *Quantum Trust-Aware Cost-Effective* control) set out to learn that decision from cheap, label-free observables, per execution context. It was evaluated against fixed policies (never, always) and a simple rule. A finding that a simple rule matches the learned controller was registered in advance as a reportable result.

## 3. Research questions

| | Question |
|---|---|
| **Original** | Can a learned controller, using only deployable observables, choose per-context mitigation actions for a noisy VQC fraud classifier that beat fixed policies on a reliability–cost trade-off? |
| **Final** (PI brief, 2026-10-08) | When should a noisy QML fraud model spend additional quantum resources on mitigation, and is learning that decision actually better than a simple observable rule? |

Supporting questions, answered in order:
1. What does simulated noise at the [RR] anchor severities do to a VQC fraud classifier? (§8)
2. What do the mitigation actions repair, at what cost? (§9)
3. Across many independently trained models, is the best action context-dependent in a way a cheap rule cannot capture? (§11, §12)

## 4. Related work

*References are agent-checked against publisher, arXiv or Crossref records (`docs/LITERATURE.md`, E61); team confirmation is pending before external submission.*

**Error mitigation.** Readout mitigation inverts a calibrated confusion model (Bravyi et al., PRA 2021; Maciejewski et al., Quantum 2020). ZNE extrapolates from amplified noise (Temme et al., PRL 2017; Kandala et al., Nature 2019; Kim et al., Nat. Phys. 2023). Digital ZNE uses unitary folding (Giurgica-Tiron et al., QCE 2020). Cai et al. (RMP 2023) review the field. Resource-normalized evaluation finds mitigation beneficial on average but platform-dependent (Russo et al., TQE 2023), and at a matched online shot budget unconstrained ZNE can be worse than the raw estimate (Zhang et al., 2026). We use a shot-matched comparator throughout.

**Learning and QEM.** Learning-based QEM learns *the mitigation map itself* (Strikis et al., PRX Quantum 2021; Liao et al., Nat. Mach. Intell. 2024).

**Choosing which mitigation to run** is recent:
- contextual bandits for mitigation intensity (Szachara et al., 2026) and for ZNE scale factors on VQC classifiers (Rahman & Nguyen, IEEE JSAC 2026);
- utility-driven orchestration among none, ZNE, PEC, CDR and readout mitigation for quantum reinforcement learning (Majid et al., 2026);
- fuzzy selection among none, dynamical decoupling and ZNE (Rao et al., 2026);
- a decision-aware analysis in which, in the evaluated regimes, selection often retains the raw estimate (Scavino, 2026).

The three learned selectors (Szachara et al.; Rahman & Nguyen; Majid et al.) condition on information that is label-dependent or unavailable at deployment (ideal-state fidelity, simulator noise parameters, task loss, accuracy or reward) and report gains mainly over static mitigation choices; to our knowledge none compares against a simple probe-based rule. Rao et al. use label-free circuit and hardware features with a fuzzy-logic selector, and Scavino compares decision-aware with accuracy-based selection rather than learning a policy.

**QML for fraud.** VQC and quantum-kernel studies on the same dataset report classical models ahead (Dinuț et al., Electronics 2026). El Alami et al. (2026) compare QML architectures on the same dataset and on BankSim, and Tudisco et al. (IEEE Access 2024) report better recall than classical baselines on private bank data.

**Our contribution, to our knowledge:**
- extra shots and combined mitigation in the same action space;
- context restricted to label-free probes; true noise parameters are never policy inputs (a feature-registry guard with tests), and the probes estimate the noise by design;
- a pre-registered, held-out test of learning against a simple rule. Its answer is negative.

## 5. Data and leakage-safe design

**Dataset.** ULB / Kaggle European credit-card fraud data: 284,807 transactions, 492 frauds. Features are `V1`–`V28` (a PCA released by the dataset creators), `Time` and `Amount`.

**Deduplication (Phase 1).**
- 773 exact-duplicate groups were reduced to one row each, leaving **283,726 rows with 473 frauds (0.167%)**.
- No duplicate group had conflicting labels.
- 4,383 near-duplicate groups (identical except for `Time`; all legitimate) are kept but **never split across partitions**.

**Partitions** (group-aware, stratified; verified disjoint, with no feature-group crossing any boundary):

| Partition | Rows | Frauds | Used for |
|---|---:|---:|---|
| `vqc_train` | 127,677 | 213 | fitting every VQC and every preprocessing parameter |
| `vqc_val` | 28,372 | 47 | VQC selection, thresholds, Phase 3B–4 characterization |
| `ctrl_train` | 42,559 | 71 | controller-training contexts |
| `ctrl_val` | 28,372 | 47 | controller-validation contexts |
| `ctrl_test` | 56,746 | 95 | **sealed** controller test (opened once, after the final protocol is frozen) |

**Leakage controls.**
- Phase-scoped access rules refuse disallowed partitions before reading.
- A feature registry marks every quantity as deployable or offline-only:
  - true simulator noise parameters, noise labels, identifiers, labels and post-action outcomes are **never** controller inputs;
  - tests prove these cannot enter a controller feature table.
- The controller-test outcomes are stored in a gitignored lockbox. Only their row count and hash are committed.
- `V1`–`V28` come from a PCA fitted by the dataset creators on all rows. This leakage is inherited and unavoidable (§16).

## 6. Classical baselines (Phase 2)

Classical models fitted on `vqc_train` and evaluated on `vqc_val` set the scale of achievable performance:

| Model and features | AUPRC [95% CI] |
|---|---|
| Random forest, all 30 features | 0.805 [0.696, 0.909] |
| Gradient boosting, the same four features the VQC later used | 0.714 |
| Logistic regression, the same four features | 0.620 |

- AUROC (0.91–0.99) barely separates models; AUPRC does, so AUPRC was the discrimination metric.
- Cross-fitting showed that tuning and reporting thresholds on one partition inflates F1 by up to 0.14. VQC thresholds tuned on `vqc_val` are therefore labelled optimistic throughout.

## 7. VQC development: an encoding failure and its repair (Phases 3A, 3A-R)

**Phase 3A.** The first 4-qubit VQC used:
- inputs V17, V14, V12, V10;
- angle encoding clipped to [−π, π];
- a ZZ feature map with RealAmplitudes (depth 1);
- parity readout;
- 8 trainable parameters, trained with COBYLA on 1,065 balanced rows.

It learned real but weak signal: **AUPRC 0.104 [0.054, 0.166], AUROC 0.766**, against 0.58–0.62 for classical models on identical inputs. Training-data diagnostics located the defect in the encoding:
- 123 of 213 training frauds were clipped on all four features, leaving only 91 distinct fraud inputs;
- the ZZ map's period-π phase aliases inputs.

**Phase 3A-R (pre-registered repair).**
- **Design:** 10 candidates (4 encodings × 2 depths, plus readout variants) compared by group-aware 5-fold cross-validation inside `vqc_train`.
- **Selected:** a wide-range encoding (E3: ±15 IQR clipping, 9.6% of fraud feature values clipped; 2 of 213 frauds on all four features) with depth 2.
- **Result on `vqc_val`:** **AUPRC 0.507 [0.363, 0.661], AUROC 0.957, Brier 0.0093**, an improvement of +0.403 [0.271, 0.546].
- Classical models on the same angles remain ahead (0.59–0.62; the gap is +0.085 to +0.113). These are point estimates; only logistic regression's gap, +0.113 [0.021, 0.214], has an interval excluding 0. There is no quantum advantage.
- This model (P3A-R) is the frozen base for Phases 3B–4.

## 8. Noise characterization (Phase 3B)

**Design.** The frozen P3A-R was simulated exactly (density matrix) under the [RR] noise-anchor grid:
- depolarizing, readout, thermal and combined noise, each at low/medium/high severity;
- plus synthetic asymmetric-readout stress profiles.

A finite-shot pilot used 1,024 shots × 20 replicates.

**Findings.**
1. **Noise at the anchor severities does not measurably reduce discrimination.**
   - For gate-noise families, |ΔAUPRC| ≤ 0.003 and |ΔAUROC| ≤ 0.0007; every interval contains 0.
   - The top-47 fraud overlap is ≥ 46/47.
2. **Noise contracts scores toward 0.5, damaging calibration and threshold decisions.**
   - Brier rises from 0.0093 (clean) to 0.121 (combined-high), and ECE from 0.083 to 0.346.
   - At the frozen threshold, precision falls from 0.53 to 0.03.
3. **Symmetric readout is an exact affine contraction.** Its ranking metrics are unchanged to 1e-16 (a negative control that passed).
4. **Under finite shots, sampling noise dominates ranking change.** The registered gate G1 was a CONDITIONAL PASS: ranking reordering in the legitimate bulk (Kendall τ 0.96–0.99), calibration and threshold distortion, but no discrimination degradation.

**Consequence.** Mitigation can mainly help calibration and fixed-threshold decisions, not discrimination (AUPRC). **Brier became the primary reliability endpoint** for everything that followed.

## 9. Mitigation characterization (Phase 4)

**Actions:**

| Action | Description | Cost |
|---|---|---|
| A0 | none | S shots |
| A1 | tensored readout mitigation from two calibration circuits, with simplex projection | about S shots |
| A2 | ZNE: global unitary folding at λ = 1, 3, 5 with linear extrapolation | 3S shots, 9× CX exposure |
| A3 | combined: readout mitigation, then ZNE | 3S shots, 9× CX exposure |

Each action was compared with a **resource-matched** baseline (RM3: no mitigation, 3S shots), over 8 conditions × 2 budgets (1,024 and 4,096 shots) × 20 replicates.

**Findings:**

1. **No mitigation action improves AUPRC** over its resource-matched baseline, in any condition or budget. Extra shots improve ranking; ZNE does not.
2. **Mitigation repairs calibration and threshold behaviour, and extra shots cannot:**

   | Condition (1,024 shots) | Brier, none | Brier after | Brier, RM3 |
   |---|---|---|---|
   | ro-sym-high, A1 | 0.053 | 0.011 | 0.053 |
   | dep-high, A2 | 0.055 | 0.038 | 0.055 |
   | comb-high, A3 | 0.122 | 0.054 | 0.121 |

   F1 at the frozen threshold recovers by up to +0.30 (1,024 shots) and +0.34 (4,096 shots).
3. **ZNE only partly undoes gate noise.** In the exact reference, it closes 13–70% of the Brier gap to clean.
4. **The best action depends on the noise family** (clean → A0, readout → A1, gate → A2, combined → A3) and is identical at both budgets.
5. **The registered gate G2 was a CONDITIONAL PASS:** benefits on Brier and F1; none on AUPRC.

## 10. Independent model pool (Phase 5A)

**Design.** A pre-registered pool of **64 VQCs**:
- 16 structures × 4 seeds;
- 3 train-only feature sets, 3 alias-safe encodings, 2 ansatz families × 2 depths, parity and mean-Z readout.

**Results.**
- All 64 trained and qualified on clean `vqc_val`, with bitwise-reproducible retraining.
- **Performance:** median AUPRC 0.235 (range 0.047–0.538), AUROC 0.91–0.96.
- **Diversity:** between-structure prediction correlations are low (Spearman median 0.24); same-structure seeds are close (0.91).
- **Freeze and split:** the pool is frozen with a hashed manifest. A **structure-level split** keeps all seeds of a structure together: 8 train / 4 validation / 4 test structures.
- **Power:** heterogeneity in mitigation benefit is well powered (minimum detectable σ_b ≈ 0.17 σ_w). A controller-versus-rule comparison on 16 held-out models is only moderately powered (≈ 0.70 SD), and that figure assumed 16 independent models; at the structure level (4 test structures), power is lower.

## 11. Phase 5B: the learned-controller hypothesis fails under categorical noise

**Design.** Each model was run on its own controller partition:
- 64 models × 8 noise conditions × 2 budgets × 20 replicates × 5 actions (A0–A3, plus A4 = extra shots as a real action), giving **102,400 action outcomes** (122,880 rows including the RM9 diagnostic);
- the test outcomes are sealed.

The controller may see only:
- 16 static model descriptors;
- 11 label-free probe features: a readout-calibration probe that A1/A3 reuse, and a fixed 32-binding gate probe at λ = 1, 3, costing ≈ 2.4 shots per inference.

The **Oracle** p\* is the cheapest action whose context-mean Brier is within 10% of the best.

**Results.**
- **The preferred action is a lookup on noise family:** clean → A0, readout → A1, gate → A2, combined → A3.
- **Extra shots (A4) are never preferred,** and the shot budget never changes the preferred action.
- **Probes track benefits closely:**
  - readout-probe error vs A1's Brier change: Spearman −0.90;
  - gate-probe contraction vs A2's: +0.85.
- **A four-category probe rule** fitted on train is wrong in **0.33% of validation replicates** (3.5% on train). The best single action is wrong 62.5% of the time.
- **Benefit magnitude is strongly model-specific** (ICC ≈ 0.98 for A1/A3), but the noise context explains 82–99% of the variance in benefit and rarely changes the winner.
- **The only systematic deviation** is one mean-Z structure that does not need readout mitigation under asymmetric readout.

**G3B = FAIL (`fixed_rule_sufficient`).** As registered, no controller was trained. **This negative result stands and is not reinterpreted.**

**Self-critique** (motivating Phase 5C). The 5B conditions were near-categorical (none, readout-only, gate-only, combined), so a cheap probe effectively reads the category. Real devices show readout and gate errors simultaneously, at continuously varying magnitudes.

## 12. Phase 5C: continuous mixed noise

**Registered design** (`PREREG_P5C.md`, `39b584a`):
- **Noise space:** readout magnitude, readout asymmetry, depolarizing and thermal noise vary **continuously and jointly**. Each lies on an anchor-severity scale that interpolates the validated anchors and never exceeds "high".
- **Design:** split-plot space-filling, 17 gate settings × 4 readout settings = 68 points.
- **Budgets and replicates:** 256 / 1,024 / 4,096 shots; 20 replicates.
- **Unchanged from 5B:** the models, structure split, probes, actions and Oracle.
- **Gate G3C:** pass to controller training only if a residual decision problem survives the best of three pre-registered simple probe rules, and that residual is model-dependent across several structures, larger than replicate noise, material in reliability or cost, and adequately supported.

**Results** (`EXPERIMENT_PROTOCOL.md` §3.13): a reported run, 1,305,600 counterfactual outcomes, every validation check passed, test outcomes sealed.

- **Joint noise removes most of the choice.** In our design, 16 of 17 gate settings carry gate noise. Across all contexts, combined mitigation A3 is the cost-aware choice in 67–71% and ZNE A2 in 23–27% (71–76% and 24–29% of the contexts with gate noise). A2 wins where readout error is below about 0.003; readout-only A1 and no-mitigation A0 occur only without gate noise. Extra shots (A4) are never chosen, and the shot budget changes the choice in under 3% of cases.
- **A one-threshold probe rule is near-Oracle.** R_thr uses one readout-probe and one gate-probe threshold per budget, fitted on training models. On held-out validation models:
  - its choice differs from the Oracle's in 9.6% of replicates;
  - only **2.0%** [1.6, 2.7] of its choices are material (≥ 2× the reliability tolerance, or ≥ 1× S extra shots);
  - its Brier is within **+0.3%** [−0.4, +1.0] of the Oracle at +0.02 S extra action shots per inference (excluding probes).
- **Always using combined mitigation (A3)** never breaks the tolerance, but overspends materially in 5.9% of contexts. This is exactly the 1/17 share of contexts on the gate-free setting, where A3 pays 2S more than readout mitigation; it is a property of the design, not of devices.
- **Model dependence is small.** The best model-agnostic action at the *true* noise point already matches 94% of validation contexts. The large exception is the mean-Z readout, which a one-descriptor rule absorbs.
- **Probe limitation.** The gate probe tracks depolarizing but not thermal noise (Spearman −0.12). The rule mostly needs gate *presence*, so this did not matter here.

**G3C = FAIL (`negligible_regret`).** As registered, no learned controller was trained. The learned-controller hypothesis is unsupported in both noise environments. What remains is to confirm the simple rule, and that learning adds nothing, on sealed held-out models (§14).

## 13. Final policy

Because G3C failed, no controller was trained (completion brief, negative path).

**The deployable policy is R_thr**, frozen from Phase 5C training models. For each shot budget:
1. If the readout-probe error is ≥ ~0.0037–0.0044, readout noise is present.
2. If the gate-probe contraction is ≤ ~0.97–0.98, gate noise is present.
3. Choose: both present → A3 (readout mitigation + ZNE); gate only → A2 (ZNE); readout only → A1 (readout mitigation); neither → A1 (A0 at 256 shots).

These thresholds are specific to this simulated 4-qubit setting (its circuits and probes) and would need refitting for another device or circuit family.

**Cost.** The probes cost 66·S shots per batch. The readout probe *is* the calibration that A1/A3 reuse.

## 14. Final held-out evaluation

**Protocol** (`PREREG_FINAL.md`): pushed with code before any learned comparator was fitted or any test row was read.
- **Policies:** the frozen R_thr. Comparators fixed in advance: universal policies, the 5B category rule, a readout-observable rule, and four learned comparators with fixed hyperparameters, fitted on training models only and frozen by decision fingerprints.
- **Hypotheses:** H1–H4, with frozen thresholds.
- **Unlock:** once (2026-10-08T21:28Z), through a guard that refuses unsafe states and a second unlock. The sealed contents matched their committed hashes.

**Results.** All four hypotheses are supported.

| Environment | R_thr material failure | R_thr Brier regret | Best learned comparator | Always combined |
|---|---|---|---|---|
| **5C test** (continuous joint noise; 4 unseen structures) | **0.020** [0.015, 0.026] | −0.03% | L_gbt 0.021 (paired difference, R_thr − L_gbt, −0.0005 [−0.027, 0.016]) | 0.059 |
| **5B test** (categorical noise) | **0.088** | −0.3% | L_tree3 0.118 | 0.500 |

Paired differences are R_thr − comparator (negative favours R_thr). Brier regret is measured against the Oracle's action, which may sit up to 10% above the best Brier, so an overspending policy can have negative regret.

- **R_thr's cost:** 0.6% more shots than the Oracle (including probe shots) and 3.4% fewer than always-combined mitigation (5C test). Always-combined's 0.059 is exactly the 1/17 gate-free design share, so H3's margin and the 3.4% saving scale with the share of gate-free batches; where gate noise is always present, both shrink towards the A2-versus-A3 choice (two calibration circuits per batch).
- **Mean-Z test structure:** it explains R_thr's higher raw failure on the test. These are non-material overspends, because readout mitigation is unnecessary for mean-Z readouts and costs only two calibration circuits. The readout-observable rule absorbs them.
- **Learned comparators on mean-Z:** they reach 5–30% *material* failure on this unseen readout type.

**Statistical caveats.**
- The test CIs come from a two-stage cluster bootstrap over only 4 structures and are likely too narrow; always-A3's is degenerate ([0.059, 0.059]). The ≈ 0.70 SD detectable effect (§10) assumed 16 independent models.
- H2 is a non-superiority result on material failure. On raw failure (any disagreement with the Oracle), L_gbt, L_tree3 and R_obs were significantly better than R_thr on the 5C test (paired R_thr − comparator: L_gbt 0.154 [0.028, 0.391]; L_tree3 0.133 [0.003, 0.387]; R_obs 0.130 [0.001, 0.384]); R_thr's extra disagreements were not material.
- The learned comparators were much worse on validation than on test (material failure: L_gbt 0.107 → 0.021; L_tree3 0.175 → 0.026), so "the test reproduces validation" holds for R_thr only (0.020 on both).
- On the 5B test, the 5B category rule R_cat (0.064) was significantly better than R_thr (0.088): paired R_thr − R_cat 0.024 [0.011, 0.037].

## 15. Robustness and ablations

**Registered sensitivity analyses** (Phase 5C):

| Factor | Effect |
|---|---|
| Shot budget | changes the best action in < 3% of cases |
| Tolerance ε = 0.05–0.20 | the rule's material failure stays at 2–7.5% |
| Extra-shots action | never preferred at the registered ε = 0.10; ≤ 0.03% of contexts at ε = 0.20 |

**Exploratory ablations on validation only** (`ablation_probes.csv`, `ablation_probe_cost.csv`; the test was never reused):

| Variant | 5C val material failure | 5B val material failure |
|---|---|---|
| R_thr (both probes) | 2.0% | 9.4% |
| Gate probe only | 1.8% | 9.4% |
| Readout probe only | 6.2% | 50% |
| No probe (fixed per budget) | 5.9% | 50% |

- **The gate probe carries the material value.** The readout probe only chooses between A2 and A3, which differ by two calibration circuits.
- **Probe-cost break-even.** Probing pays off only for batches larger than ≈ 645–685 transactions under continuous noise (budget-dependent; ≈ 80 under categorical noise). Below that, always-combined mitigation is cheaper. The 66·S probe cost includes the 2 calibration circuits that always-A3 already pays, so the break-even is conservative. Like H3, it scales with the share of gate-free batches in the design.
- **Learned-model complexity** (Phase 7 and final test): more flexible learners (gradient boosting) do not beat the two-threshold rule on material failure, and they generalize worse to an unseen readout observable.

## 16. Limitations

- **Simulation only.**
  - All noise is simulated with Qiskit Aer density matrices.
  - Asymmetric readout profiles are **synthetic stress tests**, not device calibration data.
  - No hardware experiment was run. Simulation-to-hardware generalization is future work.
- **Scale.** 4 qubits; shallow circuits (15–18 CX, noisy depth 17–21); one dataset.
- **Data.** One public, heavily imbalanced dataset (0.17% fraud). Inherited PCA leakage in `V1`–`V28`. The validation and controller partitions hold only 47–95 frauds, so discrimination intervals are wide.
- **Models.** VQCs are weaker than classical models on identical inputs. **There is no quantum advantage, and none is claimed.** The 64-model pool varies structure and seed within one family of circuits.
- **Noise models.** Depolarizing, thermal relaxation and readout confusion are applied gate by gate, with no crosstalk, leakage, drift or coherent errors. Mitigation is restricted to readout inversion and linear ZNE (no PEC, CDR or dynamical decoupling).
- **Thresholds.** Per-model thresholds were tuned on clean `vqc_val` and are optimistic. Threshold metrics are secondary.
- **Statistical units.** Models and structures are the independent units. The held-out test has 16 models from 4 structures, so model-level comparisons are only moderately powered, structure-level power is low, and cluster-bootstrap intervals over 4 structures are likely too narrow.
- **Design dependence.** The advantage over always-combined mitigation and the probing break-even scale with the share of gate-free batches (1 of 17 gate settings in the continuous design).
- **Failed hypotheses** are reported as results:
  - noise did not degrade discrimination (G1 conditional);
  - mitigation did not improve AUPRC (H4.3, G2 conditional);
  - the learned-controller hypothesis failed under categorical noise (G3B).

## 17. Conclusions

1. **Noise.** For 4-qubit VQC fraud classifiers under simulated hardware-like noise, noise primarily damages calibration and threshold decisions, not discrimination (AUPRC/AUROC) or the top-ranked frauds.
2. **Mitigation.** It is valuable for calibrated decisions (Brier, F1 at a fixed threshold) and worthless for discrimination (AUPRC). Extra shots are not a substitute.
3. **Choosing what to run.** The choice is governed by which noise is present. In our continuous joint-noise design (16 of 17 gate settings carry gate noise) it collapses to one question: is gate noise present (then pay 3× for ZNE-based mitigation) or not?
4. **The deployable answer is a two-threshold probe rule.** It is near-Oracle on unseen models in two noise environments.
5. **Learning adds nothing measurable on the registered endpoint.** The learned-controller hypothesis failed two registered gates, and fixed learned comparators did not beat the rule on material failure in the sealed test; no controller was trained.

**Answer to the capstone question:** *spend resources on mitigation when the probes detect noise that biases calibration, choosing the technique by noise type with a simple rule. Learning that decision is not better than the rule.*

## 18. Future work

- **Hardware validation.** Run the same probe and action protocol on a real device, where readout asymmetry, drift and crosstalk are real.
- **Richer mitigation.** Probabilistic error cancellation, Clifford data regression or dynamical decoupling, with cost-aware selection.
- **Larger circuits and other datasets,** where noise may degrade discrimination as well as calibration.
- **Decision endpoints** that weight threshold errors by fraud-operations cost.

## Appendix A: Reproducibility

See `docs/REPRODUCIBILITY.md`, the per-phase pre-registrations in `docs/`, and the decision log `docs/DECISIONS.md`.
