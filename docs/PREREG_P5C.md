# Phase 5C pre-registration: continuous mixed-noise counterfactual study and residual-complexity gate G3C

| | |
|---|---|
| **Status** | PRE-REGISTERED 2026-10-08. Committed and pushed, **together with the generation and analysis code**, before any Phase 5C outcome exists. |
| **Authority** | PI autonomous-completion brief (`docs/AUTONOMOUS_PROJECT_COMPLETION_BRIEF.md`; DECISIONS A16), which resolves O29 by ordering this study. |
| **Machine-readable** | `configs/mixed_noise_study/p5c_v1.yaml` (study; inherits `p5b_v1`), `configs/experiments/phase5c_mixed_noise.yaml` (protocol 0.12) |
| **Builds on** | Phase 5B (G3B = FAIL, `018734c`). Nothing in Phase 5B is changed, re-analysed or re-interpreted. |
| **Not in this phase** | Training any controller (Q-TRACE or otherwise); reading the sealed test split. |

## 1. Why this study, and what it asks

Phase 5B's eight conditions were near-categorical noise families (none, readout-only, gate-only, combined). Cheap label-free probes revealed the family almost perfectly, so a four-cell probe rule reproduced the cost-aware Oracle in 99.7% of validation replicates (G3B = FAIL, `fixed_rule_sufficient`).

Real devices show readout and gate errors **simultaneously, at continuously varying magnitudes**. Phase 5C asks:

> **Does a genuinely non-trivial selective-mitigation decision problem emerge under continuous, joint readout / depolarizing / thermal noise and varied shot budgets, or does a simple probe-based policy remain sufficient?**

| # | Question | Answered by (§) |
|---|---|---|
| Q1 | How is the cost-aware preferred action distributed over the continuous noise space and budgets? | §11.1 |
| Q2 | How well do simple, pre-registered probe rules reproduce it on held-out validation models? | §9, §11.2 |
| Q3 | Does the right action depend on the model at a fixed noise point (model × noise interaction), across several structures? | §10.1 |
| Q4 | Is the residual larger than replicate (finite-shot) noise in the Oracle labels? | §10.2 |
| Q5 | Is the rule–Oracle gap material in reliability or resources? | §8, §11.2 |
| Q6 | Does the shot budget (now including 256) change the preferred action? | §11.1 |
| Q7 | Is a learned controller justified? | G3C, §12 |

**Either answer is a valid scientific outcome.** The study is designed to detect a decision problem *if one exists*. It does not strengthen noise beyond the validated anchors to create one.

## 2. Frozen assets (inherited from Phase 5B, unchanged)

| Asset | Value |
|---|---|
| Model pool | 64 frozen Phase 5A VQCs; manifest SHA-256 `90f09562…` re-verified, along with every artifact and circuit hash |
| Structure split | Phase 5B registered split, 8 / 4 / 4 structures, all four seeds of a structure together (`p5b_v1.structure_split`) |
| Controller panels (A04) | Full partitions: train models → `ctrl_train` (42,559 rows), val → `ctrl_val` (28,372), test → `ctrl_test` (56,746). Access phase `phase5c` |
| Actions and implementations | A0–A4 exactly as Phase 5B / Phase 4 (`p4_v1`): tensored readout inversion with simplex projection; global folding 1/3/5 with linear least-squares ZNE; combined; A4 = None with 3S shots |
| Cost order | A0 < A1 < A4 < A2 < A3 (Phase 5B §5) |
| Probes | The Phase 5B readout probe (= the calibration counts A1/A3 reuse) and gate probe (the **same** 32 fixed synthetic bindings at λ = 1, 3; same seed key) |
| Controller inputs | The Phase 5B 16 static + 11 probe features (registry, now v0.4) |
| Seeds | Experiment master seeds identical to Phase 5B; Phase 5C uses its own stream keys (`p5c-design`, `p5c-shots`, `p5c-bootstrap`, `p5c-structure-permutation`) |

## 3. What is new in Phase 5C

| Item | Phase 5B | Phase 5C |
|---|---|---|
| Noise contexts | 8 named conditions | **68 points of a continuous split-plot design** (§4) |
| Shot budgets | 1,024; 4,096 | **256**; 1,024 (primary); 4,096 |
| RM9 diagnostic | drawn | not drawn (not an action) |
| Outcome metrics | incl. ranking diagnostics | Brier, ECE, AUPRC, AUROC, precision, recall, F1, F2 (ranking diagnostics are not endpoints) |
| Gate | G3B | **G3C** (§12) |

