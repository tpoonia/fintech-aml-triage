# When is quantum error mitigation worth paying for? A pre-registered study of selective mitigation for noisy variational fraud classifiers

*Manuscript draft (complete), venue-agnostic. Authors: Mayank Kumar Pokhriyal, Tushar Poonia. References are agent-checked against publisher, arXiv or Crossref records; **team confirmation is pending before submission** (`docs/LITERATURE.md`, E61).*

*The typeset, publication-formatted manuscript is `deliverables/paper/main.tex` (PDF: `deliverables/paper/Q-TRACE_manuscript.pdf`). This Markdown file is the working draft, kept consistent with it.*

---

## Abstract

Quantum error mitigation trades extra circuits and shots for less biased estimates, but a deployed quantum classifier must decide *when* that trade is worth making. We study this decision for 4-qubit variational quantum classifiers that score credit-card transactions for fraud.

**Setting.**
- **Noise:** simulated depolarizing, thermal and readout noise.
- **Actions:** none, readout mitigation, zero-noise extrapolation, both, or three times the shots.
- **Models:** 64 independently trained classifiers.
- **Choice:** in each context, the cost-aware best action is the cheapest within 10% of the best Brier score.
- **Process:** every phase is pre-registered before its outcomes.

**Characterization.** Noise mainly damages calibration and fixed-threshold decisions, not discrimination (AUPRC/AUROC) or the top-ranked frauds. Mitigation repairs calibration but never improves AUPRC beyond a shot-matched baseline, and extra shots never substitute for mitigation.

**Decision.** We test whether *learning* the per-context decision from cheap label-free probes beats a simple rule:
- Two pre-registered gates, one under categorical and one under continuous joint noise, find no material residual decision structure (a small but statistically significant structure association, driven by the mean-Z readout).
- On a sealed set of unseen model structures, opened once, a two-threshold probe rule fitted on training models makes material errors in only 2.0% of decisions under continuous joint noise (95% CI 1.5–2.6%) and 8.8% under categorical noise. It matches the Oracle's Brier within 0.03% at 0.6% more shots.
- Four pre-specified learned comparators (logistic regression, decision tree, gradient boosting) did not reduce material errors, although the best of them disagreed less often with the Oracle; they generalize worse to an unseen readout observable. The intervals rest on only four held-out structures.

**Conclusion.** In our continuous joint-noise design (16 of 17 gate settings carry gate noise) the decision reduces to whether gate noise is present. Selective mitigation in this setting is a simple observable rule, not a learning problem. The evidence is simulation-only; we make no quantum-advantage claim.

## 1. Introduction

Quantum error mitigation (QEM) trades additional quantum resources for less biased estimates [temme2017error; kandala2019error; cai2023quantum] on noisy hardware [preskill2018quantum]. Two widely used techniques are:
- **readout mitigation**, which inverts a calibrated measurement-confusion model [bravyi2021mitigating; maciejewski2020mitigation];
- **zero-noise extrapolation (ZNE)**, which amplifies gate noise, for example by pulse stretching [kim2023scalable] or unitary folding [giurgicatiron2020digital], and extrapolates to the zero-noise limit.

Both cost circuits, shots and two-qubit-gate exposure, and neither is guaranteed to help a downstream task. A deployed quantum classifier therefore faces a recurring *decision*: in the current execution context, should it spend extra resources on mitigation, on which technique, or simply on more shots?

Recent work learns such decisions with contextual bandits or orchestration policies [szachara2026gsc; rahman2026adaptive; majid2026context]. These works typically rely on information unavailable at deployment, such as labels, ideal-state fidelities or simulator noise parameters. They report gains mainly over fixed (static) mitigation choices and, in one case, over grid-search and other published ZNE variants [rahman2026adaptive]; to our knowledge none compares against a simple observable rule. A decision-aware analysis suggests that accuracy gains from mitigation need not improve downstream decisions [scavino2026decision], and a budget-aware evaluation shows that mitigation can increase error relative to the raw estimate [zhang2026worse].

We study this decision for a concrete task: variational quantum classifiers (VQCs) [havlicek2019supervised; schuld2020circuit] that score credit-card transactions for fraud [dalpozzolo2015calibrating; mlgulb2018creditcardfraud]. We ask:

> **When should a noisy quantum fraud classifier spend additional quantum resources on mitigation, and is *learning* that decision better than a simple observable rule?**

