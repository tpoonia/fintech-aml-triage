# Phase 5B — Pre-registration: cross-model counterfactual dataset and observable context

| | |
|---|---|
| **Status** | PRE-REGISTERED. Committed and pushed before any Phase 5B counterfactual outcome is generated. The generation and analysis code is part of this commit. |
| **Date** | 2026-10-07 |
| **Machine-readable** | [`configs/counterfactual_study/p5b_v1.yaml`](../configs/counterfactual_study/p5b_v1.yaml) (authoritative), [`configs/experiments/phase5b_counterfactual.yaml`](../configs/experiments/phase5b_counterfactual.yaml), [`configs/features/registry.yaml`](../configs/features/registry.yaml) v0.3 |
| **Exclusions** | No Q-TRACE training, no fitted rule, no λ. No model change, addition or removal. Test-split outcomes are sealed in the lockbox. |

## 1. Questions

Is action benefit heterogeneous across independently trained VQCs? Can that heterogeneity be predicted from pre-action observables? Does a non-trivial selective decision problem remain beyond a fixed rule? These are answered as Q1–Q6, and gate **G3B** decides.

**Core object:** context × action → downstream outcome + quantum cost.

## 2. Frozen assets

| Asset | Detail |
|---|---|
| Pool | The 64 models of `artifacts/model_pool/p5a_pool_manifest.json`, SHA-256 `90f09562…ca22f9d` (verified). Each artifact hash and rebuilt circuit hash is verified on load. |
| Anchor and controls | P3A-R and the diagnostic controls are not used. |
| Thresholds | Each model's τ_m is frozen from Phase 5A (max-F1 on clean `vqc_val`). It is **never** tuned on `ctrl_*`, under noise or by action. Threshold metrics inherit the documented `vqc_val` optimism. **Brier is the primary endpoint** partly for this reason. |

## 3. Model split (primary: by structure; all 4 seeds of a structure together)

| Split | Structures (models) | Controller partition |
|---|---|---|
| **train** (8 / 32) | top4-e3-ra1-parity, top4-e3-esu2-parity, next4-e3-ra2-parity, next4-e3-esu2-parity, pca4-e3-ra1-parity, pca4-e3-ra2-parity, top4-e2-ra2-parity, top4-e3-esu1-mean_z | `ctrl_train` |
| **val** (4 / 16) | top4-e3-ra2-parity, top4-s5-ra2-parity, next4-e3-esu1-parity, pca4-e3-esu1-parity | `ctrl_val` |
| **test** (4 / 16) | top4-e3-esu1-parity, next4-e3-ra1-parity, pca4-e3-esu2-parity, top4-e3-ra2-mean_z | `ctrl_test` |

**Stratification.** Each split has the feature sets in proportion 2:1:1 (top4 : next4 : pca4) and a balanced ansatz family and depth where possible.

**Documented imbalance:**
- `val` has no ra1, esu2 or `mean_z` structure.
- `test` has no e2 or s5 encoding.
- e2 appears in train only; s5 in val only; `mean_z` in train and test.

**Secondary diagnostic split.** Within each partition, seed index 3 is held out from seeds 0–2. It shares transaction panels, so it is diagnostic only; the primary split is the publication-level split.

## 4. Controller panels (A04)

- **Panel:** every model is evaluated on the **full** controller partition of its split, in `row_id` order.

  | Partition | Rows | Frauds |
  |---|---|---|
  | `ctrl_train` | 42,559 | 71 |
  | `ctrl_val` | 28,372 | 47 |
  | `ctrl_test` | 56,746 | 95 |

- **Properties:**
  - group-safe (the partitions are group-aware by construction, F28);
  - identical across actions, giving paired counterfactuals;
  - frozen before any outcome;
  - verified against the Phase 1 partition hashes.
- **Feasibility:** full partitions are feasible (the Phase 5A projection was about 2.6 h), so no sampling is needed.
- **Access:** phase `phase5b` allows only the `ctrl_*` partitions, and each model reads only its own.

## 5. Contexts, shot budgets, actions, replicates

