# Phase 5A — Pre-registration: independent VQC model pool

| | |
|---|---|
| **Status** | PRE-REGISTERED. Committed and pushed before any pool model is trained. |
| **Date** | 2026-10-07 |
| **Machine-readable** | [`configs/model_pool/p5a_v1.yaml`](../configs/model_pool/p5a_v1.yaml) (authoritative), [`configs/experiments/phase5a_pool.yaml`](../configs/experiments/phase5a_pool.yaml) |
| **Exclusions** | No noise, no mitigation, no counterfactual labels, no Q-TRACE controller. Controller partitions locked. No design choice uses any noise, mitigation or policy outcome. |

## 1. Question

**Main question:** do independently trained 4-qubit fraud VQCs differ enough — structurally, in their clean predictions, and later in their noise and mitigation responses — for a selective policy to learn more than a fixed rule?

**What Phase 5A does:**
- builds the pool;
- qualifies it on **clean validity only**;
- freezes it;
- measures its diversity, compute cost and statistical adequacy.

**What Phase 5A does not do:** measure mitigation responses (that is Phase 5B).

## 2. Known before registration (disclosure)

1. **Everything from Phases 1–4,** in particular P3A-R's validation results and Phase 4's mitigation findings. No pool design choice is conditioned on Phase 4 outcomes.
2. **Train-only descriptives on `vqc_train`** (30 processed columns):

   | Quantity | Value |
   |---|---|
   | ANOVA-F ranks 1–8 | V17, V14, V12, V10 \| V16, V3, V7, V11 |
   | Unstandardized PCA-4 explained variance | 0.122 / 0.090 / 0.075 / 0.064 |
   | Standardized PCA-4 explained variance | ≈ 0.04 per component (rejected; see below) |

   Standardized PCA is rejected because V1–V28 are already decorrelated components; standardizing makes PCA-4 an essentially arbitrary projection.

   Frauds sharing an encoded vector (of 213):

   | Features | e3 | e2 | s5 |
   |---|---|---|---|
   | top4 | 2 | 80 | 0 |
   | next4 | 0 | 15 | 0 |
   | pca4 | 0 | 20 | 0 |

   For comparison, the P3A-original encoding (clip 3, [−π, π]) gives 123.
3. **Transpiled circuit sizes** (ZZ full + ansatz, `{rz, sx, x, cx}`, no data):

   | Ansatz | Parameters | CX | SX | Depth |
   |---|---|---|---|---|
   | ra0 | 4 | 12 | 12 | 23 |
   | ra1 | 8 | 15 | 20 | 29 |
   | ra2 | 12 | 18 | 28 | 35 |
   | esu1 | 16 | 15 | 20 | 31 |
   | esu2 | 24 | 18 | 28 | 38 |

4. **Not done:** no pool candidate was trained or evaluated on `vqc_val`. The `mean_z` readout is untested on this task. Prior evidence: single-qubit Z (`z_qubit0`) was weak in the 3A-R cross-validation.

## 3. Data and access

- **New access phase** `phase5a` allows `vqc_train` and `vqc_val` only.
  - **Fitting** (representations, encoders, training subsets, training): `vqc_train` only.
  - **Qualification and diversity:** clean exact scores on `vqc_val` (28,372 rows, 47 frauds).
- **Controller partitions** `ctrl_train`, `ctrl_val` and `ctrl_test` are never read (runtime guard and static test).

## 4. Candidate design (16 structures × 4 seeds = 64 candidates, single wave)

| Axis | Levels |
|---|---|
| Features (train-only) | **top4**: ANOVA-F ranks 1–4 (V17, V14, V12, V10); **next4**: ranks 5–8 (V16, V3, V7, V11); **pca4**: unstandardized PCA-4 of all 30 processed columns |
| Encoding (alias-safe, θ ∈ [−π/4, π/4]) | **e3**: clip ±15 IQR, linear (the P3A-R encoding); **e2**: clip ±5 IQR, linear; **s5**: (π/4)·tanh(r/5), smooth with no clipping |
| Ansatz (linear entanglement) | **RealAmplitudes** reps 1 and 2; **EfficientSU2** reps 1 and 2 |
| Readout | **parity** Z⊗4; **mean_z** = ¼ΣZᵢ. In both cases p_fraud = (1 − ⟨O⟩)/2. |
| Feature map | ZZFeatureMap, reps 1, full entanglement (fixed, as in P3A-R) |