**Contributions** (each stated relative to the literature we located; see §2):
1. **Characterization of what noise and mitigation do to VQC classifiers.** For 4-qubit VQC fraud classifiers under simulated depolarizing, thermal and readout noise:
   - noise primarily damages *calibration and threshold decisions*, not discrimination (AUPRC/AUROC) or the top-ranked frauds;
   - mitigation repairs calibration but does not improve AUPRC beyond a shot-matched baseline;
   - extra shots cannot remove the bias that mitigation removes.
2. **A counterfactual mitigation benchmark** over 64 independently trained VQCs with structure-level held-out models. Every model is run under every action (none, readout mitigation, ZNE, combined, extra shots) with paired random draws. The policy context is restricted to cheap label-free probes and static descriptors, and leakage of true noise parameters is excluded by construction.
3. **A pre-registered test of the learned-controller hypothesis** against simple probe rules, in two noise environments:
   - near-categorical noise families (Phase 5B);
   - continuous joint mixed noise across shot budgets (Phase 5C).
4. **A single, frozen evaluation on sealed held-out models,** showing that a two-threshold probe rule is near-Oracle on material errors and that pre-specified learned comparators did not reduce them.

All experiments were pre-registered and pushed before their outcomes were generated. Negative results are reported as results.

## 2. Related work

**Quantum error mitigation.**
- Cai et al. [cai2023quantum] review QEM, including the practice of choosing a technique by the dominant noise source.
- ZNE was introduced with Richardson extrapolation [temme2017error], demonstrated on hardware [kandala2019error] and scaled to 26 qubits [kim2023scalable]. Digital ZNE by unitary folding [giurgicatiron2020digital] is the variant we use.
- Probabilistic error cancellation (PEC) with learned sparse Pauli–Lindblad models [vandenberg2023probabilistic] removes bias at an exponential sampling cost.
- Readout mitigation by tensored or tomographic inversion [bravyi2021mitigating; maciejewski2020mitigation] is cheap when calibration is amortized.
- A resource-normalized evaluation across hardware platforms finds mitigation beneficial on average but strongly platform-dependent, with some settings worse than no mitigation [russo2023testing]; at a matched online shot budget, unconstrained ZNE can be worse than the raw estimate on a large fraction of instances [zhang2026worse]. We adopt a shot-matched comparator throughout.

**Learning for QEM.** Learning-based QEM learns *the mitigation map itself*:
- quasi-probability compensation learned from near-Clifford training circuits [strikis2021learning];
- regression, forests and graph networks that mimic ZNE at lower cost [liao2024machine].

Relatedly, noise-aware circuit learning optimizes the circuit itself against a device's noise model [cincio2021machine].

Our question differs: we keep standard mitigation maps and learn only *which one to apply, if any*.

**Adaptive selection of mitigation.** Several 2026 works select mitigation per context:
- **GSC-QEMit** [szachara2026gsc] clusters telemetry, forecasts degradation and uses Thompson sampling to choose abstract mitigation intensities, on eight simulated benchmark workloads, including GHZ, QFT and Grover.
- **A cost-aware LinUCB** [rahman2026adaptive] chooses ZNE scale-factor sets for hybrid VQC image classifiers.
- **APGEM** [majid2026context] selects among no mitigation, ZNE, PEC, CDR and readout mitigation in quantum reinforcement learning for vehicle routing, using fidelity-, reward- and noise-level context.
- **Rao et al.** [rao2026adaptive] choose none, dynamical decoupling or ZNE per circuit from circuit and hardware features.
- **Scavino** [scavino2026decision] argues that mitigation should be selected by its effect on downstream decisions rather than by expectation-value accuracy, and finds that, in the regimes evaluated, decision-aware selection often retains the raw estimate.

To our knowledge, these works do not:
- (i) include extra shots and combined mitigation as alternatives in the same action space;
- (ii) restrict the context to cheap label-free probes, with true noise parameters never used as policy inputs;
- (iii) test, with pre-registration and held-out models, whether a learned policy outperforms a simple probe rule.

**QML for fraud detection.** VQCs and quantum kernels have been applied to credit-card fraud:
- kernel-based anomaly detection [kyriienko2022unsupervised];
- VQC and quantum-kernel classifiers on the same European dataset under depolarizing noise, with AUPRC as the primary metric [dinut2026comparative];
- architecture comparisons under several noise channels [elalami2026comparative; das2025qfdnn; li2025hqrnn];
- a large private bank dataset [tudisco2024evaluating].