The low 256-shot budget is included because Phase 4/5B found no budget effect at ≥ 1,024 shots, and cost-constrained deployments run at low shot counts. There, probe noise and the extra-shots action (A4) may matter. It is a resource condition, not a noise-strength change.

## 4. Noise design (registered table `results/tables/p5c_design.csv`, SHA-256 `331397d2…`)

### 4.1 Anchor-severity scale

Each noise source has a severity s ∈ [0, 3]. 0 means absent; 1, 2, 3 are the [RR] **low / medium / high** anchors validated in Phase 3B. Physical parameters are **piecewise linear in s between anchors**, so no point exceeds the validated "high" anchor.

| Source | s = 0 | s = 1 | s = 2 | s = 3 |
|---|---|---|---|---|
| Readout mean error r | 0 | 0.005 | 0.020 | 0.050 |
| Depolarizing (p1, p2) | (0, 0) | (0.0005, 0.005) | (0.001, 0.010) | (0.003, 0.020) |
| Thermal rates (1/T1, 1/T2) per µs | 0 (T = ∞) | (1/200, 1/250) | (1/100, 1/150) | (1/50, 1/70) |

- **Readout asymmetry** α ∈ [0, 0.5]: p01 = r(1 − α), p10 = r(1 + α). α = 0 is symmetric; α = 0.5 is the Phase 3B 0.5p / 1.5p split. **The asymmetric component is a synthetic stress-test assumption, not device calibration data (O20 remains open).**
- Thermal rates (not times) are interpolated; this preserves T2 ≤ 2 T1 on every segment (checked).
- Gate times are unchanged (35 ns one-qubit, 300 ns two-qubit). Gate-noise construction is unchanged (Phase 3B §4).

### 4.2 Split-plot space-filling design

Gate noise needs an exact density-matrix simulation per setting (about 100 s per model per setting on 42.6k rows). Readout noise is applied classically and is nearly free. The design is therefore split-plot:

- **17 gate plots:**
  - 1 **gate-free** plot (s_dep = s_th = 0);
  - 16 plots from a **maximin Latin hypercube** in (s_dep, s_th) ∈ [0, 3]²: 500 candidate LHS draws, keeping the one with the largest minimum pairwise distance.
- **4 readout points per plot** from a **sliced Latin hypercube** in (s_ro, α):
  - across all 68 points, each of s_ro and α is an LHS with 68 strata;
  - within every plot, the 4 points fall in the 4 different quarters of both ranges.
  - So every gate setting is crossed with low, low-mid, mid-high and high readout noise, giving near-clean, readout-dominated, gate-dominated, mixed and transition regions by construction.
- **68 noise points** with fixed IDs `gXX-rJ`.
- The generator is deterministic: `noise` stream, key `p5c-design`. The table is committed with this registration. Its hash is in the config, and the build refuses to run if the regenerated design differs.

**Gate plots (s_dep, s_th):**

| g00 | g01 | g02 | g03 | g04 | g05 | g06 | g07 | g08 | g09 | g10 | g11 | g12 | g13 | g14 | g15 | g16 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| 0, 0 | 2.06, 2.09 | 1.61, 2.72 | 0.18, 1.55 | 0.66, 0.69 | 1.48, 1.98 | 2.57, 2.46 | 1.09, 1.17 | 2.15, 1.11 | 0.21, 2.89 | 0.55, 2.28 | 2.84, 0.07 | 2.33, 0.31 | 2.81, 0.84 | 1.79, 1.47 | 0.76, 1.72 | 1.19, 0.54 |

**Descriptive regions** use the true severities with cut 1 (the "low" anchor). A source counts as present if its severity is ≥ 1; for gate noise this means max(s_dep, s_th) ≥ 1.

| Region | Points |
|---|---|
| mixed | 40 |
| gate-dominated | 20 |
| readout-dominated | 5 |
| near-clean | 3 |

Regions are offline labels for reporting only. The design is uniform in anchor severity and was **not** tuned toward any region or outcome.

## 5. Counterfactual generation

| Item | Registration |
|---|---|
| Contexts | 64 models × 68 points × 3 budgets = 13,056 contexts (train 6,528; val 3,264; test 3,264, sealed) |
| Replicates | 20 per context |
| Rows | 13,056 × 20 × 5 actions = **1,305,600** |
| Draws | Phase 4 paired, nested draws (`draw_context` without RM9): A0–A3 share the scale-1 draw; A4 adds 2S shots to it; calibration S + S. Gate probe: S shots per binding at λ = 1 and 3 |
| Seeds | `shots` stream, key (`p5c-shots`, model, point, budget, replicate, component) |
| Execution | One isolated worker per model (largest panels first); each gate plot's exact distributions are computed once and shared by its 4 readout points; deterministic sorted merge; duplicates refused |
| Storage | train/val → `results/processed/phase5c` (gitignored); **test → `results/lockbox/phase5c` (gitignored, sealed)**; only the test row count and content hash are committed |