| Block | Structures |
|---|---|
| Main grid (12) | {top4, next4, pca4} × {ra1, ra2, esu1, esu2}, all with e3 and parity |
| Encoding variants (2) | top4-e2-ra2-parity, top4-s5-ra2-parity |
| Readout variants (2) | top4-e3-ra2-mean_z, top4-e3-esu1-mean_z |

**Rationale:**
- The main grid crosses the two axes most likely to change both clean behavior and circuit noise exposure: inputs, and ansatz family × depth.
- The variants add encoding and readout diversity without a full factorial. A single-qubit-type readout responds to readout noise as (1 − 2p) instead of (1 − 2p)⁴.
- `z_qubit0` is not used: it collapsed the signal in 3A-R.
- Expected yield: about 45–64 qualified models.

**Controls** (diagnostic; never in the primary pool):
- **ctrl-p3a-original:** the existing artifact, replayed; alias-prone encoding.
- **ctrl-shallow:** top4-e3-ra0-parity, seed index 0.

**Anchor:** P3A-R (`e3-r2-par`) is replayed only, never retrained, reported separately and not counted.

## 5. Training protocol (one frozen protocol; clean; no noise)

| Item | Setting |
|---|---|
| Representation and encoder | Fitted on **all** of `vqc_train`. Feature rankings must reproduce the registered lists exactly. |
| Training subset | All 213 `vqc_train` frauds + 4 legitimate per fraud (1,065 rows), drawn with the `undersample` stream, subset id `p5a-lpf4-s{k}`. One draw per seed index k is shared by every structure, so structural comparisons are not confounded by the data draw. |
| Objective | BCE on p_fraud, with ε = 1e-7, from exact statevector expectations. |
| Optimizer | COBYLA, 1,000 evaluations, rhobeg 1.0, tol 1e-4, init U(−π, π). Identical to P3A-R. O25 says this budget binds for deeper models; that is accepted as natural heterogeneity. |
| Restarts | 3 per model; keep the lowest final training BCE. |
| Transpilation | One parametrized transpile per structure: `{rz, sx, x, cx}`, optimization level 1. |

## 6. Seeds, IDs and hashes

**Seeds:**
- subset: `undersample` stream, key (`p5a-lpf4-s{k}`);
- initialization: `model` stream, key (`p5a-init`, struct_id, k, restart), mod 2³²;
- transpilation: `model` stream, key (`p5a-transpile`, struct_id), mod 2³¹.

**Identity:**
- **Model ID:** `p5a-{features}-{encoding}-{ansatz}-{readout}-s{k}`.
- **`model_config_sha256`** hashes the structure, seed index, subset id, optimizer, restarts, feature map and transpile seed.
- **`artifact_sha256`** hashes the frozen model: θ, encoder and representation parameters, training record and provenance hashes.
- Also recorded: θ hash, `vqc_val` prediction hash (scores rounded to 12 decimals) and transpiled-circuit hash (QASM3 SHA-256).
- **Artifacts:** `artifacts/model_pool/p5a/<model_id>.json`. **Manifest:** `artifacts/model_pool/p5a_pool_manifest.json`.

## 7. Threshold rule

Each model's frozen τ_m is the max-F1 threshold on its clean exact `vqc_val` scores, ties going to the highest. This is the Phase 3B/4 convention.
- Threshold metrics reported on `vqc_val` are **optimistic**, because τ_m is tuned and reported on the same partition.
- τ_m is frozen for later phases. `vqc_val` is not a controller partition, so later controller evaluation on `ctrl_*` sees no threshold leakage.

## 8. Qualification (clean validity only; broad; fixed now)

A candidate enters the **primary pool** only if all of the following hold, checked in order:

| # | Criterion |
|---|---|
| Q1 | AUROC 95% CI lower bound > 0.5 (shared Phase 2 `vqc_val` bootstrap, 1,000 resamples). |
| Q2 | AUPRC 95% CI lower bound > 10 × `vqc_val` prevalence (E33 rule). |
| Q3 | Kept restart: final training BCE ≤ 0.95 × initial BCE. |
| Q4 | At least 100 distinct `vqc_val` scores (rounded to 12 decimals). |
| Q5 | All scores finite and in [0, 1]. |
| Q6 | Encoding: ≤ 50% of `vqc_train` frauds share an encoded vector, and half-width < π/2. |
| Q7 | Aer density-matrix (noiseless) replay of the transpiled circuit equals the exact engine on the first 256 `vqc_val` rows (≤ 1e-10). |
| Q8 | Bitwise retraining: retraining every restart reproduces θ and the prediction hash. |
| Q9 | Not a duplicate: θ hash and prediction hash differ from every model already admitted, in registry order. |