Comparisons with classical models are mixed: on the same dataset, tuned classical baselines outperform 4-qubit VQC and quantum-kernel classifiers [dinut2026comparative], whereas other studies report quantum or hybrid models matching or exceeding classical baselines on particular metrics or datasets [kyriienko2022unsupervised; li2025hqrnn; tudisco2024evaluating]. **We make no quantum-advantage claim.** We use the VQC as a noisy classifier whose mitigation decisions we study, not as a competitor to classical fraud models.

**Noise as a performance factor.** Noise can occasionally *improve* QML models in specific regimes [zhu2026rethinking; ahmed2025noisy]. The effects of mitigation on hybrid networks are strongly noise-model-dependent [minguenjiki2026robustness]. Our Phase 3B characterization is consistent with this: noise reshapes calibration far more than discrimination.

## 3. Methods

### 3.1 Data and partitions

**Dataset and deduplication.** We use the European credit-card fraud dataset [dalpozzolo2015calibrating; mlgulb2018creditcardfraud]: 284,807 transactions, 0.17% fraud, with features `V1`–`V28` (PCA components released by the dataset creators), `Time` and `Amount`. Exact duplicates are removed, leaving 283,726 rows and 473 frauds.

**Partitions.** Rows are assigned to five partitions by a group-aware stratified split, in which rows that are identical apart from `Time` never straddle partitions:
- VQC training (127,677 rows);
- VQC validation (28,372);
- controller training (42,559);
- controller validation (28,372);
- controller test (56,746).

**Preprocessing.** Every preprocessing parameter is fitted on VQC training data only.

### 3.2 Variational quantum classifiers

**Base model.** A 4-qubit ZZ feature map [havlicek2019supervised] with a RealAmplitudes or EfficientSU2 ansatz and a parity or mean-Z readout. Scores are p = (1 − ⟨O⟩)/2. Models are trained by COBYLA on balanced subsets of VQC-training data.

**Encoding repair.** A pre-registered cross-validated repair replaced an aliasing, saturating angle encoding. It raised the base model's validation AUPRC from 0.104 to 0.507 (AUROC 0.957).

**Pool.** We then trained a pre-registered pool of **64 VQCs**: 16 structures (feature sets, encodings, ansatz family and depth, readout) × 4 seeds. All qualified on clean validation data. Each model's decision threshold τ_m is tuned once on clean VQC-validation data and frozen.

### 3.3 Noise

**Simulation.** Noise is simulated exactly with Qiskit Aer density matrices [javadiabhari2024quantum]:
- depolarizing channels after one- and two-qubit gates (parameters p1, p2);
- thermal relaxation over gate durations (T1, T2; 35 ns and 300 ns);
- per-qubit readout confusion (p01, p10), applied classically to the exact distribution.

Finite-shot outcomes are sampled from these exact distributions.

**Anchors.** Severities follow a low/medium/high anchor grid (p2 up to 0.02, T1 down to 50 µs, mean readout error up to 0.05). Asymmetric readout is a **synthetic stress-test assumption**, not device data.

**Phase 5B** used 8 near-categorical conditions: clean, readout-only, gate-only and combined.

**Phase 5C** varies all sources *continuously and jointly*:
- Each source is placed on an *anchor-severity* scale s ∈ [0, 3], piecewise linear through the anchors, so nothing exceeds the "high" anchor.
- A split-plot space-filling design crosses 17 gate settings (a gate-free plot plus a 16-point maximin Latin hypercube in depolarizing × thermal severity) with 4 readout settings each (a sliced Latin hypercube in magnitude × asymmetry): 68 noise points in total.

### 3.4 Actions and costs

| Action | Description | Shots per inference | CX exposure | Circuits |
|---|---|---|---|---|
| **A0** | none | S | 1× | 1 |
| **A1** | tensored readout mitigation from two calibration circuits, with Euclidean projection onto the simplex | S (calibration amortized: 2S/N) | 1× | 1 |
| **A2** | ZNE: global unitary folding at λ = 1, 3, 5 with linear least-squares extrapolation | 3S | 9× | 3 |
| **A3** | A1 at each fold, then ZNE | 3S | 9× | 3 |
| **A4** | no mitigation, with 3S shots (the shot-matched alternative to ZNE) | 3S | 3× | 1 |

Here S is the shot budget per circuit (256, 1,024 or 4,096). The cost order is A0 < A1 < A4 < A2 < A3. All actions within a replicate share paired, nested random draws.

### 3.5 Observable context and leakage control