## 6. Observable context and leakage

- **Inputs** of any later policy are only the Phase 5B static and probe features. The registry is now v0.4, with no new deployable entries.
- **Prohibited:** the Phase 5B list, plus the Phase 5C design truth. These are now registered offline-only:
  - `noise_point_id`, `gate_plot_id`, `noise_region`;
  - true severities (`severity_readout`, `severity_depolarizing`, `severity_thermal`);
  - `readout_asymmetry_true`, `readout_mean_true`.
- `mixed_controller_table` rejects them, and the tests prove it.
- The true design is used **only offline**: Oracle labelling, the noise-only ceiling (§10.1), region summaries and probe validity.

## 7. Outcomes and cost

**Per context × replicate × action:**
- Brier (**primary reliability endpoint**);
- ECE;
- AUPRC and AUROC (secondary diagnostics);
- precision, recall, F1, F2 at the frozen τ_m (secondary; τ_m is Phase 5A's `vqc_val` threshold, never tuned on ctrl\_\*, under noise or by action);
- clipping and projection diagnostics.

**Cost** per model × budget × action uses the raw Phase 5B accounting, not collapsed: shots, circuits, calibration, CX-shots, noisy one-qubit gate-shots, depth-weighted shots.

**Probe cost** is charged separately: 66 circuits and 66·S shots per batch. **Total deployment cost = probe cost + action cost** for any probe-using policy. Universal policies pay no probe cost.

## 8. Oracle, failure and regret

- **p\*(c)** (descriptive; never a feature): the cheapest action in the cost order whose context-mean Brier is ≤ (1 + ε) × the minimum over A0–A4.
  - Primary ε = **0.10**, as in Phase 5B.
  - Sensitivity ε ∈ {0.05, 0.20}: shares and rule failures are re-derived, with rules re-fitted on train at each ε.
- **Failure:** the chosen action's Brier exceeds the tolerance, **or** it costs more than p\*. Because p\* is the cheapest action within tolerance, **a decision fails exactly when it differs from p\***.
- **Material failure:** either of the following:
  - Brier > (1 + 2ε) × min, i.e. more than twice the tolerance;
  - the choice costs ≥ 1 × S more shots per inference than p\*.

  Near-ties and near-free overspends (A1 vs A0, A3 vs A2: only 2S/N calibration shots) are failures but not material.
- **Regret:**
  - reliability: (Brier(a) − Brier(p\*)) / min Brier;
  - resources: (shots(a) − shots(p\*)) / S.
- Reported, with total shots and CX-shots per inference including probe cost.
- No scalar utility and no λ are used. The constrained formulation above is the registered decision rule.

## 9. Simple probe rules (fitted on TRAIN replicates only; evaluated per replicate)

All three rules have the Phase 5B §10 decision-list form, with cells {none, gate, readout, both}:
- readout error ≥ t_r **and** contraction ≤ t_g → cell "both";
- readout error ≥ t_r only → "readout";
- contraction ≤ t_g only → "gate";
- otherwise → "none".

Each cell takes the majority train p\* (ties go to the cheaper action), which minimises train failure.

| Rule | Thresholds | Groups |
|---|---|---|
| **R_cat** | a priori: t_r = 0.005, t_g = 0.90 (the Phase 5B category rule) | per budget |
| **R_thr** | chosen per budget to minimise train failure over a grid of the train replicates' 2.5%, 5%, …, 97.5% quantiles of `probe_readout_error_mean` and `probe_gate_contraction` (39 × 39) | per budget |
| **R_obs** | as R_thr, fitted separately per **readout observable** (parity / mean-Z; a legitimate static descriptor) | per descriptor × budget |

**Comparators:** universal "always a" for a ∈ A0–A4, with the best universal action chosen on train; and the Oracle.

**The gate's "simple rule"** is whichever of R_cat, R_thr and R_obs has the **lowest validation failure**. This choice favours the simple rule, which makes the gate *harder* to pass. That is deliberate: if any registered simple rule suffices, learning is not justified.

## 10. Residual-structure analysis (train; validation as replication; test never)

1. **Noise-only ceiling F_N (Q3).** For each (noise point, budget), take the single action that is p\* for the most models (ties go to the cheaper action), chosen *on the split itself* using the **true** noise point. F_N is the share of contexts where a model's p\* differs from it.
   - F_N is an optimistic bound for *any* model-agnostic policy, even one that knew the noise exactly.
   - F_N > 0 means the right action depends on the model at a fixed noise point.
   - It is reported per structure. A structure "supports" model dependence if its F_N(s) ≥ 0.05.
2. **Label stability (Q4).**
   - Split-half agreement of p\* (replicates 0–9 vs 10–19).
   - **Label instability:** the mean probability that p\* changes when each context's 20 replicates are bootstrap-resampled, paired across actions; 200 resamples.
3. **Structure association:** I(p\*; structure | best rule's modal cell, budget), tested by permuting model→structure labels (2,000 permutations).
4. **Uncertainty:** two-stage cluster bootstrap (structures, then models within structure; 2,000 resamples) for 95% CIs of validation failure, material failure and regrets of the rules and the best universal policy. No statistic treats replicates, transactions or action rows as independent model-level observations.
5. **Descriptives:**
   - preferred-action maps per point × budget;
   - region and structure summaries;
   - between-budget disagreement;
   - two-way η² (model × noise point) of ΔBrier per action and budget;
   - probe validity: Spearman correlations of context-mean probes with the true readout mean, s_dep, s_th and max(s_dep, s_th).

## 11. Reporting

1. **Q1, Q6:** p\* shares (train / val; by budget, region, structure); between-budget disagreement; A4 and A0 shares.
2. **Q2, Q5:** a policy table for train and val × budget (all and per budget) × ε. It reports failure, material failure, reliability failure, mean Brier, regrets, total shots and CX-shots per inference, with CIs on val.

## 12. G3C (registered)

**FAIL if any of the following holds.** Then **no learned controller** is trained.

| Condition | Threshold |
|---|---|
| Dominance | one action is p\* in ≥ 90% of train **or** val contexts |
| Rule sufficient | best simple rule's val failure < 0.05 |
| Negligible regret | best simple rule's val **material** failure < 0.05 |
| Replicate noise | train split-half p\* agreement < 0.60 |

**PASS only if not FAIL and all of the following hold** (the brief's six criteria):

| # | Criterion | Operationalisation |
|---|---|---|
| P1 | Multiple actions meaningfully preferred | ≥ 2 actions each p\* in ≥ 10% of **both** train and val contexts |
| P2 | Not reproducible almost perfectly by a simple rule | best simple rule's val failure ≥ 0.15 |
| P3 | Residual depends on model × noise interaction | F_N(val) ≥ 0.10, **and** ≥ 2 of 4 val structures **and** ≥ 3 of 8 train structures each with F_N(s) ≥ 0.05 (not a single-structure exception, unlike the Phase 5B mean-Z case) |
| P4 | Larger than replicate noise | best rule's val failure − val label instability ≥ 0.10 |
| P5 | Meaningful rule–Oracle gap | best rule's val material failure ≥ 0.10 |
| P6 | Sample and independent-model support | every action with ≥ 10% train share is p\* in ≥ 5% of the contexts of ≥ 3 train structures and ≥ 2 val structures; no single val structure holds > 60% of the best rule's val failures |

**CONDITIONAL:** neither FAIL nor PASS. **A learned controller is then also not trained** (the brief requires all six criteria). The residual is reported as a limitation of the simple rule.

**Consequences:**

| Verdict | Next step |
|---|---|
| **PASS** | A separate Phase 6 pre-registration (controller formulation, candidate models from simplest to more complex, group-aware tuning on train/val only), committed before any training. Then Phase 7 validation comparison and a frozen final-test protocol. |
| **FAIL / CONDITIONAL** | The negative-result path. No Q-TRACE controller. The deployable policy is chosen from the registered simple rules on train/val. A final-test protocol (frozen policy, metrics, tests and outputs, including simple learned comparators fixed in advance to test the "learning adds nothing" claim) is committed before the sealed test is opened once. |

The thresholds mirror G3B's scale (0.05 fail, 0.15 pass, 0.60 split-half, 0.10 share) and were fixed before any Phase 5C outcome.

## 13. Validation and stopping

**Per model** (recorded in `p5c_validation.json`; any failure stops the analysis):
- Aer clean vs the engine on the first 256 panel rows: ≤ 1e-10.
- Folded clean vs unfolded clean (λ = 3, 5): ≤ 1e-10.
- **Noise amplification:** for every noisy gate plot, the mean total-variation distance from clean increases strictly with λ.
- **Gate-free plot:** exact A1 with exact calibration recovers clean expectations (≤ 1e-10) under symmetric and asymmetric readout.

**Build:** the design hash matches the registration, the pool manifest hash matches, the merge has no duplicates, and the lockbox holds the test split.

## 14. Compute

| Item | Value |
|---|---|
| Measured costs (one train model, single process) | about 100 s exact simulation per gate plot; about 0.25 s per replicate-context of draws and metrics |
| Projected run | about 45 P-core-hours. With Phase 5B's measured 2.2× slowdown for 15 workers on 5 P-cores + 10 E-cores, about **6–8 h wall** under `caffeinate`, run once as a reported run on the registration commit |
| Timing profile before registration | One train model under the **Phase 5B** comb-high condition, measuring exact simulation and replicate cost. Only timings were printed; no Phase 5C design point and no outcome value were inspected. |

## 15. Outputs

**Committed:**

| Kind | Files |
|---|---|
| Build | `p5c_design.csv`, `p5c_panels.csv`, `p5c_costs.csv` (64 × 3 × 5 rows), `p5c_validation.json`, `p5c_lockbox_manifest.json` (count and hash only), `p5c_build.json` |
| Analysis | `p5c_point_summary_{train,val}.csv`, `p5c_preferred_by_point_{train,val}.csv`, `p5c_policy_eval.csv`, `p5c_eps_sensitivity.csv`, `p5c_structure_summary.csv`, `p5c_region_summary.csv`, `p5c_budget_effect.csv`, `p5c_variance_decomposition.csv`, `p5c_probe_validity.csv`, `p5c_metadata.json` (G3C, rules, shares, stability, noise-only, association) |
| Figures | Made from committed tables after the analysis |

**Not committed:** replicate-level and context-level datasets (gitignored), and anything about test outcomes beyond the row count and hash.

## 16. Integrity notes

**Known before registration:**
- the Phase 3B/4/5B results, including that 5B's decision followed the noise family;
- the anchor values.

**Not known before registration:**
- any Phase 5C outcome;
- where the continuous boundaries lie.

**Fixed now:** the design (table and hash), budgets, replicates, Oracle and failure definitions, rule families, grids, gate thresholds, and the consequences of each verdict.

**Tests run before registration** used synthetic panels only (with the real frozen model artifacts), plus the timing profile in §14.

## 17. Not done in Phase 5C

- No controller is trained.
- The test split is not read.
- No new mitigation technique, probe or feature is added.
- No noise beyond the "high" anchors.
- No change to Phase 5B artifacts or conclusions.
- No hardware.

---

## Execution record (appended after execution; sections 1–17 unchanged)

**Registration:** committed and pushed at `39b584a` with the generation and analysis code, before any Phase 5C outcome existed.

**Generation:** one reported run on that clean tree (`20261008T141214Z-31395654`; 6.8 h wall, 15 workers, under `caffeinate`). Executed exactly as registered. No code changed between registration and generation, and the analysis ran unchanged.

**Validation:** every per-model check passed (`p5c_validation.json`):
- Aer vs engine ≤ 2.1e-15;
- folded vs unfolded clean ≤ 5.3e-15;
- gate-free exact A1 recovery ≤ 1.6e-15;
- noise amplification strictly monotone in all 16 noisy plots for all 64 models.

The regenerated design matched the registered hash.

**Datasets:**

| Split | Rows | Content SHA-256 | Location |
|---|---|---|---|
| train | 652,800 | `a1f1b9a8…` | processed |
| val | 326,400 | `8c8dad73…` | processed |
| test | 326,400 | `91b0a5b9…` | **sealed in the lockbox, never read** |

**Outcome: G3C = FAIL (`negligible_regret`).** The best simple rule (R_thr) has val material failure **0.020** (95% two-stage CI 0.016–0.027), below the 0.05 fail threshold. No other fail condition triggered. Of the six pass criteria, P1 and P6 hold; P2, P3, P4 and P5 do not. **No learned controller is trained.**

**Disclosures:**
1. **Memory pressure.** The run was slower than projected (6.8 h vs 6–8 h estimated, at the upper end) because 15 workers under memory compression lost about 25% of CPU time. This affects timing only.
2. **Mean-Z residual.** The only structure with large model-specific residual is the train mean-Z structure (noise-only miss 0.59). Val has no mean-Z structure (registered split, as in 5B); the sealed test has one.
3. **Probe sensitivity.** The gate probe's contraction tracks depolarizing severity (Spearman −0.89 to −0.92) but barely tracks thermal severity (−0.12). This is a probe limitation, reported in §3.13.
4. **Rule selection.** R_thr and R_obs tie on val failure (0.0964 vs 0.0965). R_thr is the registered "best simple rule" by the registered criterion.

**Next (completion brief, negative path):**
- A pre-registered Phase 7 / final-test protocol, with fixed learned comparators to test whether learning adds anything.
- Then one opening of the sealed test.