| Item | Registration |
|---|---|
| Conditions | The 8 Phase 4 conditions with identical parameters: clean, ro-sym-high, ar-020, ar-050, dep-high, th-high, comb-medium, comb-high. ar-* are *synthetic asymmetric readout stress-test profiles* (not device data; O20). |
| Shot budgets | 1,024 and 4,096 per circuit. The budget is an observable context feature. |
| **A0** | None: S shots |
| **A1** | Phase 4 readout mitigation: calibration counts only, tensored inversion, simplex projection |
| **A2** | Phase 4 ZNE: global folding 1/3/5, linear least squares, clipping |
| **A3** | Combined |
| **A4** | **Extra shots: None with 3S shots.** A real action. |
| RM9 | None with 9S shots: diagnostic only |
| Cost order | A0 < A1 < A4 < A2 < A3. Shots per inference S < S + 2S/N < 3S = 3S < 3S + 2S/N; A4 is cheaper than A2 in CX-shots (54S vs 162S). |
| Replicates | 20 per (model, condition, budget) |
| Seeds | `shots` stream, key (`p5b-shots`, model, condition, budget, replicate, component) |
| Pairing | The Phase 4 paired, nested draws. A0–A3 share the scale-1 draw; A4 and RM9 extend it. |
| Unchanged from Phase 4 | Implementations, ZNE factors, extrapolator, calibration procedure, projection and clipping |

**Implementation note (validated, not new science).** Folded *noiseless* circuits equal the unfolded circuit (Phase 4: ≤ 2.4e-15 on every row). The clean scale-1 distribution is therefore reused for scales 3 and 5, and this is re-checked per model on the first 256 panel rows (≤ 1e-10).

## 6. Observable context (A12 tightened as A15; registry v0.3)

**Static (pre-execution or frozen at training):**
- circuit depth and noisy-gate depth;
- noisy one-qubit and CX counts;
- trainable parameters;
- ansatz family and repetitions;
- readout observable;
- encoding family and feature set;
- shot budget;
- clean `vqc_val` AUPRC, AUROC, Brier and ECE at freeze;
- frozen τ.

**Probes (label-free, executed before action selection, cost charged):**