**Near-duplicates** (Spearman ≥ 0.9999 with an admitted model) are **reported, not excluded**.

**Never used for qualification:** noise, mitigation, Q-TRACE, controller separability, or any Phase 4 endpoint. Weaker-than-P3A-R models are kept if they pass.

## 9. Stopping rule and freeze

- **One wave:** the 64 registered candidates are trained once.
- **Primary pool:** **every** qualified candidate, with no cap and no selection.
- **If fewer than 40 qualify, G3A = FAIL.** No second wave without a new registration.
- **Freeze:** the manifest lists every candidate (status, exclusion reason, hashes, configuration, clean metrics), the controls and the anchor. Later additions or removals require a new registration.

## 10. Diversity diagnostics

| Kind | Measures |
|---|---|
| Structural | Counts by features, encoding, ansatz family, depth and readout. |
| Prediction | Pairwise Spearman, Kendall, mean \|Δscore\|, and flag disagreement at each model's own τ. Summarized by pair type: same structure (seed pairs), one axis differs, two or more axes differ. Average-linkage clustering on 1 − ρ orders the heatmap. |
| Performance | Distributions of AUPRC, AUROC, Brier, ECE and F1@τ_m (optimistic). |
| Circuit | Distributions of depth, CX, noisy one-qubit gates and parameter count. |

## 11. Power and sample-size assessment (O15)

**(a) Heterogeneity of mitigation benefit across models.** Model a per-model benefit Δ_m, measured with R shot replicates, as one-way random effects. Within-model replicate SD σ_w is taken from Phase 4 (replicate SD of ΔBrier, ΔF1@τ and ΔAUPRC for the applicable actions). The minimum detectable between-model SD σ_b uses the noncentral-F test at α = 0.05 and power 0.80, for N ∈ {20, 30, 40, 50, 60, N_pool} and R ∈ {5, 10, 20}.

**(b) Controller vs fixed rule** on held-out models. The paired minimum detectable effect is (z₀.₉₇₅ + z₀.₈₀)/√N_test in SD units, with N_test = 25% of the pool.

**Limits:** the analysis checks adequacy; it never stops anything early. Between-model variance is unknown until Phase 5B.

## 12. Runtime benchmark and projection

**Measured per model:**
- training wall time (all restarts), `vqc_val` inference time, and the transpiled circuit;
- Aer density-matrix time per row at λ = 1, 3, 5 under comb-high gate noise, on 256 **synthetic** parameter bindings. This is timing only; no metric is computed.

**Projection (Table E):** the full Phase 4 design per model:
- 5 gate signatures × 3 factors of exact simulation at the measured per-row time;
- plus Phase 4's measured finite-shot and bootstrap costs, scaled by rows;
- plus scenarios without the two-stage bootstrap and with 10 replicates;
- converted to wall-clock on 15 cores.

## 13. G3A rule

| Verdict | Condition |
|---|---|
| **PASS** | All of (a)–(f) below. |
| **FAIL** | Fewer than 40 qualified; **or** median between-structure Spearman ≥ 0.99; **or** ≥ 50% of qualified pairs have Spearman ≥ 0.999 (essentially identical models); **or** projected full Phase 5B > 168 h wall. Stop and report. |
| **CONDITIONAL PASS** | Otherwise: at least 40 qualified, but (b), (c), (d) or (f) is not fully met. |

The PASS conditions:
- **(a) Size:** at least 40 qualified primary models.
- **(b) Coverage:** every level of every design axis (features 3, encoding 3, ansatz family 2, depth 2, readout 2) has at least 3 qualified models.
- **(c) Prediction diversity:** the median pairwise Spearman between qualified models of *different* structures is ≤ 0.95, **and** fewer than 5% of all qualified pairs have Spearman ≥ 0.999.
- **(d) No dominance:** no ansatz family above 75%, no seed index above 40%, and no single structure above 15% of qualified models.
- **(e) Clean signal:** every qualified model passes Q1–Q9, and the pool median AUPRC ≥ 10× prevalence.
- **(f) Feasibility:** the projected full Phase 5B is ≤ 48 h wall-clock on this machine.