**What a policy sees:**
- **16 static descriptors:** circuit size and depth, ansatz, readout observable, encoding family, feature set, frozen clean-validation metrics and threshold.
- **11 probe features** from two cheap, label-free probes:
  - a *readout probe*: the two calibration circuits that A1/A3 reuse;
  - a *gate probe*: 32 fixed synthetic parameter bindings executed at fold factors 1 and 3, giving mean |⟨O⟩| contraction, slope and shot variance.

**Probe cost.** 66 circuits and 66·S shots per batch, charged to every probing policy (≈ 0.2% of A0 at our batch sizes).

**What a policy never sees:** a feature registry marks true noise parameters, noise labels, design-point identifiers, model identifiers, labels and post-action outcomes as offline-only. Automated tests prove they cannot enter a policy's input table. The probes, by contrast, are deployable measurements that *estimate* the noise by design: the readout probe tracks the true mean readout error closely.

### 3.6 Decision formulation

**Primary endpoint.** Brier score [brier1950verification], because Phases 3B–4 showed that mitigation acts on calibration.

**Context.** A context c is (model, noise point, shot budget). Its outcome for an action is the mean Brier over 20 replicates.

**Oracle.** The cost-aware Oracle action p\*(c) is the **cheapest action whose Brier is within (1 + ε) of the minimum over actions**, with ε = 0.10 (sensitivity analysis at 0.05 and 0.20).

**Failure.**
- A policy *fails* at c if its action is too unreliable (beyond the tolerance) or more expensive than p\*. Because p\* is the cheapest action within tolerance, failure is equivalent to disagreeing with p\*.
- A failure is **material** if the action's Brier exceeds (1 + 2ε) × the minimum, or if it costs at least S more shots per inference than p\*.

**Regret.** We also report relative Brier regret against p\* and cost regret in units of S. Brier regret can be negative: p\* may lie up to ε above the best Brier, so a policy that overspends (for example always-A3) can be more reliable than the Oracle while costing more. Cost regret and the overspend criterion count action shots only; reported shots per inference also include probe shots.

**No λ.** We do not choose a scalar utility weight; the constrained formulation is the registered decision rule.

### 3.7 Policies