| Probe | What it runs | Features |
|---|---|---|
| **Readout** | The calibration circuits \|0000⟩ and \|1111⟩, S shots each. These *are* the calibration A1/A3 reuse. | Mean p̂01, mean p̂10, mean error, asymmetry (p̂10 − p̂01), binomial SE |
| **Gate** | 32 **fixed synthetic** bindings (data-free: angles ~ U(−π/4, π/4) from `model` stream key `p5b-probe-bindings`, plus the model's frozen θ) through the model's own circuit at fold scales 1 and 3, S shots each, read with the model's own observable | Mean \|⟨O⟩\| at λ = 1 and λ = 3, contraction (ratio), signed and absolute slope, shot variance |

Neither probe uses transactions, labels or post-action results, and neither executes the action matrix.

**Probe cost per batch:** 66 circuits and 66S shots (64S gate + 2S readout), plus CX-shots 32·S·(CX₁ + CX₃). Total policy cost = probe cost + action cost. The readout probe's shots are reused by A1/A3.

**Prohibited** (registry offline-only; automated tests):
- noise family, profile and severity;
- **true simulator parameters** (p1, p2, readout p01/p10, T1, T2);
- the oracle confusion matrix;
- model ID, structure ID and seeds;
- labels;
- current-batch metrics;
- mitigated scores and ZNE task outputs;
- realized deltas;
- the Oracle or preferred action.

Grouping keys live in a separate frame and are never features.

## 7. Outcomes and cost (per context × replicate × action)

| Group | Measures |
|---|---|
| Discrimination | AUPRC, AUROC |
| Calibration | **Brier (primary reliability endpoint)**, ECE |
| Threshold at the frozen τ_m | Precision, recall, F1, F2; crossings against exact clean (all, fraud, legitimate) |
| Ranking against exact clean | Spearman, Kendall, top-K overlap with K = panel frauds, 100 and 1% of the panel |
| Diagnostics | Clipping, projected rows |
| Cost | Raw `ResourceUsage`-style counts per model × budget × action (shots, circuits, calibration, folded executions, CX-shots, noisy one-qubit gate-shots, depth-weighted shots), plus the probe cost. Runtime and wall-clock go to raw only. |

**No scalar utility and no λ.**

## 8. Dataset and independence

**Replicate-level dataset** (gitignored):
- train and val in `results/processed/phase5b`;
- **test in `results/lockbox/phase5b`, sealed;** only its row count and hash are committed.

**Committed:** context-level aggregates, preferred actions and context features for train and val, plus build records.

**Policy context and grouping:**
- A **policy context** is model × condition × budget. Replicates give uncertainty; no statistic treats replicates or transactions as independent contexts.
- **Grouping keys:** model, structure, condition, replicate.

## 9. Preferred action (Oracle, descriptive)

**p\*(c):** the cheapest action (cost order §5) whose context-mean Brier is ≤ 1.10 × the minimum context-mean Brier over A0–A4.

**Also reported:**
- the reliability-best action (argmin Brier);
- the F1-preferred action (cheapest within 0.05 of the maximum F1@τ).

**Policy failure** in context c: the chosen action's Brier exceeds 1.10 × the minimum (reliability failure), **or** it is costlier than p\*(c) (overspend).

The Oracle is an upper bound and never a feature.

## 10. Fixed-rule family (defined now; fitted only in Phase 6, on train contexts)

**Inputs:** readout-probe error and asymmetry, gate-probe contraction and slope, shot budget.

**Form:** a threshold decision list:
- readout error ≥ t_r **and** contraction ≤ t_g → A3;
- else readout error ≥ t_r → A1;
- else contraction ≤ t_g → A2 or A4 (A4 when the probe's shot variance is high relative to its slope);
- else → A0.

The thresholds are Phase 6 parameters, fitted on train contexts only.

## 11. Heterogeneity analysis (TRAIN contexts; VAL as replication; TEST never)

1. **Benefit distributions across models.** For ΔBrier, ΔF1@τ, ΔAUPRC and ΔECE (each action − A0) per condition × budget: mean, SD, quantiles. Plus Δcost.
2. **Preferred-action frequencies** by condition, by structural family (features, encoding, ansatz family, depth, readout) and by budget. **Between-budget agreement** is the share of (model, condition) pairs with the same p\* at 1,024 and 4,096 shots.
3. **Random effects (Table H).** For each (action, condition, budget), a one-way random-effects model of replicate-paired ΔBrier across train models: F test, σ_b, σ_w, ICC.
   - Holm correction across cells, α = 0.05.
   - A cell is **heterogeneous** if its Holm p < 0.05 and ICC ≥ 0.10.
4. **Variance decomposition.** A two-way (model × context) decomposition of context-mean ΔBrier per action, giving η² for context, model and interaction (Q2).
5. **Split-half stability** of p\*: replicates 0–9 vs 10–19.
6. **Observable predictability (Q6), descriptive:**
   - **A priori probe categories per replicate:** readout detected if mean probe readout error ≥ 0.005; gate detected if probe contraction ≤ 0.90. This gives categories {none, readout, gate, both} × budget.
   - **Category rule:** the majority p\* per stratum over **train** replicates (ties go to the cheaper action), evaluated per replicate on train and on **val**.
   - **Comparators:** universal "always a" policies.
   - **Structure association:** the conditional mutual information I(p\*; structure | category, budget) on train contexts, tested by permuting model→structure labels (2,000 permutations; `bootstrap` key `p5b-structure-permutation`).
   - Spearman associations between context-mean features and ΔBrier.

## 12. Q1–Q6 (answered from §11)

| Question | Measured by |
|---|---|
| Q1: benefit varies across models | heterogeneous-cell fraction, ICC, η²_model |
| Q2: noise context vs model structure | η² |
| Q3: budget changes the preferred action | between-budget disagreement |
| Q4: A4 preferred | share of contexts; share among intervention contexts |
| Q5: A0 preferred | share |
| Q6: residual after probes | val category-rule failure, rule gain over the best universal policy, structure-association p |

## 13. G3B (registered; pilot-indicative thresholds)

**FAIL if any of the following holds** (train unless stated). If FAIL: **STOP, no Q-TRACE training.**

| Condition | Threshold |
|---|---|
| Dominance | one action is p\* in ≥ 90% of contexts |
| Negligible differences | < 10% of contexts can improve Brier by ≥ 10% over A0 |
| Replicate noise | split-half p\* agreement < 0.60 |
| No observable signal | val gain of the category rule over the best universal policy < 0.05 |
| Fixed rule sufficient | val category-rule failure < 0.05 |

**PASS if not FAIL and all of the following hold:**
- at least 2 actions are each p\* in ≥ 10% of train contexts;
- the best universal policy fails in ≥ 25% of val contexts;
- the category-rule gain is ≥ 0.20;
- **residual complexity:** val category-rule failure ≥ 0.15 **and** structure-association permutation p < 0.05;
- **model heterogeneity:** ≥ 25% of the testable Table-H cells are heterogeneous.

**CONDITIONAL PASS:** otherwise. The fixed rule then becomes the central Phase 6 baseline.

## 14. Validation and stopping

**Per model** (recorded; any failure stops the analysis):
- artifact and circuit hashes;
- Aer clean equals the exact engine on 256 panel rows (≤ 1e-10);
- folded clean equals unfolded (≤ 1e-10);
- noise exposure decreases with λ;
- exact A1 under symmetric readout recovers clean (≤ 1e-10).

**Unit tests (synthetic):**
- structure and partition isolation;
- frozen hashes;
- probe determinism and behavior;
- probe and action costs;
- counterfactual completeness;
- no duplicate rows;
- deterministic merge;
- leakage guards;
- lockbox refusal;
- the analysis and G3B rules;
- end-to-end build and report.

**Slow tests:** partial regeneration matches the stored dataset row for row, and the report reproduces byte for byte.

## 15. Compute

| Item | Estimate |
|---|---|
| Exact simulation (per model: 4 noisy signatures × λ 1/3/5 + clean, on its panel) | ≈ 25 CPU-h |
| Finite-shot (16 contexts × 20 replicates × 6 vectors) | ≈ 4–6 CPU-h |
| Wall-clock | ≈ 2 h on 15 cores, under `caffeinate` to prevent sleep |

The **full** design runs. There is no replicate reduction and no resource-based stopping.

## 16. Outputs

**Tables** (`results/tables/p5b_*`):

| Table | Content |
|---|---|
| A | split, panels |
| B | feature definitions, costs, static features |
| C | action summary |
| D | benefit distribution |
| E | preferred by condition |
| F | preferred by family |
| G | preferred by budget |
| H | heterogeneity, variance decomposition |
| I | Pareto |
| — | predictability |
| — | context outcomes, preferred actions, context features |
| — | validation, lockbox manifest, build record, metadata (G3B, Q1–Q6) |

**Figures:**
- **A:** models × contexts → p\*;
- **B:** ΔBrier by action and context;
- **C:** Pareto;
- **D:** probes vs benefit;
- **E:** p\* by family;
- **F:** 1,024 vs 4,096.

## 17. Not done in Phase 5B

- no controller training;
- no rule fitting beyond the descriptive train majority;
- no λ;
- no test-split analysis;
- no pool change;
- no new conditions.

---

## Execution record (appended after execution; sections 1–17 unchanged)

**Registration** was committed and pushed at `0572c4c`, together with the generation and analysis code, before any Phase 5B outcome existed.

**Generation** was a single *reported* run on that clean tree (`20261007T223317Z-aa8d41b8`, 1.8 h under `caffeinate`). It ran exactly as registered:
- the split and full-partition panels;
- the 8 conditions, 2 budgets and 20 replicates;
- A0–A4 and RM9;
- probes, features, seeds and costs.

No code changed between registration and generation. The analysis was run afterwards with the registered code, unchanged.

**Outcome:**
- **Datasets:**

  | Split | Rows | Content SHA-256 | Location |
  |---|---|---|---|
  | train | 61,440 | `5b107177…` | processed |
  | val | 30,720 | `5b748b8d…` | processed |
  | test | 30,720 | `c9ecc091…` | sealed in the lockbox, never read |

- **Validation:** every per-model check passed.
- **G3B = FAIL** under the registered rule, on `fixed_rule_sufficient`: the val category-rule failure is 0.33%, below 5%. No other FAIL condition triggered.

**Disclosures:**
1. **Why val failure is low.** Val contains no mean-Z structure, a registered split imbalance (§3). The only model-specific deviation in train (top4-e3-esu1-mean_z prefers A0 under asymmetric readout) therefore cannot appear in val. That is why val failure (0.33%) is below train failure (3.5%). The sealed test split contains a mean-Z structure; it was not examined.
2. **A4's statistical heterogeneity is tiny.** A4's random-effects cells are all "heterogeneous" under the registered statistical criterion, but at σ ≈ 1e-5 Brier the effect is negligible in absolute terms.
3. **The secondary endpoint is descriptive only.** F1@τ preferences vary across models within conditions. F1@τ was registered as secondary and is not part of G3B; it is reported descriptively and was not used to change the verdict.
4. **Dataset schema quirk (test-only fix).** Top-k overlap columns are named per panel (k = the panel's fraud count and 1% of its rows). The deterministic merge takes the union of columns, so each stored split also carries all-NaN overlap columns named after the other partitions' sizes (e.g. `top95_overlap` in train). These names encode only panel sizes already committed in `p5b_panels.csv`; they hold no outcome values. The slow partial-regeneration test initially failed because it took its column list from the stored frame. It now compares the regenerated columns and asserts that the extra columns are all-NaN overlap columns. No data, generation or analysis code changed.

**Results:** `docs/EXPERIMENT_PROTOCOL.md` §3.12 and `results/tables/p5b_*`. **Stop:** no Q-TRACE training (PI rule for G3B FAIL).