## 14. Outputs (aggregate only)

**Tables** in `results/tables/p5a_*`:

| Table | Content |
|---|---|
| A | candidate registry |
| B | qualified-pool metrics |
| C | structural coverage |
| D | prediction-diversity summary, plus Spearman and Kendall matrices |
| E | runtime projection |
| — | power |
| — | encoding diagnostics |
| — | metadata, with G3A |

**Figures:**
- **A:** AUPRC distribution;
- **B:** clustered prediction-correlation heatmap;
- **C:** circuit complexity vs performance;
- **D:** structural family vs performance.

**Artifacts:** frozen models and the manifest.

## 15. Not done in Phase 5A

- no noise, no mitigation, no counterfactual labels;
- no controller, no meta-split use (model-level splits are registered before Phase 5B);
- no hardware.

At most a one-model compatibility smoke test with the noise engine, which is not used scientifically.

## 16. Runtime estimate (pre-registration)

| Item | Estimate |
|---|---|
| Training | about 1–3 s per restart, so roughly 10 min for 64 models × 3 restarts plus the retraining check |
| Feature states for 5 (features, encoding) combinations on `vqc_val` | about 1–2 min |
| Bootstrap | about 1 min (parallel) |
| Aer benchmark | about 2–4 min |
| **Total** | **under 30 min** |

---

## Execution record (appended after execution; sections 1–16 unchanged)

**Registration** was committed and pushed at `d542770` before any pool model was trained.

**Executed exactly as registered:**
- the 16 structures × 4 seeds, the feature sets (rankings reproduced exactly), encodings, ansätze, readouts, subsets, optimizer, restarts, seeds, Q1–Q9, the threshold rule, the diversity metrics, the power method, the benchmark and the G3A rule;
- one wave, no cap, no selection.

**Outcome:**
- 64 of 64 qualified. Every retrain was bitwise-identical, and every Aer replay matched the exact engine.
- No θ or prediction duplicates.
- **G3A = PASS.**
- The anchor artifact was byte-identical before and after. Controller partitions were never read.

**Implementation details not fixed by the text** (decided before any result):
1. **Parallelism.** Candidates are trained in parallel processes (joblib). Each is deterministic, and the slow test rebuilds the pool byte for byte.
2. **Representation columns.** Representations are fitted on the 30 processed columns (`time_robust`, V1–V28, `amount_log1p_robust`). PCA outputs are named `pca4_pc1`–`pca4_pc4`. Encoder median and IQR use `np.percentile` (25/50/75) on all of `vqc_train`.
3. **Q7 and prediction hashes.** Q7 uses the first 256 `vqc_val` rows in `row_id` order. Prediction hashes use scores rounded to 12 decimals.
4. **Benchmark bindings.** These are seeded by structure index: angles U(−π/4, π/4), θ U(−π, π). They measure timing only.

**Disclosures:**
- **Host sleep.** The host slept during the dev run, so its manifest wall-clock (29.5 min) includes sleep. All reported timings are `perf_counter` compute time (224 s).
- **Table E is not byte-reproducible.** The measured runtime table depends on timing, so it is excluded from the byte-for-byte reproduction test. Every other output is deterministic.
- **Near-duplicates (reported, not excluded, per §8).** 9 same-structure seed pairs have ρ ≥ 0.999, one with ρ = 0.99997 (top4-e3-ra2-parity s1/s2). All four seeds of top4-e3-esu1-mean_z converge to nearly the same solution. There are 57 connected components at ρ ≥ 0.999.
- **What Spearman measures here.** Spearman over all rows mostly measures ordering of the legitimate bulk. Decision-level disagreement at each model's own τ is a median of 0.3% of rows. G3A's registered criterion (c) uses Spearman as registered.
- **The shallow control is strong.** It reaches AUPRC 0.524, as strong as the best pool model. It remains a diagnostic control, as registered.

**Results:** `docs/EXPERIMENT_PROTOCOL.md` §3.11, `results/tables/p5a_*`, `artifacts/model_pool/`.