| Policy | Description | Fitted on |
|---|---|---|
| Never / Always | A0, or always A1, A2, A3 or A4 | — |
| Best universal action | the single action with lowest training failure | training contexts |
| **R_cat** | probe category rule: readout error ≥ 0.005 and/or gate contraction ≤ 0.90, giving 4 cells, each taking its majority Oracle action per budget | cell actions on training contexts |
| **R_thr** | the same decision list with per-budget thresholds fitted by grid search | training contexts |
| **R_obs** | R_thr fitted separately by readout observable (a legitimate static descriptor) | training contexts |
| Learned comparators | four, specified before fitting and using all 27 registered inputs: **L_logistic** (multinomial logistic regression, C = 1), **L_tree3** (decision tree, depth 3, min leaf 50) and **L_gbt** (histogram gradient boosting, depth 4, learning rate 0.1, 200 iterations), each predicting p\* directly; **L_gbt_benefit** (the same gradient boosting predicting each action's log Brier ratio to A0, then the cost-aware rule). Fixed hyperparameters, no tuning and no cross-validation; no random forest | 5C training contexts only; frozen by decision fingerprints |
| Oracle | upper bound | — |

### 3.8 Pre-registration, gates and statistics

**Pre-registration.** Each phase was pre-registered with its code and pushed before outcomes existed. Gates decided whether to proceed:
- **G3B** (Phase 5B): registered as FAIL if the best simple rule failed in < 5% of validation contexts.
- **G3C** (Phase 5C): passes to controller training only if
  1. several actions matter;
  2. the best of the registered simple rules fails ≥ 15% of the time;
  3. the residual depends on the model at a fixed noise point, across several structures;
  4. it exceeds replicate label noise by ≥ 0.10;
  5. material failures are ≥ 10%;
  6. support is adequate.

**Statistics.** Models (and their structures) are the independent units. In the multi-model phases (5B onward), uncertainty comes from a two-stage cluster bootstrap (structures, then models within structures; 2,000 resamples), and replicates, transactions and action rows are never treated as independent observations. (The single-model characterization of Phases 3B–4 resamples transactions and replicates for one model and makes no claim beyond that model.) Policy comparisons use paired, per-decision differences, reported as R_thr − comparator, so negative values favour the rule. The held-out test contains only four structures, so its structure-level bootstrap intervals are likely too narrow (always-A3's is degenerate). The pre-registered detectable effect of ≈ 0.70 SD assumed 16 independent models; at the structure level, power is lower.

**Sealed test.** The controller test partition's outcomes are generated into a gitignored lockbox. They are read exactly once, by a final evaluation whose protocol is committed beforehand.

## 4. Results

### 4.1 What noise and mitigation do

**Noise** (P3A-R base model, VQC validation data; exact simulation at the [RR] anchors):
- AUPRC changes by at most 0.003, with every interval containing zero, and at least 46 of the 47 top-ranked validation frauds are preserved. Noise does reorder scores within the legitimate bulk (Kendall τ 0.96–0.99).
- Scores contract toward 0.5, damaging calibration [guo2017calibration]:
  - Brier rises from 0.0093 to 0.121 under combined-high noise;
  - precision at the frozen threshold falls from 0.53 to 0.03.

**Mitigation** (1,024 and 4,096 shots, 20 replicates):
- No action improves AUPRC over its shot-matched baseline.
- Brier is restored:

| Condition (1,024 shots) | Action | Brier: before → after |
|---|---|---|
| readout-high | readout mitigation | 0.053 → 0.011 |
| depolarizing-high | ZNE | 0.055 → 0.038 |
| combined-high | both | 0.122 → 0.054 |

- With 3× extra shots, Brier is unchanged.

### 4.2 Categorical noise (Phase 5B): the decision is a lookup

Across 64 models × 8 conditions × 2 budgets:
- **Preferred action by noise family:** clean → none, readout → readout mitigation, gate → ZNE, combined → both.
- **A four-cell probe rule** fitted on training structures fails in 0.33% of validation replicates. The best single action fails in 62.5%.
- **Model dependence:** mitigation benefit is strongly model-specific (ICC ≈ 0.98 for the readout-based actions A1/A3), but it rarely changes the best action.
- **Residual:** the association between structure and preferred action is statistically detectable (mutual information 0.08 nats, p = 0.001) but far below materiality.

**G3B failed.**

### 4.3 Continuous joint noise (Phase 5C): the decision collapses

Across 68 noise points × 3 budgets:
- **Preferred actions:** combined mitigation in 67–71% of contexts and ZNE in 23–27%. Extra shots are never preferred, and the budget changes the choice in < 3%.
- **The best simple rule** (one readout-probe and one gate-probe threshold per budget) has validation material failure 0.020 [0.016, 0.027] and Brier within 0.3% of the Oracle.
- **Model-agnostic ceiling:** knowing the *true* noise point, a model-agnostic policy already matches 94% of validation contexts.
- **Residual:** the structure association is again statistically detectable (validation mutual information 0.04 nats, p < 0.001), driven by the mean-Z readout, but small.

**G3C failed.**

### 4.4 Sealed held-out evaluation

**5C test (16 unseen models, 4 unseen structures):**
- **R_thr:** material failure **0.020** [0.015, 0.026], Brier regret −0.03%, 0.6% more shots than the Oracle.
- **Learned comparators:** 0.021–0.094. The best of them on this test is L_gbt (0.021); its paired difference, R_thr − L_gbt, is −0.0005 [−0.027, 0.016]. H2 is a non-superiority result on material failure.
- **Always-combined mitigation:** 0.059, exactly the 1/17 share of contexts on the gate-free setting, where it pays 2S more than readout mitigation. H3's margin and R_thr's 3.4% shot saving therefore scale with the share of gate-free batches.

**5B test (categorical noise):**
- **R_thr:** 0.088.
- **R_cat** (the 5B category rule): 0.064, significantly better than R_thr (paired R_thr − R_cat 0.024 [0.011, 0.037]).
- **Learned comparators:** 0.12–0.44 (best: L_tree3, 0.118).

All four pre-registered hypotheses are supported.

**Caveats.**
- On raw failure (any disagreement with the Oracle), L_gbt, L_tree3 and R_obs were significantly better than R_thr on the 5C test (paired R_thr − comparator: L_gbt 0.154 [0.028, 0.391]; L_tree3 0.133 [0.003, 0.387]; R_obs 0.130 [0.001, 0.384]). R_thr's extra disagreements were not material.
- The learned comparators were much worse on validation than on test (material failure: L_gbt 0.107 → 0.021; L_tree3 0.175 → 0.026); R_thr scored 0.020 on both.
- The test intervals come from a cluster bootstrap over only four structures and are likely too narrow (§3.8).

### 4.5 Ablations (validation only)

- **The gate probe alone** matches the full rule on material failure (1.8% / 9.4%), although its raw disagreement with the Oracle rises from 10% to 25% under continuous noise. The readout probe only chooses between ZNE and combined mitigation, which differ by two calibration circuits.
- **Probing pays** only for batches above ≈ 645–685 transactions (continuous noise; budget-dependent) or ≈ 80 (categorical). This is conservative, because the 66·S probe cost includes the 2 calibration circuits that always-A3 already pays, and like H3 it scales with the share of gate-free batches.

## 5. Discussion

**Why learning fails here.** The decision has very little structure left once the probes are available:
- Mitigation acts on a calibration *bias* that extra shots cannot remove, so the shot budget is irrelevant.
- In our continuous joint-noise design, 16 of 17 gate settings carry gate noise, so combined mitigation is almost always within tolerance.
- The remaining choice concerns readout noise and is nearly free: ZNE versus combined differs by two calibration circuits.
- Model heterogeneity is real in *magnitude*, but it changes the *ranking* of actions only for one readout type. A single static descriptor captures that, while learners trained on one such structure do not extrapolate.

**Relation to adaptive-QEM work.** Bandit and orchestration approaches to mitigation selection report gains over fixed single-technique policies. Our results suggest such gains should also be measured against **simple probe rules and cost-aware Oracles**, with held-out models and pre-registration. In our setting, the rule captures essentially all of the achievable value on the registered endpoint (material failure).

**Practical recommendation.**
- Run the cheap gate probe.
- If gate noise is detected, use ZNE, adding readout mitigation when the readout probe exceeds ~0.4% error; otherwise use readout mitigation alone.
- Never spend the budget on extra shots to fix calibration.
- For very small batches (< ≈ 645–685 transactions, budget-dependent; ≈ 80 under categorical noise), skip probing and always use combined mitigation.

The numeric thresholds are fitted to our simulated 4-qubit circuits and probes and would need refitting for another device or circuit family.

## 6. Limitations

See `docs/FINAL_REPORT.md` §16:
- simulation only (no hardware);
- 4 qubits;
- one dataset;
- synthetic asymmetric readout;
- an optimistic per-model threshold;
- no quantum advantage;
- design dependence: the advantage over always-A3 and the probing break-even scale with the share of gate-free batches (1 of 17 gate settings);
- four held-out structures: cluster-bootstrap intervals are likely too narrow, and structure-level power is low;
- endpoint choice: on raw disagreement with the Oracle, two learned comparators and R_obs were significantly closer to the Oracle than R_thr.

## 7. Conclusion

We asked when a noisy quantum fraud classifier should pay for error mitigation, and whether learning that decision beats a simple observable rule. Mitigation matters for calibrated decisions and is chosen by noise type. In both categorical and continuous joint noise, a two-threshold probe rule is near-Oracle on unseen models. Learned controllers were not justified by two pre-registered gates, and fixed learned comparators did not improve on the rule in a one-time held-out test.

**Selective quantum error mitigation in this setting is a simple rule, not a learning problem.** Hardware validation, larger circuits and richer mitigation techniques are the natural next tests of that conclusion.

## References

*Keys resolve to `docs/LITERATURE.md` §A (L-rows), §D and §E, which carry DOIs or arXiv identifiers; the dataset page `mlgulb2018creditcardfraud` is §B S01. Full metadata for every key is in `deliverables/paper/references.bib`, checked in `deliverables/paper/REFERENCES_VERIFICATION.md`. All are agent-checked; team confirmation is pending before submission.*

ahmed2025noisy (L08) · bravyi2021mitigating · brier1950verification · cai2023quantum · cincio2021machine (L18) · dalpozzolo2015calibrating · das2025qfdnn (L04) · dinut2026comparative (L01) · elalami2026comparative (L02) · giurgicatiron2020digital · guo2017calibration · havlicek2019supervised · javadiabhari2024quantum · kandala2019error · kim2023scalable (L11) · kyriienko2022unsupervised (L05) · li2025hqrnn (L06) · liao2024machine (L13) · maciejewski2020mitigation · majid2026context (L17) · minguenjiki2026robustness (L09) · mlgulb2018creditcardfraud (S01) · preskill2018quantum · rahman2026adaptive (L16) · rao2026adaptive (R01) · russo2023testing · scavino2026decision (R03) · schuld2020circuit · strikis2021learning (L10) · szachara2026gsc (L15) · temme2017error · tudisco2024evaluating (L03) · vandenberg2023probabilistic (L12) · zhang2026worse (R04) · zhu2026rethinking (L07)
