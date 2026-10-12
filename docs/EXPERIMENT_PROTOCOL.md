# Q-TRACE — Experimental Protocol

| | |
|---|---|
| **Version** | 0.14 — Final evaluation incorporated 2026-10-08 (single sealed-test unlock; `PREREG_FINAL.md`). |
| **Freeze rule** | Becomes `1.0` via the git tag `protocol-v1.0` before any controller-test outcome is analysed (§17). Afterwards every change is a logged deviation (§20). |
| **Source** | [RR] = [`research/deep-research-report.md`](research/deep-research-report.md). Decision IDs refer to [`DECISIONS.md`](DECISIONS.md). |

**Tags used throughout:**
- **[RR]**: specified by the research report.
- **[ENG]**: engineering choice.
- **[OPEN]**: needs pilot evidence.
- **[ACC]**: accepted amendment.
- **[DEF]**: deferred amendment.

---

## 1. Stage overview

```text
P1 data → P2 classical → P3A one clean VQC  ══ Oct 12 freeze / Oct 13 WIP ══
P3B benchmark + pool → P4 noise (G1: A13 distortion classes) → P5 QEM + probe + resources (G2)
→ P6 counterfactual dataset (controller-test lockboxed) → P7 predictors (G3)
→ P8 policies, endpoint freeze, locked evaluation (G4) → P9 ablations / OOD → P10 extensions
```

## 2. Data

### 2.1 Source [RR]

- ULB / Kaggle European Credit Card Fraud (`mlg-ulb/creditcardfraud`): 284,807 rows, 492 frauds (0.172%).
- Columns: `V1`–`V28`, `Time`, `Amount`, `Class`.
- ULB and Kaggle are the **same** dataset.
- Record the URL, the licence (as stated on the source page), the download date and the SHA-256 (`configs/datasets/ulb_v1.yaml:expected_sha256`, filled in Phase 1).

### 2.2 Duplicate audit and deduplication (Phase 1 results; `F27`)

The checksum-verified file has 284,807 rows and 492 frauds (0.1727%). `row_id` is the 0-based position in the file.

**Audit** (duplicate key = all 30 feature columns; values compared exactly):

| Finding | Count |
|---|---|
| Exact duplicate groups (features + label) | **773** groups, 1,854 rows in groups |
| Redundant copies | **1,081** (19 fraud, 1,062 legitimate) |
| Duplicate fraud transactions | **Yes**: 13 fraud groups, 32 fraud rows in groups |
| Group sizes | 611×2, 66×3, 81×4, 10×5, 1×6, 2×9, 2×18 |
| Identical features with conflicting labels | **0 groups** |
| Near-duplicates ignoring `Time` (not duplicates under `F27`) | 4,383 groups, 12,456 rows (12,446 after exact deduplication), **all legitimate**, no label conflicts. Kept, but **never split across partitions** (O23, §2.3). |

**Policy applied before splitting:**
- conflicting groups excluded (none existed);
- each exact group reduced to its lowest-`row_id` occurrence.

**Result:** **283,726 rows, 473 frauds (0.1667%).**

**Inherited leakage.** `V1`–`V28` come from a PCA fitted by the dataset creators on the full data. This is unavoidable and listed in §19.

### 2.3 Splits and transaction partitions

**[RR] split (superseded by `F28`):** stratified 60/20/20 train/validation/test.

**[ACC A04]** Controller **training**, **validation** and **testing** must use **disjoint transaction partitions**, in addition to disjoint models.

**[RESOLVED O21 → F28] Option B, group-aware (O23 → E25).**

- **Group key.** Rows sharing `V1`–`V28` + `Amount` form one group. There are 275,663 groups: 271,280 singletons and 4,383 multi-row groups holding 12,446 rows, the largest 77 rows. None mixes labels.
- **Assignment.** Groups are stratified (a group is fraud if it contains any fraud), shuffled with the `split` seed, and assigned whole by midpoint on cumulative largest-remainder targets.
- **Result.** Deviation from the target counts is 0 in both strata. The actual counts after deduplication:

| Partition | Target | Rows | Fraud | Legit | Prevalence |
|---|---:|---:|---:|---:|---:|
| `vqc_train` | 45% | 127,677 | 213 | 127,464 | 0.1668% |
| `vqc_val` | 10% | 28,372 | 47 | 28,325 | 0.1657% |
| `ctrl_train` | 15% | 42,559 | 71 | 42,488 | 0.1668% |
| `ctrl_val` | 10% | 28,372 | 47 | 28,325 | 0.1657% |
| `ctrl_test` | 20% | 56,746 | 95 | 56,651 | 0.1674% |

**Verified:**
- zero overlap between any two partitions;
- no exact duplicate across partitions;
- **zero `V1`–`V28` + `Amount` groups crossing partitions**;
- identical output on rerun;
- other seed streams do not change it.

Source: `results/tables/ulb_v1_dataset_summary.csv`.

**[OPEN O18]** A temporal split is a sensitivity analysis only.

### 2.4 Preprocessing [RR; ACC A04; E24]

1. Keep `V1`–`V28` unchanged, plus `Time` and `Amount`.
2. Apply `log1p(Amount)`. This is valid because `Amount` ≥ 0; 1,825 rows have an amount of 0.
3. Robust-scale `Time` and `log1p(Amount)` with the median and the 25–75 interquantile range.
4. Reduce dimensionality to k = 4 [OPEN O02, Phase 3A].
5. Apply the angle encoding [OPEN O03].

Every learned parameter is fitted **only on `vqc_train`**, at natural prevalence and before undersampling. The fit function selects those rows itself, and tests prove that changing any other partition cannot alter the fit.

**Fitted values (127,677 rows):**

| Column | Median | Q25 | Q75 | Scale (IQR) |
|---|---:|---:|---:|---:|
| `Time` | 84,682 | 54,156 | 139,230 | 85,074 |
| `log1p(Amount)` | 3.13853 | 1.87794 | 4.36539 | 2.48745 |

These were refitted after the O23 correction. Artifact SHA-256: `ce78309f985b922f25870cf7aecfeffb213025ada2c0bbf95c9a0ecf6d795ecf`. Fit-partition hash: `df9d1c017b59afab0c09633caf2c3ebf0969af1678f450e79205d9c41f683356`.

### 2.5 VQC training subset [RR; OPEN O17]

The utility `qtrace.data.subset` is implemented, but **nothing is frozen**:

- **Source.** It samples only from `vqc_train`. The schema allows no other partition.
- **Seeds.** It uses the `undersample` seed stream.
- **Record.** Selected row ids and their hash are recorded.
- **Class balance.** Configurable: all frauds or *n* frauds; legitimate rows per fraud or an explicit count; an optional maximum size.

[RR]'s 3–5 legitimate per fraud, with a maximum of 1,600, is a candidate for Phase 3A, not a decision. With 213 training frauds, 4 per fraud gives 1,065 rows.

### 2.6 Evaluation panels [OPEN O06]: interface only

`qtrace.data.panels` defines a panel record and an abstract sampler. A panel:
- comes from one allowed partition, never `vqc_train`;
- has unique row ids and optional positive weights;
- has a reproducible hash;
- is checked for membership against the partition table.

**Not frozen:** size, prevalence, sampling strategy, weighting, inverse-probability weighting, number of panels. These are designed separately before Phase 6.

At 0.167% prevalence, a 256-row panel ([RR]) contains about 0.43 frauds in expectation, so **AUPRC is undefined**. The controller-test partition holds only 95 frauds in total.

**Rules:**
- Panel composition is identical across every stage whose results are compared.
- Weighted panels use large legitimate samples.
- No QEM observation is ever evaluated on VQC training data. The schema enforces this.

### 2.7 Phase 2: classical sanity baselines (results; evidence only)

**Scope.** Fit on `vqc_train`; select thresholds and report on `vqc_val` (28,372 rows, **47 frauds**). Controller partitions were never read (E26). Configuration: `configs/baselines/classical_v1.yaml` (E28).

**Validation AUPRC [95% bootstrap interval], full `vqc_train` training (Regime A):**

| Representation | Logistic regression | Random forest | Gradient boosting |
|---|---|---|---|
| All 30 features | 0.654 [0.515, 0.806] | **0.805** [0.696, 0.909] | 0.791 [0.685, 0.894] |
| Top-4, ANOVA F (V17, V14, V12, V10) | 0.620 [0.483, 0.778] | 0.676 [0.533, 0.819] | 0.714 [0.576, 0.855] |
| PCA-4, standardized | 0.200 [0.132, 0.317] | 0.713 [0.583, 0.835] | 0.672 [0.536, 0.803] |
| PCA-4 (≈ V1–V4) | 0.264 [0.168, 0.416] | 0.513 [0.373, 0.681] | 0.529 [0.390, 0.675] |

**VQC-scale training (Regime B, mean AUPRC over 3 subset draws), gradient boosting:**

| Training rows (legit per fraud) | All 30 features | Top-4 |
|---|---|---|
| 426 (1) | 0.629 | 0.650 |
| 1,065 (4) | 0.745 | 0.665 |
| 2,130 (9) | 0.679 | 0.634 |

**Other findings:**
- With full-partition training, AUROC is 0.91–0.99 for every full-feature and top-4 model while AUPRC spans 0.62–0.81. AUROC barely separates the models; AUPRC does.
- Cross-fitted F1 is 0.01–0.11 below the in-sample-threshold F1 under full-partition training (0.00–0.14 across all configurations). This quantifies the optimism of tuning and reporting on one partition.
- Class-weighted logistic regression is grossly overconfident: the 0.9–1.0 score bin holds 29% fraud. Random forest and gradient boosting are close to the diagonal where bins have enough rows.
- Brier and ECE are dominated by the ~28,300 rows scored near 0 (§12.1, O14).

All of this is O02/O17 *evidence*, not a decision.

## 3. Quantum model

### 3.1 Architecture [RR]

- ZZ feature map (reps = 1) followed by {RealAmplitudes, EfficientSU2} × reps {1, 2}, on 4 qubits (`configs/qml/pool_rr_v1.yaml`).
- Entanglement patterns are partly unspecified in [RR] and are decided in Phase 3A.
- **[DEF A05]** No additional architectures until after the runtime benchmark and the first heterogeneity results.

### 3.2 Readout observable and score link [OPEN O01] — the decision that matters most

The candidates are global parity, ⟨Z₀⟩, or a multi-observable classical head.

**Theory (derived; the Phase 4 negative-control experiment verifies it):**

1. AUROC and AUPRC depend only on ranking. Any noise that maps the score observable through one increasing affine map, *identical for all transactions*, leaves them **exactly unchanged**, and so does mitigating that noise.
2. **Symmetric** independent readout error is such a map for every Z-type observable. **Readout mitigation is therefore exactly rank-preserving** under symmetric readout, even at finite shots. **[ACC A07]** The [RR] symmetric readout-only anchors are therefore **negative controls**: any AUPRC change there signals a bug or a non-Z observable.
3. **Asymmetric** readout is still affine for ⟨Z₀⟩, but can change ranks for parity. A scratch check gave Spearman ≈ 0.99 at $p_{01}$ = 0.02, $p_{10}$ = 0.08.
4. Gate noise is only approximately uniform. Thermal relaxation is non-unital and may distort scores non-uniformly. The **A13** classification (§16) measures this.

**Rule.** Choose O01 on clean validation performance only. It is provisional in Phase 3A and pre-registered before Phase 4. **Never choose it to make QEM look useful.**

### 3.3 Training [RR]

- Clean training with exact expectation values; then freeze, hash and store.
- COBYLA, `maxiter` 100, provisional [OPEN O04].
- The loss is unspecified.
- **Phase 3A trains exactly one model** (one architecture, one seed) for the Oct 13 deliverable (`F24`).

### 3.4 Pool [RR; ACC-in-principle A06]

- [RR]: 2 × 2 × 10 = 40 models, split 6/2/2 per architecture.
- [RR]'s 8 test models are insufficient if models are the independent units. N is chosen after the Phase 3B benchmark and power analysis [OPEN O15].
- `ModelPoolConfig` already scales without code changes (tested at 200 models).

### 3.5 Inclusion criterion and threshold [OPEN O04, O05]

- Inclusion: a pre-registered minimum clean validation AUPRC. Excluded models are reported.
- Threshold τ is chosen on clean validation data and frozen with the model.
- Brier score and ECE are computed after a fixed clean-validation calibration map, because training prevalence is about 20%.

### 3.7 Phase 3A: first clean 4-qubit VQC (results)

**Configuration:** `configs/vqc/vqc3a_top4_ra1.yaml`. Every choice below was fixed before any `vqc_val` result was seen.

- **Inputs:** V17, V14, V12, V10. This is the top-4 selection, reproduced exactly; it is provisional (O02).
- **Encoding:** θ = (π/3)·clip((x − median)/IQR, −3, 3) ∈ [−π, π], fitted on `vqc_train` (O03).
- **Circuit:** ZZ feature map (reps 1, full entanglement) followed by RealAmplitudes (reps 1, linear entanglement). Transpiled to `{rz, sx, x, cx}`: 4 qubits, depth 29, 15 CX, 20 SX, 34 virtual RZ, 69 operations; 4 data parameters and 8 trainable ones.
- **Readout:** four-qubit parity, with p_fraud = (1 − z)/2 (O01).
- **Training:** binary cross-entropy (ε = 1e-7) on exact statevector expectations. Subset `p3a-lpf4`: 213 fraud + 852 legitimate rows.
- **Optimizer:** COBYLA with a 600-evaluation budget. It used 277 evaluations and stopped with status 0 (trust-region radius at its lower bound). BCE went from 0.7328 to 0.6042.

**`vqc_val` (47 frauds), with 95% intervals from the same stratified bootstrap resamples as Phase 2:**

| Model (same 4 angle inputs, same 1,065 rows) | AUPRC | ROC-AUC | Δ AUPRC vs VQC |
|---|---|---|---|
| **Clean VQC** | 0.104 [0.054, 0.166] | 0.766 [0.674, 0.847] | — |
| Logistic regression | 0.615 [0.485, 0.773] | 0.948 [0.891, 0.989] | +0.511 [0.397, 0.646] |
| Random forest | 0.619 [0.491, 0.765] | 0.966 [0.926, 0.995] | +0.514 [0.406, 0.638] |
| Hist. gradient boosting | 0.582 [0.449, 0.737] | 0.962 [0.922, 0.991] | +0.477 [0.368, 0.608] |

**Pre-registered sanity conditions (E33): all pass.**

| Condition | Observed |
|---|---|
| AUPRC CI low > 10 × prevalence (0.017) | 0.054 |
| AUROC CI low > 0.5 | 0.674 |
| Loss reduction ≥ 5% | 17.5% |
| Distinct scores ≥ 100 | 27,465 |
| Retraining and replay | bitwise identical |
| Aer noiseless replay of 1,024 rows | agrees |

**So the VQC learns real fraud signal, but far less than classical models given identical inputs and data.** Training-data-only diagnostics locate the gap in the quantum model (O24):

1. **Training loss floor.** Training BCE 0.604 is above the constant-20% predictor (0.500), even though training AUPRC is 0.745. The parity readout has no trainable bias or scale.
2. **Saturation.** 123 of 213 training frauds are clipped on all four features, leaving only 91 distinct fraud angle vectors. On `vqc_val`, 22 of 47 frauds share one score for this reason.
3. **Aliasing.** The ZZ map's phase 2x has period π, so x and x + π alias on [−π, π].
4. **Not information loss.** The encoding keeps the signal: classical models on unclipped inputs gain only 0.006–0.010 AUPRC (CIs include 0).

Threshold metrics are exploratory (threshold tuned and reported on `vqc_val`). Raw VQC scores spread over 0.1–0.9 with near-zero fraud rates outside the 0.8–0.9 bin (Brier 0.241, ECE 0.474): they are **not** probabilities at the 0.17% deployment prevalence.

### 3.8 Phase 3A-R: pre-registered repair (results)

**Registration:** [`PREREG_P3AR.md`](PREREG_P3AR.md), committed before any run.

**Design:** 10 candidates (4 encodings × depth 1/2 × parity, plus 2 first-qubit-Z variants), cross-validated inside `vqc_train`:
- 5 group-aware stratified folds, each 25,534–25,536 rows with 42–43 frauds;
- per fold, train on all fold-train frauds + 4 legitimate per fraud; evaluate on the held-out fold at natural prevalence;
- 3 identical restart seeds per candidate; COBYLA with 1,000 evaluations.

**Encoding diagnostics (`vqc_train`):**

| Encoding | Fraud values clipped | Frauds sharing a vector | 3A alias probe | Material state collisions in probe |
|---|---:|---:|---|---:|
| E0 (±3, [−π, π]) | 75.0% | 123 / 213 | fidelity 1.0 | 7,553 |
| E1 (±3, [−π/4, π/4]) | 75.0% | 123 / 213 | not representable | 7,678 |
| E2 (±5) | 58.8% | 80 / 213 | not representable | 3,366 |
| **E3 (±15)** | **9.6%** | **2 / 213** | not representable | **1** |

"Material state collisions" are probe pairs whose inputs differ by at least 1 IQR but whose feature-map states have fidelity ≥ 0.999.

**CV (mean held-out AUPRC / AUROC):**

| Encoding | Depth 1 | Depth 2 | Note |
|---|---|---|---|
| E0 | 0.217 / 0.81 | 0.107 / 0.80 | control |
| E1 | 0.247 / 0.95 | 0.558 / 0.95 | ineligible by rule |
| E2 | 0.344 / 0.95 | 0.483 / 0.96 | |
| **E3** | 0.409 / 0.95 | **0.573 / 0.95** | |

First-qubit Z observable: 0.012 (E2) and 0.017 (E3). Restart spread reaches 0.27 in AUPRC.

**Selected:** `e3-r2-par`. Transpiled circuit: depth 35, 18 CX, 28 SX, 88 operations, 12 trainable parameters.

**Final training:** on the fixed 3A subset (hash `4e04298d…`). All 3 restarts hit the budget; the kept restart (2) reached BCE 0.263. Retraining is bitwise identical.

**One-time `vqc_val` evaluation** (paired bootstrap on the Phase 2 resamples):

| Model (same 1,065 rows) | AUPRC | ROC-AUC | Δ AUPRC |
|---|---|---|---|
| P3A-original (E0 angles) | 0.104 [0.054, 0.166] | 0.766 | — |
| **P3A-R (E3 angles)** | **0.507 [0.363, 0.661]** | **0.957** | +0.403 [0.271, 0.546] vs P3A-original |
| LR (E3 angles) | 0.620 [0.482, 0.784] | 0.946 | +0.113 [0.021, 0.214] vs P3A-R |
| RF (E3 angles) | 0.608 [0.476, 0.762] | 0.970 | +0.100 [−0.021, 0.216] vs P3A-R |
| HGB (E3 angles) | 0.592 [0.456, 0.753] | 0.960 | +0.085 [−0.048, 0.213] vs P3A-R |

All pre-registered sanity conditions pass. Calibration of P3A-R: Brier 0.0093, ECE 0.083 (P3A-original: 0.241 and 0.474). It is still trained at 20% prevalence, so its scores are not deployment probabilities.

**P3A-R is the frozen base model for Phase 3B** (PI rule: materially healthier).

### 3.9 Phase 3B: controlled-noise characterization (results)

**Registration:** [`PREREG_P3B.md`](PREREG_P3B.md), committed and pushed (`b5a14bb`) before any noisy simulation. Rules were executed as registered; the implementation details and one wording erratum are disclosed in its execution record.

**Scope:**
- **Models:** frozen P3A-R (primary) and P3A-original (exploratory pilot-model contrast). Both artifacts were verified byte-identical before and after the run.
- **Data:** `vqc_val` only (28,372 rows, 47 frauds; access phase `phase3b`).
- **Excluded:** mitigation, Q-TRACE components and retraining.

**Engine ([ENG] E39–E40):**
- The transpiled parametrized circuit (P3A-R: 18 CX, 28 SX, 42 RZ, depth 35) is run on Aer `density_matrix` with per-row parameter binds.
- Readout confusion is applied classically to the exact distribution.
- Aer clean agrees with the frozen exact engine to max |Δz| = 1.9e-15 (P3A-R) and 1.3e-15 (P3A-original). The registered tolerance is 1e-10.
- The clean references reproduce the 3A-R evaluation exactly: P3A-R AUPRC 0.507 [0.363, 0.661], frozen τ = 0.3771.

**Label abbreviations:** RP ranking_preserving, RD ranking_distortion, CD calibration_distortion, TD threshold_distortion, DD discrimination_degradation.

**Exact (Stage 1) diagnostics, P3A-R (primary).** Δ = exact noisy − exact clean, with a paired 95% interval on the shared Phase 2 resamples. Ranking metrics are computed against the clean scores; crossings are at the frozen clean τ. The ro-sym rows are negative controls and AR rows are *synthetic asymmetric readout stress-test profiles* (not device calibration).

| Condition | AUPRC | ΔAUPRC [95% CI] | ΔAUROC [95% CI] | Spearman | Kendall | Top-47 | ΔBrier | ΔECE | Cross τ (all / fraud) | A13 labels |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| clean | 0.507 | — | — | — | — | — | Brier 0.0093 | ECE 0.083 | τ = 0.3771 | — |
| dep-low | 0.507 | -0.000 [-0.002, +0.003] | +0.0001 [-0.0001, +0.0004] | 0.9999 | 0.993 | 1.000 | +0.0080 | +0.040 | 0.0002 / 0.000 | RD, CD |
| dep-medium | 0.506 | -0.001 [-0.004, +0.003] | +0.0003 [-0.0001, +0.0007] | 0.9997 | 0.986 | 1.000 | +0.0182 | +0.077 | 0.0007 / 0.043 | RD, CD |
| dep-high | 0.506 | -0.001 [-0.010, +0.008] | +0.0005 [-0.0002, +0.0015] | 0.9987 | 0.971 | 1.000 | +0.0452 | +0.147 | 0.0025 / 0.085 | RD, CD, TD |
| ro-sym-low | 0.507 | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | 1.0000 | 1.000 | 1.000 | +0.0029 | +0.016 | 0.0000 / 0.000 | RP, CD |
| ro-sym-medium | 0.507 | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | 1.0000 | 1.000 | 1.000 | +0.0139 | +0.063 | 0.0005 / 0.043 | RP, CD |
| ro-sym-high | 0.507 | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | 1.0000 | 1.000 | 1.000 | +0.0433 | +0.143 | 0.0017 / 0.085 | RP, CD, TD |
| th-low | 0.508 | +0.001 [-0.001, +0.005] | -0.0002 [-0.0008, +0.0002] | 0.9999 | 0.991 | 1.000 | +0.0029 | +0.016 | 0.0000 / 0.000 | RD, CD |
| th-medium | 0.509 | +0.002 [-0.001, +0.007] | -0.0003 [-0.0014, +0.0004] | 0.9995 | 0.981 | 1.000 | +0.0052 | +0.028 | 0.0002 / 0.000 | RD, CD |
| th-high | 0.510 | +0.003 [-0.003, +0.010] | -0.0007 [-0.0029, +0.0008] | 0.9981 | 0.963 | 0.979 | +0.0122 | +0.056 | 0.0004 / 0.021 | RD, CD |
| comb-low | 0.508 | +0.001 [-0.002, +0.005] | -0.0000 [-0.0004, +0.0002] | 0.9999 | 0.990 | 1.000 | +0.0159 | +0.069 | 0.0006 / 0.043 | RD, CD |
| comb-medium | 0.509 | +0.002 [-0.004, +0.008] | -0.0001 [-0.0008, +0.0005] | 0.9995 | 0.981 | 0.979 | +0.0452 | +0.147 | 0.0023 / 0.085 | RD, CD, TD |
| comb-high | 0.504 | -0.003 [-0.016, +0.009] | -0.0003 [-0.0017, +0.0010] | 0.9977 | 0.960 | 0.979 | +0.1120 | +0.263 | 0.0479 / 0.170 | RD, CD, TD |
| ar-005 | 0.511 | +0.004 [+0.000, +0.009] | +0.0004 [-0.0005, +0.0020] | 0.9997 | 0.985 | 1.000 | +0.0028 | +0.016 | 0.0000 / 0.000 | RD, CD |
| ar-020 | 0.514 | +0.007 [-0.002, +0.018] | +0.0015 [-0.0022, +0.0074] | 0.9943 | 0.939 | 0.979 | +0.0137 | +0.062 | 0.0004 / 0.043 | RD, CD |
| ar-050 | 0.519 | +0.012 [-0.003, +0.029] | +0.0025 [-0.0057, +0.0150] | 0.9609 | 0.837 | 0.979 | +0.0428 | +0.142 | 0.0013 / 0.064 | RD |

**Negative control** (exact symmetric readout = affine contraction (1 − 2p)⁴; every check passes; stored in `p3b_negative_control.csv`):

| Model | Condition | (1−2p)⁴ | max residual | abs ΔAUPRC | abs ΔAUROC | 1 − ρ | Pass |
|---|---|---:|---:|---:|---:|---:|---|
| p3a_r | ro-sym-low | 0.960596 | 4.441e-16 | 0.000e+00 | 0.000e+00 | 0.000e+00 | True |
| p3a_r | ro-sym-medium | 0.849347 | 4.441e-16 | 0.000e+00 | 0.000e+00 | 0.000e+00 | True |
| p3a_r | ro-sym-high | 0.656100 | 4.441e-16 | 0.000e+00 | 0.000e+00 | 0.000e+00 | True |
| p3a_original | ro-sym-low | 0.960596 | 2.220e-16 | 0.000e+00 | 0.000e+00 | 1.110e-16 | True |
| p3a_original | ro-sym-medium | 0.849347 | 2.776e-16 | 0.000e+00 | 1.110e-16 | 1.315e-13 | True |
| p3a_original | ro-sym-high | 0.656100 | 2.776e-16 | 0.000e+00 | 0.000e+00 | 1.110e-16 | True |

**E08 sampler validation** (first 256 rows; direct Aer shots against the cached exact distribution; all five registered tests pass for every profile; Stage 2 therefore ran):

| Profile | mean u | var u | χ² p (dof) | \|Δ mean p\| / SE | TVD ratio | KS p | Pass |
|---|---:|---:|---|---:|---:|---:|---|
| clean | +0.105 | 0.954 | 0.538 (2959) | 1.61 | 1.020 | 0.022 | yes |
| ar-050 | -0.043 | 0.921 | 0.178 (3840) | 0.58 | 0.986 | 0.626 | yes |
| th-high | +0.039 | 1.119 | 0.328 (3833) | 0.60 | 0.997 | 0.211 | yes |
| comb-high | -0.013 | 0.882 | 0.147 (3840) | 0.21 | 1.003 | 0.482 | yes |

**Stage 2 finite-shot pilot** (P3A-R; 1,024 shots × 20 replicates; O07 pilot only, not the final protocol). Δ is finite-shot noisy minus **finite-shot clean of the same replicate**. Finite-shot scores lie on a 1/1,024 grid (220–388 distinct values per replicate).

| Condition | AUPRC mean (SD) | ΔAUPRC vs shot-clean: mean [q05, q95] | ΔAUROC vs shot-clean: mean [q05, q95] | Spearman vs exact clean: mean | Exact ΔAUPRC |
|---|---|---|---|---:|---:|
| clean | 0.506 (0.008) | +0.0000 [+0.000, +0.000] | +0.0000 [+0.000, +0.000] | 0.956 | +0.0000 |
| dep-low | 0.504 (0.009) | -0.0020 [-0.028, +0.017] | -0.0010 [-0.008, +0.010] | 0.923 | -0.0000 |
| dep-medium | 0.504 (0.007) | -0.0023 [-0.020, +0.017] | -0.0014 [-0.015, +0.008] | 0.890 | -0.0006 |
| dep-high | 0.501 (0.010) | -0.0046 [-0.021, +0.010] | -0.0052 [-0.017, +0.006] | 0.816 | -0.0013 |
| ro-sym-low | 0.502 (0.010) | -0.0043 [-0.026, +0.011] | +0.0010 [-0.011, +0.012] | 0.942 | +0.0000 |
| ro-sym-medium | 0.506 (0.009) | -0.0002 [-0.013, +0.010] | +0.0005 [-0.012, +0.011] | 0.901 | +0.0000 |
| ro-sym-high | 0.501 (0.015) | -0.0055 [-0.034, +0.015] | -0.0055 [-0.029, +0.006] | 0.810 | +0.0000 |
| th-low | 0.506 (0.009) | -0.0005 [-0.014, +0.012] | +0.0008 [-0.009, +0.009] | 0.943 | +0.0013 |
| th-medium | 0.507 (0.011) | +0.0006 [-0.020, +0.023] | -0.0014 [-0.012, +0.009] | 0.933 | +0.0022 |
| th-high | 0.505 (0.010) | -0.0011 [-0.022, +0.013] | -0.0008 [-0.009, +0.007] | 0.908 | +0.0028 |
| comb-low | 0.503 (0.012) | -0.0036 [-0.024, +0.012] | +0.0002 [-0.012, +0.012] | 0.897 | +0.0011 |
| comb-medium | 0.500 (0.015) | -0.0059 [-0.033, +0.028] | -0.0022 [-0.018, +0.010] | 0.812 | +0.0015 |
| comb-high | 0.474 (0.029) | -0.0318 [-0.073, +0.003] | -0.0066 [-0.025, +0.010] | 0.614 | -0.0026 |
| ar-005 | 0.507 (0.009) | +0.0010 [-0.023, +0.022] | +0.0009 [-0.003, +0.007] | 0.942 | +0.0036 |
| ar-020 | 0.511 (0.010) | +0.0048 [-0.016, +0.023] | -0.0021 [-0.013, +0.008] | 0.895 | +0.0070 |
| ar-050 | 0.506 (0.018) | +0.0003 [-0.032, +0.026] | -0.0003 [-0.009, +0.013] | 0.775 | +0.0122 |

**G1 (registered rule; primary model, exact, negative controls excluded): CONDITIONAL PASS.**
- **Why not PASS:** no condition is labelled `discrimination_degradation`; every ΔAUPRC and ΔAUROC interval has an upper bound above 0. No `ranking_distortion` reaches the top-47 criterion either: the minimum overlap is 0.979, i.e. 46 of 47.
- **Why CONDITIONAL:** all 12 non-control conditions carry `ranking_distortion` (driven by Kendall τ < 0.995, i.e. reordering in the dense legitimate bulk). 11 carry `calibration_distortion`. 3 carry `threshold_distortion`: dep-high, comb-medium and comb-high.
- **Severity trends:** all four families show one (Spearman non-increasing; depolarizing also ΔAUPRC).

**Exploratory pilot-model contrast (P3A-original; never H1 evidence).**

| Condition | AUPRC | ΔAUPRC [95% CI] | ΔAUROC [95% CI] | Spearman | Kendall | Top-47 | ΔBrier | ΔECE | Cross τ (all / fraud) | A13 labels |
|---|---:|---|---|---:|---:|---:|---:|---:|---|---|
| clean | 0.104 | — | — | — | — | — | Brier 0.2410 | ECE 0.474 | τ = 0.8257 | — |
| dep-low | 0.104 | -0.000 [-0.000, +0.000] | +0.0000 [-0.0003, +0.0003] | 1.0000 | 0.996 | 0.979 | -0.0004 | +0.002 | 0.0030 / 0.468 | RP, TD |
| dep-medium | 0.102 | -0.002 [-0.005, -0.000] | +0.0000 [-0.0006, +0.0007] | 0.9999 | 0.991 | 0.979 | -0.0006 | +0.004 | 0.0034 / 0.468 | RD, TD |
| dep-high | 0.102 | -0.002 [-0.007, +0.002] | -0.0000 [-0.0014, +0.0015] | 0.9995 | 0.981 | 0.915 | -0.0006 | +0.007 | 0.0036 / 0.468 | RD, TD |
| ro-sym-low | 0.104 | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | 1.0000 | 1.000 | 1.000 | -0.0003 | +0.001 | 0.0028 / 0.468 | RP, TD |
| ro-sym-medium | 0.104 | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | 1.0000 | 1.000 | 1.000 | -0.0007 | +0.004 | 0.0034 / 0.468 | RP, TD |
| ro-sym-high | 0.104 | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | 1.0000 | 1.000 | 1.000 | -0.0005 | +0.008 | 0.0036 / 0.468 | RP, TD |
| th-low | 0.104 | +0.000 [+0.000, +0.000] | +0.0002 [-0.0004, +0.0007] | 1.0000 | 0.995 | 0.979 | -0.0003 | +0.001 | 0.0027 / 0.468 | RD, TD |
| th-medium | 0.106 | +0.002 [+0.000, +0.006] | +0.0003 [-0.0007, +0.0014] | 0.9999 | 0.990 | 0.979 | -0.0005 | +0.001 | 0.0029 / 0.468 | RD, TD |
| th-high | 0.191 | +0.086 [+0.047, +0.145] | +0.0014 [-0.0007, +0.0035] | 0.9994 | 0.979 | 0.532 | -0.0008 | +0.003 | 0.0032 / 0.468 | RD, TD |
| comb-low | 0.105 | +0.001 [-0.000, +0.004] | +0.0002 [-0.0005, +0.0010] | 0.9999 | 0.992 | 0.979 | -0.0007 | +0.003 | 0.0034 / 0.468 | RD, TD |
| comb-medium | 0.104 | +0.000 [-0.004, +0.005] | +0.0003 [-0.0012, +0.0018] | 0.9997 | 0.984 | 0.915 | -0.0007 | +0.008 | 0.0036 / 0.468 | RD, TD |
| comb-high | 0.178 | +0.074 [+0.039, +0.127] | +0.0014 [-0.0015, +0.0044] | 0.9985 | 0.967 | 0.553 | +0.0013 | +0.014 | 0.0036 / 0.468 | RD, CD, TD |
| ar-005 | 0.105 | +0.001 [-0.000, +0.004] | -0.0005 [-0.0011, +0.0003] | 0.9999 | 0.994 | 0.979 | -0.0005 | +0.001 | 0.0028 / 0.468 | RD, TD |
| ar-020 | 0.198 | +0.093 [+0.051, +0.153] | -0.0011 [-0.0039, +0.0018] | 0.9991 | 0.974 | 0.511 | -0.0015 | +0.003 | 0.0034 / 0.468 | RD, TD |
| ar-050 | 0.243 | +0.138 [+0.077, +0.220] | -0.0042 [-0.0114, +0.0035] | 0.9935 | 0.931 | 0.383 | -0.0023 | +0.006 | 0.0036 / 0.468 | RD, TD |

**Runtime benchmark** (dev run `20261007T165007Z-a9b5c110`, Apple M5 Pro; `results/raw/phase3b_noise/<run>/runtime.json`):

| Item | Time |
|---|---|
| Exact clean, P3A-R / P3A-original (28,372 rows) | 3.6 s / 3.1 s (0.13 / 0.11 ms per row) |
| Exact gate-noise condition, P3A-R / P3A-original | 7.6–7.8 s / 6.4–6.5 s (≈ 0.27 / 0.23 ms per row) |
| Stage 1 total: both models, 2 × 10 Aer runs, plus 2 × 15 conditions | 146 s |
| Diagnostics: 15 conditions × 1,000 paired resamples, parallel | 15.6 s / 14.3 s |
| E08: 4 profiles × 256 rows × 1,024 direct shots | 0.47 s |
| Stage 2 sampling: 16 × 20 multinomial draws of 28,372 rows | 8.4 s (26 ms per draw) + 2.5 s of metrics |
| Whole run | 188 s; peak resident memory of the main process 895 MiB |

**Findings (effect sizes; 47 frauds, so intervals are wide):**
1. **Exact noise at the [RR] anchor severities does not measurably reduce P3A-R discrimination.**
   - For the gate-noise families, |ΔAUPRC| ≤ 0.003 and |ΔAUROC| ≤ 0.0007. Every interval contains 0, except ar-005, whose interval is positive.
   - No condition is labelled DD.
2. **Noise reorders the dense legitimate bulk but not the fraud head.**
   - Kendall τ is 0.96–0.99 across the anchor families and falls to 0.84 for ar-050.
   - Spearman is ≥ 0.9977 for the anchor families.
   - Top-47 overlap is ≥ 46/47 throughout.
3. **The dominant exact effect is score contraction toward 0.5,** visible as calibration and threshold distortion:
   - Brier rises from 0.0093 clean to 0.121 at comb-high, and ECE from 0.083 to 0.346.
   - At comb-high, 4.8% of all rows and 17% of frauds cross the frozen τ.
   - Precision at τ falls from 0.53 to 0.03 while recall rises from 0.70 to 0.87.
4. **Synthetic asymmetric readout is the only family that is clearly non-affine.**
   - ar-050: Spearman 0.961, Kendall 0.837.
   - Its ΔAUPRC is positive and its interval includes 0.
5. **Finite shots dominate ranking change (pilot).**
   - Even finite-shot clean scores have Spearman 0.956 against exact clean.
   - Contraction amplifies relative shot noise. At comb-high, Spearman falls to 0.61 and the mean ΔAUPRC against shot-clean is −0.032 (5–95%: −0.073 to +0.003), against −0.003 exact.
   - Under finite shots the symmetric-readout controls also vary. This is expected and is not a negative-control failure.
6. **Contrast (exploratory).**
   - P3A-original's top ranks are fragile: top-47 overlap is 0.38–0.55 at th-high, comb-high, ar-020 and ar-050.
   - Its AUPRC *rises* under those conditions, by +0.07 to +0.14 with intervals that exclude 0.
   - Its frozen τ sits on a mass of collapsed fraud scores, so 22 of 47 frauds cross τ under every condition, including the smallest symmetric readout. This is consistent with its known encoding defects.

### 3.10 Phase 4: mitigation characterization (results)

**Registration:** [`PREREG_P4.md`](PREREG_P4.md), committed and pushed (`9d377d0`) before any mitigation was run on `vqc_val`. Everything ran as registered; the disclosures are in its execution record.

**Scope:**
- **Model and data:** frozen P3A-R only (artifact byte-identical before and after); frozen τ = 0.37708 for every action; `vqc_val` only (access phase `phase4`).
- **Contexts:** 8 conditions × 2 shot arms (1,024 and 4,096 shots per circuit) × 20 replicates.
- **Actions:** A0 None, A1 readout mitigation (calibration counts only), A2 ZNE (global folding at 1/3/5, linear), A3 combined. RM3 is the shot-matched None baseline.
- **Diagnostics only:** RM9, the oracle readout inversion and Richardson extrapolation.
- **Not done:** no Q-TRACE, no model pool, no PEC.

**Validation (all passed before the finite-shot stage):**
- The frozen τ reproduces exactly.
- Clean folded and unfolded distributions agree to 2.4e-15 on all 28,372 rows.
- Mean |z| strictly decreases with λ in every gate-noise condition: dep-high 0.537 / 0.225 / 0.095; comb-high 0.305 / 0.094 / 0.027.
- λ = 1 metrics reproduce `p3b_exact_metrics.csv` (max |Δ| = 5.0e-10).
- **Exact negative controls:**
  - A1 with exact calibration recovers clean under ro-sym-high, ar-020 and ar-050 (≤ 8.9e-16), with |ΔAUPRC| = |ΔAUROC| = 0 under symmetric readout.
  - A2 is the identity under clean and under pure readout (≤ 1.4e-15).
  - A1 is the identity under clean.
- **E08 on folded circuits** (comb-high, λ = 3 and 5), all five tests passing:
  - λ = 3: mean u 0.093, var 0.955, χ² p 0.986, TVD ratio 0.983, KS p 0.30;
  - λ = 5: mean u 0.004, var 1.021, χ² p 0.636, TVD ratio 0.995, KS p 0.70.
- **Calibration circuits** (100,000 direct Aer shots): χ² p 0.03–0.98.

**Circuits and costs** (per logical inference, S = shots per circuit):

| | CX | Noisy 1q | Depth (noisy depth) | Shots | Circuits | CX-shots |
|---|---|---|---|---|---|---|
| λ = 1 / 3 / 5 | 18 / 54 / 90 | 28 / 84 / 140 | 35 / 133 / 231 (21 / 63 / 105) | | | |
| A0 | | | | S | 1 | 18S |
| A1 | | | | S + 2S/28,372 | 1 + 2/28,372 | 18S |
| A2 | | | | 3S | 3 | 162S |
| A3 | | | | 3S + 2S/28,372 | 3 + 2/28,372 | 162S |
| RM3 / RM9 | | | | 3S / 9S | 1 | 54S / 162S |

Calibration is two circuits per batch: |0000⟩ with no gates, and |1111⟩ with 4 `x` gates.

**Exact mechanistic reference** (no shots; one-stage paired bootstrap; `p4_exact_diagnostics.csv`):

| Condition | Vector | AUPRC | ΔAUPRC vs A0 [95%] | Brier | ECE | F1@τ | max\|z − z_clean\| |
|---|---|---|---|---|---|---|---|
| clean | A0 | 0.5070 | — | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A1 | 0.5070 | +0.0000 [+0.0000, +0.0000] | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A2 | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A3 | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A1-oracle | 0.5070 | +0.0000 [+0.0000, +0.0000] | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A2-rich | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A3-rich | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
| ro-sym-high | A0 | 0.5070 | — | 0.0527 | 0.226 | 0.468 | 3.20e-01 |
|  | A1 | 0.5070 | +0.0000 [+0.0000, +0.0000] | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A2 | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0527 | 0.226 | 0.468 | 3.20e-01 |
|  | A3 | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A1-oracle | 0.5070 | +0.0000 [+0.0000, +0.0000] | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A2-rich | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0527 | 0.226 | 0.468 | 3.20e-01 |
|  | A3-rich | 0.5070 | +0.0000 [-0.0000, +0.0000] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
| ar-020 | A0 | 0.5140 | — | 0.0230 | 0.145 | 0.588 | 1.47e-01 |
|  | A1 | 0.5070 | -0.0070 [-0.0184, +0.0016] | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A2 | 0.5140 | +0.0000 [+0.0000, +0.0000] | 0.0230 | 0.145 | 0.588 | 1.47e-01 |
|  | A3 | 0.5070 | -0.0070 [-0.0184, +0.0016] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A1-oracle | 0.5070 | -0.0070 [-0.0184, +0.0016] | 0.0093 | 0.083 | 0.606 | 0.00e+00 |
|  | A2-rich | 0.5140 | +0.0000 [-0.0000, +0.0000] | 0.0230 | 0.145 | 0.588 | 1.47e-01 |
|  | A3-rich | 0.5070 | -0.0070 [-0.0184, +0.0016] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
| ar-050 | A0 | 0.5192 | — | 0.0521 | 0.225 | 0.497 | 3.32e-01 |
|  | A1 | 0.5070 | -0.0122 [-0.0291, +0.0035] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A2 | 0.5192 | +0.0000 [-0.0000, +0.0000] | 0.0521 | 0.225 | 0.497 | 3.32e-01 |
|  | A3 | 0.5070 | -0.0122 [-0.0291, +0.0035] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A1-oracle | 0.5070 | -0.0122 [-0.0291, +0.0035] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
|  | A2-rich | 0.5192 | +0.0000 [-0.0000, +0.0000] | 0.0521 | 0.225 | 0.497 | 3.32e-01 |
|  | A3-rich | 0.5070 | -0.0122 [-0.0291, +0.0035] | 0.0093 | 0.083 | 0.593 | 0.00e+00 |
| dep-high | A0 | 0.5057 | — | 0.0546 | 0.230 | 0.411 | 3.27e-01 |
|  | A1 | 0.5044 | -0.0014 [-0.0048, +0.0000] | 0.0538 | 0.228 | 0.416 | 3.23e-01 |
|  | A2 | 0.5055 | -0.0003 [-0.0037, +0.0028] | 0.0379 | 0.190 | 0.526 | 2.37e-01 |
|  | A3 | 0.5046 | -0.0011 [-0.0044, +0.0008] | 0.0372 | 0.188 | 0.533 | 2.33e-01 |
|  | A1-oracle | 0.5057 | +0.0000 [+0.0000, +0.0000] | 0.0546 | 0.230 | 0.411 | 3.27e-01 |
|  | A2-rich | 0.5066 | +0.0008 [-0.0063, +0.0092] | 0.0161 | 0.118 | 0.579 | 7.75e-02 |
|  | A3-rich | 0.5068 | +0.0011 [-0.0062, +0.0095] | 0.0156 | 0.116 | 0.579 | 7.21e-02 |
| th-high | A0 | 0.5098 | — | 0.0215 | 0.139 | 0.567 | 1.27e-01 |
|  | A1 | 0.5092 | -0.0006 [-0.0032, +0.0000] | 0.0213 | 0.138 | 0.567 | 1.25e-01 |
|  | A2 | 0.5093 | -0.0005 [-0.0052, +0.0037] | 0.0130 | 0.103 | 0.600 | 4.63e-02 |
|  | A3 | 0.5086 | -0.0012 [-0.0055, +0.0018] | 0.0128 | 0.102 | 0.600 | 4.41e-02 |
|  | A1-oracle | 0.5098 | +0.0000 [+0.0000, +0.0000] | 0.0215 | 0.139 | 0.567 | 1.27e-01 |
|  | A2-rich | 0.5088 | -0.0010 [-0.0081, +0.0056] | 0.0098 | 0.085 | 0.593 | 7.49e-03 |
|  | A3-rich | 0.5085 | -0.0014 [-0.0085, +0.0055] | 0.0096 | 0.084 | 0.593 | 5.59e-03 |
| comb-medium | A0 | 0.5086 | — | 0.0545 | 0.230 | 0.428 | 3.28e-01 |
|  | A1 | 0.5084 | -0.0001 [-0.0008, +0.0001] | 0.0347 | 0.181 | 0.541 | 2.19e-01 |
|  | A2 | 0.5067 | -0.0019 [-0.0061, +0.0000] | 0.0391 | 0.193 | 0.533 | 2.46e-01 |
|  | A3 | 0.5068 | -0.0018 [-0.0059, +0.0001] | 0.0211 | 0.138 | 0.550 | 1.22e-01 |
|  | A1-oracle | 0.5086 | +0.0000 [+0.0000, +0.0000] | 0.0351 | 0.182 | 0.541 | 2.21e-01 |
|  | A2-rich | 0.5079 | -0.0007 [-0.0056, +0.0042] | 0.0262 | 0.155 | 0.551 | 1.63e-01 |
|  | A3-rich | 0.5073 | -0.0012 [-0.0067, +0.0042] | 0.0111 | 0.093 | 0.600 | 2.34e-02 |
| comb-high | A0 | 0.5045 | — | 0.1213 | 0.346 | 0.056 | 5.88e-01 |
|  | A1 | 0.5034 | -0.0011 [-0.0043, +0.0000] | 0.0716 | 0.264 | 0.291 | 4.05e-01 |
|  | A2 | 0.5042 | -0.0003 [-0.0014, +0.0000] | 0.1062 | 0.323 | 0.121 | 5.38e-01 |
|  | A3 | 0.5029 | -0.0016 [-0.0061, +0.0000] | 0.0545 | 0.229 | 0.404 | 3.27e-01 |
|  | A1-oracle | 0.5045 | +0.0000 [+0.0000, +0.0000] | 0.0726 | 0.266 | 0.287 | 4.09e-01 |
|  | A2-rich | 0.5073 | +0.0028 [-0.0040, +0.0123] | 0.0727 | 0.267 | 0.300 | 4.11e-01 |
|  | A3-rich | 0.5067 | +0.0022 [-0.0044, +0.0106] | 0.0224 | 0.142 | 0.541 | 1.32e-01 |

**Exact readings:**
- **Readout mitigation is exact under pure readout noise.** It restores the clean scores to machine precision; because the noise was a contraction, it does not improve discrimination.
- **H4.2 holds exactly.** Under ar-020 and ar-050, A1 *lowers* AUPRC back to its clean value (0.519 → 0.507), because the non-affine asymmetric readout had slightly raised it.
- **ZNE (linear) only partly undoes gate-noise contraction.** It recovers this share of the exact Brier gap to clean: dep-high 37%, th-high 70%, comb-medium 34%, comb-high 13%. Richardson (diagnostic only) recovers 43–97%, at 5.2× the shot variance.
- **Knife-edge row.** One transaction's score defines the max-F1 τ. Exact ZNE arithmetic moves it across τ by about 1e-16 under clean and pure readout, so the exact F1@τ for A2/A3 there is 0.593 rather than 0.606. This affects 1 of 28,372 rows; scores agree with clean to 1.4e-15.

**Finite shots, 1,024 per circuit: Table A** (`p4_summary.csv`; mean of 20 replicates; RM9 and diagnostics in the file):

| Condition | Action | AUPRC (SD) | AUROC | Brier | ECE | Prec@τ | Rec@τ | F1@τ | Cross τ (all / fraud) | Spearman | Kendall | Top-47 | Shots/inference |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clean | A0 | 0.505 (0.012) | 0.9556 | 0.0094 | 0.083 | 0.515 | 0.676 | 0.584 | 0.03% / 4.1% | 0.955 | 0.825 | 0.934 | 1,024 |
|  | A1 | 0.505 (0.012) | 0.9556 | 0.0094 | 0.083 | 0.515 | 0.676 | 0.584 | 0.03% / 4.1% | 0.955 | 0.825 | 0.934 | 1,024 |
|  | A2 | 0.502 (0.015) | 0.9555 | 0.0094 | 0.083 | 0.507 | 0.671 | 0.578 | 0.03% / 5.2% | 0.938 | 0.788 | 0.927 | 3,072 |
|  | A3 | 0.502 (0.015) | 0.9555 | 0.0094 | 0.083 | 0.507 | 0.671 | 0.578 | 0.03% / 5.2% | 0.938 | 0.788 | 0.927 | 3,072 |
|  | RM3 | 0.509 (0.006) | 0.9564 | 0.0094 | 0.083 | 0.524 | 0.676 | 0.590 | 0.01% / 2.7% | 0.984 | 0.895 | 0.962 | 3,072 |
| ro-sym-high | A0 | 0.502 (0.013) | 0.9534 | 0.0528 | 0.226 | 0.292 | 0.779 | 0.425 | 0.22% / 7.7% | 0.810 | 0.625 | 0.902 | 1,024 |
|  | A1 | 0.502 (0.013) | 0.9528 | 0.0109 | 0.090 | 0.505 | 0.668 | 0.575 | 0.04% / 6.8% | 0.817 | 0.629 | 0.898 | 1,024 |
|  | A2 | 0.501 (0.019) | 0.9513 | 0.0529 | 0.226 | 0.281 | 0.776 | 0.412 | 0.24% / 7.3% | 0.760 | 0.570 | 0.880 | 3,072 |
|  | A3 | 0.500 (0.019) | 0.9511 | 0.0110 | 0.090 | 0.501 | 0.676 | 0.575 | 0.05% / 6.1% | 0.768 | 0.578 | 0.880 | 3,072 |
|  | RM3 | 0.508 (0.008) | 0.9561 | 0.0527 | 0.226 | 0.312 | 0.779 | 0.445 | 0.20% / 7.7% | 0.916 | 0.755 | 0.945 | 3,072 |
| ar-020 | A0 | 0.510 (0.008) | 0.9526 | 0.0231 | 0.145 | 0.475 | 0.736 | 0.577 | 0.04% / 4.9% | 0.895 | 0.726 | 0.926 | 1,024 |
|  | A1 | 0.508 (0.009) | 0.9509 | 0.0098 | 0.085 | 0.516 | 0.673 | 0.584 | 0.03% / 4.6% | 0.904 | 0.737 | 0.926 | 1,024 |
|  | A2 | 0.510 (0.010) | 0.9531 | 0.0232 | 0.145 | 0.465 | 0.726 | 0.567 | 0.05% / 5.1% | 0.861 | 0.678 | 0.918 | 3,072 |
|  | A3 | 0.506 (0.011) | 0.9516 | 0.0099 | 0.085 | 0.507 | 0.665 | 0.575 | 0.03% / 5.4% | 0.872 | 0.693 | 0.916 | 3,072 |
|  | RM3 | 0.514 (0.005) | 0.9562 | 0.0230 | 0.145 | 0.479 | 0.739 | 0.581 | 0.04% / 4.1% | 0.956 | 0.823 | 0.959 | 3,072 |
| ar-050 | A0 | 0.503 (0.009) | 0.9546 | 0.0523 | 0.225 | 0.331 | 0.772 | 0.463 | 0.17% / 7.0% | 0.774 | 0.586 | 0.904 | 1,024 |
|  | A1 | 0.496 (0.009) | 0.9521 | 0.0109 | 0.090 | 0.501 | 0.674 | 0.575 | 0.03% / 5.1% | 0.820 | 0.633 | 0.911 | 1,024 |
|  | A2 | 0.501 (0.012) | 0.9523 | 0.0524 | 0.225 | 0.318 | 0.771 | 0.450 | 0.18% / 7.1% | 0.723 | 0.534 | 0.870 | 3,072 |
|  | A3 | 0.492 (0.011) | 0.9501 | 0.0111 | 0.090 | 0.488 | 0.660 | 0.560 | 0.04% / 7.0% | 0.772 | 0.582 | 0.887 | 3,072 |
|  | RM3 | 0.512 (0.005) | 0.9556 | 0.0522 | 0.225 | 0.350 | 0.769 | 0.481 | 0.15% / 6.7% | 0.880 | 0.702 | 0.930 | 3,072 |
| dep-high | A0 | 0.497 (0.011) | 0.9501 | 0.0547 | 0.230 | 0.270 | 0.783 | 0.401 | 0.26% / 8.1% | 0.816 | 0.632 | 0.903 | 1,024 |
|  | A1 | 0.497 (0.010) | 0.9499 | 0.0540 | 0.228 | 0.271 | 0.783 | 0.403 | 0.26% / 8.1% | 0.817 | 0.630 | 0.905 | 1,024 |
|  | A2 | 0.497 (0.013) | 0.9506 | 0.0382 | 0.190 | 0.357 | 0.754 | 0.485 | 0.13% / 5.4% | 0.793 | 0.604 | 0.901 | 3,072 |
|  | A3 | 0.497 (0.013) | 0.9505 | 0.0375 | 0.188 | 0.359 | 0.752 | 0.486 | 0.13% / 5.2% | 0.794 | 0.605 | 0.900 | 3,072 |
|  | RM3 | 0.500 (0.007) | 0.9558 | 0.0546 | 0.230 | 0.279 | 0.788 | 0.412 | 0.25% / 8.6% | 0.919 | 0.759 | 0.938 | 3,072 |
| th-high | A0 | 0.506 (0.008) | 0.9514 | 0.0217 | 0.139 | 0.458 | 0.723 | 0.561 | 0.05% / 3.2% | 0.908 | 0.746 | 0.928 | 1,024 |
|  | A1 | 0.506 (0.008) | 0.9513 | 0.0214 | 0.138 | 0.459 | 0.723 | 0.561 | 0.05% / 3.2% | 0.908 | 0.742 | 0.928 | 1,024 |
|  | A2 | 0.504 (0.009) | 0.9509 | 0.0132 | 0.103 | 0.490 | 0.689 | 0.573 | 0.03% / 3.8% | 0.882 | 0.706 | 0.919 | 3,072 |
|  | A3 | 0.504 (0.009) | 0.9508 | 0.0130 | 0.102 | 0.492 | 0.689 | 0.574 | 0.03% / 3.8% | 0.882 | 0.706 | 0.920 | 3,072 |
|  | RM3 | 0.509 (0.005) | 0.9542 | 0.0216 | 0.139 | 0.462 | 0.727 | 0.565 | 0.04% / 2.7% | 0.964 | 0.841 | 0.954 | 3,072 |
| comb-medium | A0 | 0.498 (0.012) | 0.9523 | 0.0547 | 0.230 | 0.277 | 0.784 | 0.409 | 0.25% / 8.2% | 0.811 | 0.627 | 0.894 | 1,024 |
|  | A1 | 0.499 (0.012) | 0.9524 | 0.0350 | 0.181 | 0.384 | 0.750 | 0.508 | 0.11% / 4.8% | 0.811 | 0.623 | 0.894 | 1,024 |
|  | A2 | 0.500 (0.013) | 0.9525 | 0.0394 | 0.193 | 0.353 | 0.751 | 0.480 | 0.14% / 5.3% | 0.786 | 0.597 | 0.887 | 3,072 |
|  | A3 | 0.500 (0.012) | 0.9527 | 0.0215 | 0.138 | 0.446 | 0.718 | 0.550 | 0.06% / 4.1% | 0.786 | 0.596 | 0.886 | 3,072 |
|  | RM3 | 0.508 (0.006) | 0.9556 | 0.0546 | 0.230 | 0.286 | 0.786 | 0.419 | 0.24% / 8.4% | 0.916 | 0.756 | 0.935 | 3,072 |
| comb-high | A0 | 0.485 (0.031) | 0.9462 | 0.1215 | 0.346 | 0.018 | 0.877 | 0.034 | 8.05% / 17.4% | 0.613 | 0.442 | 0.829 | 1,024 |
|  | A1 | 0.485 (0.032) | 0.9460 | 0.0713 | 0.263 | 0.159 | 0.799 | 0.264 | 0.62% / 9.7% | 0.615 | 0.440 | 0.829 | 1,024 |
|  | A2 | 0.482 (0.033) | 0.9448 | 0.1065 | 0.324 | 0.042 | 0.850 | 0.080 | 3.15% / 14.8% | 0.593 | 0.423 | 0.823 | 3,072 |
|  | A3 | 0.481 (0.033) | 0.9446 | 0.0545 | 0.228 | 0.224 | 0.774 | 0.348 | 0.36% / 7.9% | 0.595 | 0.424 | 0.823 | 3,072 |
|  | RM3 | 0.506 (0.017) | 0.9505 | 0.1214 | 0.346 | 0.024 | 0.872 | 0.047 | 5.79% / 17.0% | 0.782 | 0.594 | 0.881 | 3,072 |

**Finite shots, 4,096 per circuit: Table A** (same layout):

| Condition | Action | AUPRC (SD) | AUROC | Brier | ECE | Prec@τ | Rec@τ | F1@τ | Cross τ (all / fraud) | Spearman | Kendall | Top-47 | Shots/inference |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clean | A0 | 0.509 (0.005) | 0.9572 | 0.0094 | 0.083 | 0.519 | 0.674 | 0.586 | 0.01% / 2.8% | 0.988 | 0.909 | 0.976 | 4,096 |
|  | A1 | 0.509 (0.005) | 0.9572 | 0.0094 | 0.083 | 0.519 | 0.674 | 0.586 | 0.01% / 2.8% | 0.988 | 0.909 | 0.976 | 4,096 |
|  | A2 | 0.510 (0.005) | 0.9571 | 0.0094 | 0.083 | 0.522 | 0.680 | 0.590 | 0.01% / 2.2% | 0.983 | 0.889 | 0.969 | 12,288 |
|  | A3 | 0.510 (0.005) | 0.9571 | 0.0094 | 0.083 | 0.522 | 0.680 | 0.590 | 0.01% / 2.2% | 0.983 | 0.889 | 0.969 | 12,288 |
|  | RM3 | 0.509 (0.002) | 0.9571 | 0.0093 | 0.083 | 0.525 | 0.688 | 0.596 | 0.01% / 1.4% | 0.996 | 0.947 | 0.985 | 12,288 |
| ro-sym-high | A0 | 0.505 (0.006) | 0.9557 | 0.0527 | 0.226 | 0.314 | 0.780 | 0.448 | 0.19% / 7.8% | 0.933 | 0.784 | 0.945 | 4,096 |
|  | A1 | 0.505 (0.006) | 0.9558 | 0.0096 | 0.084 | 0.514 | 0.670 | 0.581 | 0.02% / 3.8% | 0.937 | 0.790 | 0.948 | 4,096 |
|  | A2 | 0.504 (0.009) | 0.9561 | 0.0527 | 0.226 | 0.309 | 0.779 | 0.442 | 0.20% / 7.7% | 0.909 | 0.745 | 0.940 | 12,288 |
|  | A3 | 0.504 (0.009) | 0.9562 | 0.0097 | 0.084 | 0.510 | 0.671 | 0.580 | 0.02% / 4.4% | 0.915 | 0.753 | 0.940 | 12,288 |
|  | RM3 | 0.507 (0.004) | 0.9559 | 0.0527 | 0.226 | 0.323 | 0.781 | 0.457 | 0.18% / 7.9% | 0.975 | 0.869 | 0.974 | 12,288 |
| ar-020 | A0 | 0.511 (0.004) | 0.9574 | 0.0230 | 0.145 | 0.478 | 0.745 | 0.582 | 0.04% / 4.5% | 0.965 | 0.843 | 0.959 | 4,096 |
|  | A1 | 0.508 (0.004) | 0.9559 | 0.0096 | 0.085 | 0.520 | 0.680 | 0.589 | 0.01% / 2.4% | 0.971 | 0.858 | 0.957 | 4,096 |
|  | A2 | 0.512 (0.005) | 0.9578 | 0.0230 | 0.145 | 0.477 | 0.744 | 0.581 | 0.04% / 4.4% | 0.953 | 0.815 | 0.950 | 12,288 |
|  | A3 | 0.509 (0.005) | 0.9562 | 0.0097 | 0.085 | 0.516 | 0.673 | 0.585 | 0.02% / 3.1% | 0.960 | 0.831 | 0.948 | 12,288 |
|  | RM3 | 0.513 (0.003) | 0.9584 | 0.0230 | 0.145 | 0.482 | 0.746 | 0.586 | 0.04% / 4.4% | 0.984 | 0.894 | 0.973 | 12,288 |
| ar-050 | A0 | 0.516 (0.005) | 0.9590 | 0.0522 | 0.225 | 0.352 | 0.771 | 0.483 | 0.14% / 6.9% | 0.897 | 0.725 | 0.923 | 4,096 |
|  | A1 | 0.508 (0.005) | 0.9555 | 0.0096 | 0.084 | 0.515 | 0.673 | 0.583 | 0.02% / 3.5% | 0.939 | 0.792 | 0.951 | 4,096 |
|  | A2 | 0.514 (0.007) | 0.9583 | 0.0522 | 0.225 | 0.348 | 0.771 | 0.479 | 0.15% / 6.9% | 0.873 | 0.693 | 0.916 | 12,288 |
|  | A3 | 0.505 (0.006) | 0.9547 | 0.0097 | 0.084 | 0.516 | 0.681 | 0.587 | 0.02% / 3.4% | 0.917 | 0.756 | 0.935 | 12,288 |
|  | RM3 | 0.517 (0.003) | 0.9591 | 0.0521 | 0.225 | 0.363 | 0.768 | 0.493 | 0.13% / 6.6% | 0.938 | 0.787 | 0.952 | 12,288 |
| dep-high | A0 | 0.503 (0.007) | 0.9538 | 0.0546 | 0.230 | 0.280 | 0.784 | 0.412 | 0.25% / 8.2% | 0.936 | 0.787 | 0.944 | 4,096 |
|  | A1 | 0.503 (0.007) | 0.9537 | 0.0539 | 0.228 | 0.283 | 0.784 | 0.416 | 0.24% / 8.2% | 0.936 | 0.786 | 0.945 | 4,096 |
|  | A2 | 0.504 (0.008) | 0.9542 | 0.0380 | 0.190 | 0.382 | 0.759 | 0.508 | 0.11% / 5.6% | 0.925 | 0.769 | 0.939 | 12,288 |
|  | A3 | 0.504 (0.008) | 0.9540 | 0.0373 | 0.188 | 0.384 | 0.756 | 0.509 | 0.11% / 5.4% | 0.925 | 0.769 | 0.939 | 12,288 |
|  | RM3 | 0.503 (0.004) | 0.9561 | 0.0546 | 0.230 | 0.282 | 0.787 | 0.415 | 0.24% / 8.5% | 0.976 | 0.870 | 0.963 | 12,288 |
| th-high | A0 | 0.508 (0.006) | 0.9556 | 0.0216 | 0.139 | 0.458 | 0.728 | 0.562 | 0.04% / 2.8% | 0.972 | 0.860 | 0.955 | 4,096 |
|  | A1 | 0.508 (0.006) | 0.9556 | 0.0213 | 0.138 | 0.459 | 0.726 | 0.562 | 0.04% / 2.6% | 0.971 | 0.859 | 0.955 | 4,096 |
|  | A2 | 0.507 (0.007) | 0.9562 | 0.0130 | 0.103 | 0.505 | 0.698 | 0.586 | 0.02% / 0.9% | 0.963 | 0.838 | 0.956 | 12,288 |
|  | A3 | 0.507 (0.007) | 0.9561 | 0.0128 | 0.102 | 0.506 | 0.696 | 0.586 | 0.02% / 1.1% | 0.963 | 0.838 | 0.956 | 12,288 |
|  | RM3 | 0.509 (0.004) | 0.9559 | 0.0215 | 0.139 | 0.464 | 0.732 | 0.568 | 0.04% / 3.0% | 0.989 | 0.912 | 0.981 | 12,288 |
| comb-medium | A0 | 0.506 (0.006) | 0.9558 | 0.0546 | 0.230 | 0.289 | 0.784 | 0.422 | 0.23% / 8.2% | 0.934 | 0.785 | 0.952 | 4,096 |
|  | A1 | 0.506 (0.007) | 0.9557 | 0.0345 | 0.180 | 0.408 | 0.753 | 0.529 | 0.09% / 5.1% | 0.934 | 0.783 | 0.951 | 4,096 |
|  | A2 | 0.507 (0.006) | 0.9550 | 0.0392 | 0.193 | 0.390 | 0.764 | 0.517 | 0.11% / 6.2% | 0.922 | 0.764 | 0.947 | 12,288 |
|  | A3 | 0.507 (0.006) | 0.9549 | 0.0209 | 0.137 | 0.460 | 0.722 | 0.562 | 0.04% / 2.2% | 0.921 | 0.763 | 0.948 | 12,288 |
|  | RM3 | 0.506 (0.003) | 0.9565 | 0.0545 | 0.230 | 0.292 | 0.787 | 0.425 | 0.23% / 8.5% | 0.975 | 0.869 | 0.968 | 12,288 |
| comb-high | A0 | 0.499 (0.010) | 0.9521 | 0.1214 | 0.346 | 0.025 | 0.880 | 0.049 | 5.54% / 17.8% | 0.819 | 0.633 | 0.903 | 4,096 |
|  | A1 | 0.499 (0.010) | 0.9519 | 0.0721 | 0.265 | 0.178 | 0.801 | 0.292 | 0.53% / 9.9% | 0.818 | 0.631 | 0.904 | 4,096 |
|  | A2 | 0.500 (0.009) | 0.9532 | 0.1063 | 0.323 | 0.059 | 0.850 | 0.111 | 2.15% / 14.8% | 0.804 | 0.615 | 0.899 | 12,288 |
|  | A3 | 0.499 (0.010) | 0.9530 | 0.0550 | 0.230 | 0.261 | 0.783 | 0.391 | 0.28% / 8.1% | 0.803 | 0.615 | 0.899 | 12,288 |
|  | RM3 | 0.502 (0.009) | 0.9552 | 0.1213 | 0.346 | 0.028 | 0.885 | 0.054 | 5.03% / 18.3% | 0.919 | 0.760 | 0.934 | 12,288 |

**Resource-matched comparisons: Table C**. Each action is compared with its shot-matched comparator. Brackets give the two-stage 95% interval over transactions and replicate. **B** marks an RRB benefit under the registered G2 rule; H marks harm.

*1,024 shots per circuit:*

| Condition | Action vs comparator | Label | ΔAUPRC [95%] | ΔBrier [95%] | ΔF1@τ [95%] | RRB (AUPRC / Brier / F1) |
|---|---|---|---|---|---|---|
| clean | A1 − A0 | neg. control | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | +0.000 [+0.000, +0.000] | ·/·/· |
|  | A2 − RM3 | neg. control | -0.007 [-0.037, +0.024] | +0.0001 [+0.0000, +0.0001] | -0.012 [-0.078, +0.043] | ·/·/· |
|  | A3 − RM3 | neg. control | -0.007 [-0.037, +0.024] | +0.0001 [+0.0000, +0.0001] | -0.012 [-0.078, +0.043] | ·/·/· |
| ro-sym-high | A1 − A0 | applicable | +0.000 [-0.009, +0.008] | -0.0420 [-0.0443, -0.0390] | +0.150 [+0.042, +0.234] | ·/**B**/**B** |
|  | A2 − RM3 | neg. control | -0.007 [-0.054, +0.039] | +0.0002 [+0.0001, +0.0003] | -0.033 [-0.081, +0.015] | ·/·/· |
|  | A3 − RM3 | partial | -0.007 [-0.054, +0.038] | -0.0417 [-0.0441, -0.0387] | +0.130 [+0.037, +0.203] | ·/**B**/**B** |
| ar-020 | A1 − A0 | applicable | -0.002 [-0.013, +0.008] | -0.0133 [-0.0148, -0.0115] | +0.007 [-0.056, +0.065] | ·/**B**/· |
|  | A2 − RM3 | neg. control | -0.003 [-0.034, +0.026] | +0.0001 [+0.0001, +0.0002] | -0.015 [-0.066, +0.034] | ·/·/· |
|  | A3 − RM3 | partial | -0.008 [-0.038, +0.024] | -0.0132 [-0.0147, -0.0113] | -0.006 [-0.066, +0.052] | ·/**B**/· |
| ar-050 | A1 − A0 | applicable | -0.008 [-0.033, +0.012] | -0.0414 [-0.0432, -0.0385] | +0.112 [+0.026, +0.193] | ·/**B**/**B** |
|  | A2 − RM3 | neg. control | -0.012 [-0.050, +0.026] | +0.0002 [+0.0001, +0.0003] | -0.031 [-0.081, +0.016] | ·/·/· |
|  | A3 − RM3 | partial | -0.020 [-0.060, +0.020] | -0.0411 [-0.0430, -0.0382] | +0.079 [-0.015, +0.162] | ·/**B**/· |
| dep-high | A1 − A0 | neg. control | +0.001 [-0.003, +0.006] | -0.0007 [-0.0012, -0.0002] | +0.002 [+0.000, +0.011] | ·/·/· |
|  | A2 − RM3 | applicable | -0.003 [-0.038, +0.042] | -0.0164 [-0.0165, -0.0164] | +0.073 [+0.018, +0.128] | ·/**B**/**B** |
|  | A3 − RM3 | partial | -0.003 [-0.037, +0.042] | -0.0171 [-0.0176, -0.0167] | +0.074 [+0.017, +0.130] | ·/**B**/**B** |
| th-high | A1 − A0 | neg. control | +0.000 [-0.002, +0.005] | -0.0002 [-0.0007, +0.0000] | +0.000 [+0.000, +0.005] | ·/·/· |
|  | A2 − RM3 | applicable | -0.005 [-0.033, +0.022] | -0.0084 [-0.0085, -0.0084] | +0.008 [-0.053, +0.058] | ·/**B**/· |
|  | A3 − RM3 | partial | -0.005 [-0.033, +0.022] | -0.0086 [-0.0090, -0.0084] | +0.009 [-0.053, +0.059] | ·/**B**/· |
| comb-medium | A1 − A0 | partial | +0.001 [-0.003, +0.009] | -0.0197 [-0.0220, -0.0176] | +0.099 [+0.046, +0.153] | ·/**B**/**B** |
|  | A2 − RM3 | partial | -0.007 [-0.046, +0.029] | -0.0152 [-0.0153, -0.0151] | +0.061 [+0.010, +0.109] | ·/**B**/**B** |
|  | A3 − RM3 | applicable | -0.007 [-0.046, +0.030] | -0.0331 [-0.0351, -0.0313] | +0.131 [+0.063, +0.203] | ·/**B**/**B** |
| comb-high | A1 − A0 | partial | -0.000 [-0.011, +0.009] | -0.0502 [-0.0558, -0.0440] | +0.230 [+0.181, +0.292] | ·/**B**/**B** |
|  | A2 − RM3 | partial | -0.024 [-0.086, +0.033] | -0.0149 [-0.0151, -0.0148] | +0.033 [+0.025, +0.040] | ·/**B**/· |
|  | A3 − RM3 | applicable | -0.025 [-0.085, +0.030] | -0.0669 [-0.0724, -0.0608] | +0.301 [+0.234, +0.377] | ·/**B**/**B** |

*4,096 shots per circuit:*

| Condition | Action vs comparator | Label | ΔAUPRC [95%] | ΔBrier [95%] | ΔF1@τ [95%] | RRB (AUPRC / Brier / F1) |
|---|---|---|---|---|---|---|
| clean | A1 − A0 | neg. control | +0.000 [+0.000, +0.000] | +0.0000 [+0.0000, +0.0000] | +0.000 [+0.000, +0.000] | ·/·/· |
|  | A2 − RM3 | neg. control | +0.001 [-0.017, +0.017] | +0.0000 [+0.0000, +0.0000] | -0.006 [-0.053, +0.037] | ·/·/· |
|  | A3 − RM3 | neg. control | +0.001 [-0.017, +0.017] | +0.0000 [+0.0000, +0.0000] | -0.006 [-0.053, +0.037] | ·/·/· |
| ro-sym-high | A1 − A0 | applicable | -0.000 [-0.006, +0.005] | -0.0431 [-0.0440, -0.0416] | +0.134 [+0.046, +0.212] | ·/**B**/**B** |
|  | A2 − RM3 | neg. control | -0.003 [-0.027, +0.021] | +0.0001 [+0.0000, +0.0001] | -0.015 [-0.057, +0.028] | ·/·/· |
|  | A3 − RM3 | partial | -0.003 [-0.026, +0.022] | -0.0430 [-0.0439, -0.0415] | +0.123 [+0.040, +0.199] | ·/**B**/**B** |
| ar-020 | A1 − A0 | applicable | -0.003 [-0.012, +0.004] | -0.0134 [-0.0139, -0.0127] | +0.007 [-0.063, +0.067] | ·/**B**/· |
|  | A2 − RM3 | neg. control | -0.001 [-0.017, +0.019] | +0.0000 [+0.0000, +0.0001] | -0.005 [-0.050, +0.029] | ·/·/· |
|  | A3 − RM3 | partial | -0.004 [-0.021, +0.015] | -0.0133 [-0.0139, -0.0126] | -0.001 [-0.076, +0.063] | ·/**B**/· |
| ar-050 | A1 − A0 | applicable | -0.008 [-0.025, +0.009] | -0.0425 [-0.0434, -0.0410] | +0.100 [+0.025, +0.172] | ·/**B**/**B** |
|  | A2 − RM3 | neg. control | -0.003 [-0.026, +0.018] | +0.0001 [+0.0000, +0.0001] | -0.014 [-0.047, +0.020] | ·/·/· |
|  | A3 − RM3 | partial | -0.012 [-0.034, +0.012] | -0.0425 [-0.0434, -0.0409] | +0.094 [+0.017, +0.163] | ·/**B**/**B** |
| dep-high | A1 − A0 | neg. control | -0.000 [-0.004, +0.002] | -0.0007 [-0.0010, -0.0004] | +0.004 [+0.000, +0.017] | ·/·/· |
|  | A2 − RM3 | applicable | +0.001 [-0.019, +0.023] | -0.0166 [-0.0166, -0.0166] | +0.093 [+0.047, +0.145] | ·/**B**/**B** |
|  | A3 − RM3 | partial | +0.001 [-0.019, +0.022] | -0.0173 [-0.0176, -0.0169] | +0.094 [+0.046, +0.144] | ·/**B**/**B** |
| th-high | A1 − A0 | neg. control | +0.000 [-0.001, +0.002] | -0.0002 [-0.0004, -0.0001] | -0.000 [-0.022, +0.010] | ·/·/· |
|  | A2 − RM3 | applicable | -0.002 [-0.016, +0.013] | -0.0085 [-0.0086, -0.0085] | +0.018 [-0.030, +0.067] | ·/**B**/· |
|  | A3 − RM3 | partial | -0.002 [-0.016, +0.013] | -0.0087 [-0.0088, -0.0086] | +0.018 [-0.036, +0.068] | ·/**B**/· |
| comb-medium | A1 − A0 | partial | -0.000 [-0.004, +0.003] | -0.0201 [-0.0210, -0.0186] | +0.107 [+0.054, +0.153] | ·/**B**/**B** |
|  | A2 − RM3 | partial | +0.001 [-0.017, +0.020] | -0.0154 [-0.0154, -0.0153] | +0.091 [+0.040, +0.140] | ·/**B**/**B** |
|  | A3 − RM3 | applicable | +0.001 [-0.018, +0.020] | -0.0336 [-0.0344, -0.0324] | +0.137 [+0.072, +0.202] | ·/**B**/**B** |
| comb-high | A1 − A0 | partial | -0.000 [-0.007, +0.006] | -0.0493 [-0.0518, -0.0462] | +0.243 [+0.200, +0.291] | ·/**B**/**B** |
|  | A2 − RM3 | partial | -0.002 [-0.034, +0.031] | -0.0151 [-0.0152, -0.0150] | +0.057 [+0.045, +0.068] | ·/**B**/**B** |
|  | A3 − RM3 | applicable | -0.003 [-0.035, +0.031] | -0.0663 [-0.0687, -0.0632] | +0.337 [+0.270, +0.408] | ·/**B**/**B** |

**Table D (descriptive best action**: the cheapest action within the minimum effect of the best mean; `p4_best_action.csv`). The choice is identical in both arms:

| Condition | AUPRC | Brier | F1@τ |
|---|---|---|---|
| clean | A0 | A0 | A0 |
| ro-sym-high | A0 | A1 | A1 |
| ar-020 | A0 | A1 | A0 |
| ar-050 | A0 | A1 | A1 |
| dep-high | A0 | A2 | A2 |
| th-high | A0 | A2 | A0 |
| comb-medium | A0 | A3 | A1 |
| comb-high | A0 | A3 | A3 |

**Runtime** (dev run `20261007T192731Z-f3f75543`, 15-core Apple M5 Pro; raw `runtime.json`):

| Stage | Wall time | CPU time | Detail |
|---|---|---|---|
| Exact stage (15 Aer runs, parallel) | 119 s | 1,065 s | λ = 1 / 3 / 5 ≈ 32 / 83 / 115 s per run under contention |
| Exact diagnostics | 86 s | | |
| Direct-shot validation | 1.8 s | | |
| Finite-shot study | 157 s | sampling and mitigation 96 s; metrics 164 s; two-stage bootstrap 1,398 s | |
| Whole run | 365 s | | peak resident memory of the main process 456 MiB |

**G2 (registered rule): CONDITIONAL PASS.**
- **Why not FAIL:** 54 qualifying cell-endpoints have a resource-robust benefit (RRB): 32 on Brier and 22 on F1@τ. Table D also varies across contexts.
- **Why not PASS:** no cell has an AUPRC RRB against its resource-matched comparator, in either arm.
- **Negative-control cells:** none has an RRB, and the clean-context flag did not fire.

**Hypotheses:**

| Hypothesis | Outcome | Detail |
|---|---|---|
| H4.1 | **supported** | 6 of 6 readout cells have a Brier RRB. |
| H4.2 | **supported** | Exact: ΔAUPRC = ΔAUROC = 0. Finite-shot: the interval contains 0 in both arms. |
| H4.3 | **not supported** | No AUPRC RRB, as the pre-registered theory predicted. |
| H4.4 | **supported** | The best action depends on the noise family; RRB status varies across family and severity. |
| H4.5 | **not supported under its registered test** | Every A2/A3 qualifying cell beats RM3 on Brier, because RM3 cannot remove bias. |

H4.5 descriptive note: A3 costs 3× A1 for the same calibration under pure readout, and A2 is pure cost under pure readout (negative control). The registered comparator did not capture this.

**Findings:**
1. **Mitigation does not improve fraud discrimination.**
   - Its ΔAUPRC against the shot-matched baseline is never interval-supported; at 1,024 shots, the ZNE-based actions trend negative (−0.024 [−0.086, +0.033] at comb-high).
   - Extra shots do help ranking: under comb-high at 1,024, RM3 raises AUPRC from 0.485 to 0.506 and Spearman from 0.61 to 0.78. ZNE does not.
2. **Mitigation repairs the effects Phase 3B identified: calibration and the threshold.**
   - Readout mitigation brings Brier back near clean under readout noise (0.053 → 0.011). ZNE does the same under gate noise (dep-high 0.055 → 0.038), and A3 under combined noise (comb-high 0.122 → 0.054).
   - F1 at the frozen τ recovers by up to +0.30 (comb-high: 0.03 → 0.35).
   - These gains are *not* obtainable by spending more shots: RM3 and RM9 leave Brier unchanged.
3. **The best action is context-dependent:**
   - readout noise → A1;
   - gate noise → A2;
   - combined noise → A3 (Brier) or A1/A3 (F1);
   - clean → A0.

   The cost-aware choice is a genuine selective decision. It depends on the noise family, which the controller cannot observe directly (A12).
4. **The shot budget changes magnitudes slightly but never the descriptive choice** (Table D is identical across arms; Figure D points sit on the diagonal for Brier).
5. **Calibration overhead is negligible** when amortized over the batch: 2 circuits per 28,372 inferences.

### 3.11 Phase 5A: independent VQC model pool (results)

**Registration:** [`PREREG_P5A.md`](PREREG_P5A.md), committed and pushed (`d542770`) before any pool model was trained. It was executed as registered in a single wave, with no cap and no selection.

**Scope:**
- **Data:** `vqc_train` fits everything; clean `vqc_val` qualifies (access phase `phase5a`).
- **Not done:** no noise, mitigation, counterfactuals or controller.
- **Anchor and controls:** P3A-R is replayed as the anchor and left untouched. The two diagnostic controls are excluded from the pool.

**Outcome:**
- **64 of 64 candidates qualified** (Q1–Q9); none was excluded.
- Every model retrains bitwise-identically, and every Aer replay matches the exact engine.
- **Duplicates:** no θ or prediction duplicates. 9 same-structure seed pairs are near-duplicates (ρ ≥ 0.999; one at 0.99997); they are reported, not excluded. Merging every pair at ρ ≥ 0.999 leaves **57 effectively distinct models**.
- **Manifest:** `artifacts/model_pool/p5a_pool_manifest.json`.

**Per structure** (4 seeds each; clean `vqc_val`; F1@τ is optimistic because τ_m is tuned on `vqc_val`):

| Structure | Params | CX / noisy depth | AUPRC mean [min, max] | AUROC mean | Brier mean | ECE mean | F1@τ mean (optimistic) | Budget-bound seeds |
|---|---|---|---|---|---|---|---|---|
| top4-e3-ra1-parity | 8 | 15 / 17 | 0.325 [0.315, 0.335] | 0.951 | 0.0082 | 0.078 | 0.540 | 0/4 |
| top4-e3-ra2-parity | 12 | 18 / 21 | 0.460 [0.389, 0.503] | 0.956 | 0.0088 | 0.080 | 0.588 | 3/4 |
| top4-e3-esu1-parity | 16 | 15 / 17 | 0.347 [0.294, 0.441] | 0.953 | 0.0090 | 0.073 | 0.520 | 2/4 |
| top4-e3-esu2-parity | 24 | 18 / 21 | 0.408 [0.245, 0.538] | 0.946 | 0.0108 | 0.075 | 0.510 | 4/4 |
| next4-e3-ra1-parity | 8 | 15 / 17 | 0.153 [0.069, 0.185] | 0.925 | 0.0176 | 0.113 | 0.298 | 1/4 |
| next4-e3-ra2-parity | 12 | 18 / 21 | 0.143 [0.136, 0.156] | 0.945 | 0.0212 | 0.120 | 0.250 | 3/4 |
| next4-e3-esu1-parity | 16 | 15 / 17 | 0.077 [0.047, 0.126] | 0.944 | 0.0270 | 0.136 | 0.165 | 1/4 |
| next4-e3-esu2-parity | 24 | 18 / 21 | 0.234 [0.192, 0.274] | 0.950 | 0.0163 | 0.102 | 0.337 | 4/4 |
| pca4-e3-ra1-parity | 8 | 15 / 17 | 0.101 [0.089, 0.109] | 0.934 | 0.0254 | 0.135 | 0.245 | 0/4 |
| pca4-e3-ra2-parity | 12 | 18 / 21 | 0.080 [0.071, 0.085] | 0.936 | 0.0217 | 0.117 | 0.188 | 1/4 |
| pca4-e3-esu1-parity | 16 | 15 / 17 | 0.156 [0.078, 0.294] | 0.921 | 0.0298 | 0.138 | 0.286 | 2/4 |
| pca4-e3-esu2-parity | 24 | 18 / 21 | 0.245 [0.182, 0.313] | 0.935 | 0.0190 | 0.102 | 0.370 | 4/4 |
| top4-e2-ra2-parity | 12 | 18 / 21 | 0.383 [0.352, 0.419] | 0.961 | 0.0149 | 0.082 | 0.488 | 4/4 |
| top4-s5-ra2-parity | 12 | 18 / 21 | 0.390 [0.379, 0.396] | 0.962 | 0.0117 | 0.074 | 0.482 | 4/4 |
| top4-e3-ra2-mean_z | 12 | 18 / 21 | 0.237 [0.231, 0.243] | 0.943 | 0.0345 | 0.173 | 0.342 | 0/4 |
| top4-e3-esu1-mean_z | 16 | 15 / 17 | 0.234 [0.233, 0.235] | 0.942 | 0.0282 | 0.152 | 0.371 | 0/4 |

**Pool distribution (64 models):**

| Metric | Median | Range | Mean (SD) |
|---|---|---|---|
| AUPRC | 0.235 | 0.047–0.538 | 0.248 (0.131) |
| AUROC | 0.946 | 0.911–0.965 | |
| Brier | | 0.007–0.036 | |
| ECE | | 0.065–0.176 | |
| F1@τ | 0.370 | 0.125–0.603 | |

33 of 64 hit the 1,000-evaluation budget (O25).

**Anchor and diagnostic controls** (not in the pool):

| Model | Role | AUPRC [95% CI] | AUROC | Brier | ECE | F1@τ |
|---|---|---|---|---|---|---|
| ctrl-shallow | control | 0.524 [0.382, 0.686] | 0.958 | 0.0043 | 0.054 | 0.592 |
| p3a_r | anchor | 0.507 [0.363, 0.661] | 0.957 | 0.0093 | 0.083 | 0.606 |
| ctrl-p3a-original | control | 0.104 [0.054, 0.166] | 0.766 | 0.2410 | 0.474 | 0.295 |

The shallow control (RealAmplitudes reps 0) is as strong as the best pool models. It stays a control, as registered.

**Prediction diversity** (Table D; pairwise over all 28,372 `vqc_val` rows):

| Pair type | Pairs | Spearman median [5%, 95%] | Kendall median | Mean \|Δscore\| median | Flag disagreement median | Pairs ρ ≥ 0.999 |
|---|---|---|---|---|---|---|
| all_pool_pairs | 2016 | 0.249 [-0.013, 0.903] | 0.168 | 0.068 | 0.29% | 9 |
| same_structure | 96 | 0.915 [0.682, 1.000] | 0.752 | 0.017 | 0.11% | 9 |
| one_axis | 464 | 0.655 [0.019, 0.916] | 0.474 | 0.047 | 0.26% | 0 |
| two_plus_axes | 1456 | 0.211 [-0.018, 0.841] | 0.142 | 0.073 | 0.31% | 0 |
| with_anchor | 64 | 0.479 [0.045, 0.852] | 0.335 | 0.055 | 0.21% | 0 |
| between_structure | 1920 | 0.236 [-0.015, 0.866] | 0.160 | 0.070 | 0.30% | 0 |

**Reading the diversity numbers:**
- Spearman over all rows is dominated by how models order the **legitimate bulk**.
- Decision-level disagreement at each model's own τ is small: a median of 0.3% of rows, about 85 transactions.
- Inputs dominate prediction structure: the heatmap clusters by feature set first (`p5a_b_correlation.png`).

**Power** (O15; one-way random effects; σ_w = Phase 4 median replicate SD of the resource-matched Δ: AUPRC 0.0061, Brier 0.0006, F1@τ 0.0177):

| Models | R | MDE σ_b/σ_w | MDE σ_b: ΔAUPRC | ΔBrier | ΔF1@τ | Meta-test models | Controller-vs-rule MDE (SD units) |
|---|---|---|---|---|---|---|---|
| 20 | 5 | 0.534 | 0.0033 | 0.00032 | 0.0095 | 5 | 1.25 |
| 20 | 10 | 0.360 | 0.0022 | 0.00021 | 0.0064 | 5 | 1.25 |
| 20 | 20 | 0.250 | 0.0015 | 0.00015 | 0.0044 | 5 | 1.25 |
| 40 | 5 | 0.415 | 0.0025 | 0.00024 | 0.0073 | 10 | 0.89 |
| 40 | 10 | 0.281 | 0.0017 | 0.00017 | 0.0050 | 10 | 0.89 |
| 40 | 20 | 0.195 | 0.0012 | 0.00012 | 0.0035 | 10 | 0.89 |
| 64 (pool) | 5 | 0.355 | 0.0022 | 0.00021 | 0.0063 | 16 | 0.70 |
| 64 (pool) | 10 | 0.242 | 0.0015 | 0.00014 | 0.0043 | 16 | 0.70 |
| 64 (pool) | 20 | 0.168 | 0.0010 | 0.00010 | 0.0030 | 16 | 0.70 |

**Runtime** (dev run `20261007T205828Z-0919913a`; compute time, because the host slept during the run, inflating wall-clock to 29.5 min):

| Item | Value |
|---|---|
| Training | 8.0 s per model mean (3 restarts; max 13.0 s) |
| Pool training wall-clock | 74 s on 15 cores, including the bitwise retraining check |
| Feature-map states | 18.5 s |
| Qualification bootstrap | 87 s |
| Whole run | 224 s compute; peak memory 712 MiB |
| Aer density matrix, comb-high (ms per row, λ = 1 / 3 / 5) | 0.36–0.51 / 0.98–1.61 / 1.57–2.61 |

**Projected Phase 5B (Table E;** the Phase 4 design for all 64 models, using Phase 4's measured finite-shot and bootstrap costs):

| Scenario | CPU hours | Wall-clock on 15 cores |
|---|---|---|
| Full Phase 4 design | 39.5 | **2.6 h** |
| Without the two-stage bootstrap | 14.6 | 1.0 h |
| With 10 replicates | 24.8 | 1.7 h |

**G3A (registered rule): PASS.** All six criteria hold, and no fail condition is triggered:
- **(a) size:** 64 ≥ 40;
- **(b) coverage:** every axis level has at least 4 models;
- **(c) prediction diversity:** median between-structure Spearman 0.236 ≤ 0.95, and 0.45% of pairs at ρ ≥ 0.999 (< 5%);
- **(d) no dominance:** family 56%, seed 25%, structure 6.25%;
- **(e) clean signal:** median AUPRC 0.235 ≥ 10× prevalence;
- **(f) feasibility:** 2.6 h ≤ 48 h.

**Findings:**
1. **Training is robust.** Every registered design trains into a valid fraud classifier, including `mean_z` readouts, ANOVA ranks 5–8 and unstandardized PCA-4.
2. **Inputs dominate clean performance.** The top4 structures reach 0.23–0.54 AUPRC, against 0.05–0.31 for next4 and pca4. Depth and family matter less.
3. **The pool is weaker than P3A-R** (median AUPRC 0.235 against 0.507). The P3A-R-like structure top4-e3-ra2-parity averages 0.460, so P3A-R sits at the favourable end of its own structure.
4. **Structural diversity is genuine; decision-level diversity is modest.** Within-structure seed pairs are highly correlated (median ρ 0.915), while between-structure pairs are not (0.236).
5. **The pool supports Phase 5B on cost and power.** Its size is adequate for detecting between-model heterogeneity in mitigation benefit: minimum detectable σ_b is about 0.17 σ_w at 64 models × 20 replicates. It is only moderately powered for a controller-vs-rule comparison at the model level (0.70 SD with 16 held-out models).

### 3.12 Phase 5B: cross-model counterfactual dataset (results)

**Registration:** [`PREREG_P5B.md`](PREREG_P5B.md), committed and pushed (`0572c4c`) **with the generation and analysis code** before any outcome existed.

**Generation:** one *reported* run on the clean registered tree (`20261007T223317Z-aa8d41b8`). Everything was executed as registered.

**Design:**
- 64 frozen pool models, split by structure 8/4/4.
- Each model is evaluated on its own full controller partition (A04):

  | Partition | Rows | Frauds |
  |---|---|---|
  | `ctrl_train` | 42,559 | 71 |
  | `ctrl_val` | 28,372 | 47 |
  | `ctrl_test` | 56,746 | 95 |

- Per model: 8 conditions × 2 budgets × 20 replicates × (A0–A4 + RM9).
- **122,880 outcome rows:**

  | Split | Rows | Storage |
  |---|---|---|
  | train | 61,440 | `results/processed/phase5b` |
  | val | 30,720 | `results/processed/phase5b` |
  | test | 30,720 | **sealed** in `results/lockbox/phase5b`; only its count and content hash `c9ecc091…` are committed |

**Validation:** every per-model check passed:
- Aer agrees with the exact engine to ≤ 2.1e-15;
- folded clean circuits match unfolded ones to ≤ 5.3e-15;
- noise exposure decreases with λ;
- exact A1 recovers clean under symmetric readout (≤ 7.3e-16).

**Probes:**
- **Readout probe:** recovers each readout profile's mean error (≈ 0.02 for ar-020 and comb-medium; ≈ 0.05 for ro-sym-high, ar-050 and comb-high).
- **Gate probe:** contraction is 1.0 under readout-only noise and 0.3–0.9 under gate noise.
- **Category accuracy:** with the a priori thresholds, each condition's modal probe category is correct for **every** context; 99.6% of replicates are categorized correctly.
- **Cost:** 66 circuits and 66S shots per batch, i.e. 2.4 shots per inference at S = 1,024 on `ctrl_val`, under 0.25% of A0.

**Action outcomes** (train, 1,024 shots; context means over 32 models; Table C):

| Condition | Brier A0 | A1 | A2 | A3 | A4 | F1@τ A0 | A1 | A2 | A3 | A4 | AUPRC A0 | A4 |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| clean | 0.0184 | 0.0184 | 0.0184 | 0.0184 | 0.0183 | 0.367 | 0.367 | 0.366 | 0.366 | 0.368 | 0.308 | 0.312 |
| ro-sym-high | 0.0576 | 0.0192 | 0.0577 | 0.0194 | 0.0575 | 0.258 | 0.360 | 0.256 | 0.356 | 0.262 | 0.299 | 0.309 |
| ar-020 | 0.0316 | 0.0186 | 0.0316 | 0.0187 | 0.0315 | 0.330 | 0.363 | 0.331 | 0.361 | 0.326 | 0.307 | 0.312 |
| ar-050 | 0.0587 | 0.0191 | 0.0588 | 0.0193 | 0.0586 | 0.266 | 0.361 | 0.263 | 0.357 | 0.269 | 0.302 | 0.311 |
| dep-high | 0.0580 | 0.0573 | 0.0422 | 0.0416 | 0.0579 | 0.244 | 0.244 | 0.289 | 0.290 | 0.248 | 0.296 | 0.305 |
| th-high | 0.0294 | 0.0292 | 0.0218 | 0.0216 | 0.0293 | 0.325 | 0.325 | 0.351 | 0.352 | 0.320 | 0.304 | 0.310 |
| comb-medium | 0.0586 | 0.0413 | 0.0446 | 0.0288 | 0.0585 | 0.249 | 0.293 | 0.289 | 0.329 | 0.254 | 0.298 | 0.307 |
| comb-high | 0.1169 | 0.0727 | 0.1020 | 0.0565 | 0.1168 | 0.128 | 0.202 | 0.152 | 0.243 | 0.130 | 0.275 | 0.296 |

**Preferred action** (cost-aware Oracle on Brier; train and val identical in pattern):

| Context | Preferred action (every model, both budgets) |
|---|---|
| clean | A0 |
| ro-sym-high, ar-020, ar-050 | A1 (exception below) |
| dep-high, th-high | A2 |
| comb-medium, comb-high | A3 |

- **Exception:** all 4 seeds of **top4-e3-esu1-mean_z** prefer **A0** under asymmetric readout. Readout mitigation improves a mean-Z model's Brier by only 2–8% there, against 20–87% for parity models.
- **A4 (extra shots) is never preferred:** it changes Brier by ≈ 0.1% (median), because Brier is dominated by bias.
- **Shot budget never changes the preferred action** (0% of model–condition pairs).

**Shares** (train / val):

| Action | Train | Val |
|---|---|---|
| A0 | 15.6% | 12.5% |
| A1 | 34.4% | 37.5% |
| A2 | 25.0% | 25.0% |
| A3 | 25.0% | 25.0% |
| A4 | 0% | 0% |

Split-half stability of the preferred action is 1.000.

**Heterogeneity across models (train; Table H):**

| Action vs A0 | Testable cells | Heterogeneous (Holm p < 0.05, ICC ≥ 0.10) | Median ICC | Median σ_between | Median σ_within |
|---|---|---|---|---|---|
| A1 | 14 | 14 | 0.976 | 0.00502 | 0.00073 |
| A2 | 16 | 16 | 0.814 | 0.00024 | 0.00001 |
| A3 | 16 | 16 | 0.981 | 0.00526 | 0.00068 |
| A4 | 16 | 16 | 0.369 | 0.00001 | 0.00001 |

| Action | η² noise context | η² model | η² model × context |
|---|---|---|---|
| A1 | 0.825 | 0.091 | 0.084 |
| A2 | 0.993 | 0.001 | 0.006 |
| A3 | 0.838 | 0.087 | 0.075 |
| A4 | 0.817 | 0.114 | 0.069 |

**Reading the heterogeneity results:**
- The *size* of the mitigation benefit is strongly model-specific: σ_between ≈ 7× σ_within for A1 and A3.
- It almost never changes *which* action is best, because the noise context explains 82–99% of the variance.
- A4's statistically "heterogeneous" cells are negligible in absolute terms (σ ≈ 1e-5 Brier).

**Observable predictability (Q6):**
- Probe features track the benefit they target: Spearman with ΔBrier is −0.90 for readout error vs A1, and +0.85 for gate contraction vs A2.
- **The rule:** categories {none, readout, gate, both} × budget, with the majority action fitted on train, gives none → A0, readout → A1, gate → A2, both → A3.
- **Failure rates:**

  | Policy | Train | Val |
  |---|---|---|
  | Category rule | 3.5% | **0.33%** |
  | Best universal action | 65.6% | 62.5% |

  The rule's gain over the best universal action on val is 0.62.
- **Residual:** structure association I(p\*; structure | category, budget) = 0.078 nats, permutation p = 0.001. It comes entirely from the mean-Z structure above.
- Val contains no mean-Z structure (a registered imbalance), which is why val failure is lower than train.
- The sealed test split *does* contain one (top4-e3-ra2-mean_z), so a probe-only rule may fail more there. This is **not** examined.

**G3B (registered rule): FAIL — `fixed_rule_sufficient`.** The val category-rule failure is 0.0033, below the 0.05 fail threshold. Every other criterion pointed toward a decision problem:

| Criterion | Value |
|---|---|
| Dominance | max share 0.34 (no dominance) |
| Improvable contexts | 84% |
| Split-half agreement | 1.0 |
| Useful actions | 4 |
| Universal failure (val) | 0.625 |
| Rule gain (val) | 0.62 |
| Model heterogeneity | 100% of cells |
| Structure association | p = 0.001 |

The registered rule makes "fixed rule sufficient" a FAIL condition. **Per the PI's instruction the study stops here: no Q-TRACE training.**

**Secondary endpoint (descriptive; not part of G3B).** The F1@τ-preferred action varies far more across models within a condition. For example, in train comb-high it is A0 for 23 contexts, A1 for 20 and A3 for 21. F1@τ uses the optimistic `vqc_val`-tuned thresholds and is noisier (replicate SD ≈ 0.018), so this is a hypothesis for any reframing, not evidence.

**Runtime:**

| Item | Value |
|---|---|
| Generation | 6,445 s wall (1.8 h) on 15 cores, under `caffeinate` |
| Compute | 25.6 CPU-h; per-model jobs 539–2,994 s (by panel size) |
| Peak memory (main process) | 639 MiB |
| Analysis | 21 s |

### 3.13 Phase 5C: continuous mixed-noise study (results)

**Registration:** [`PREREG_P5C.md`](PREREG_P5C.md), pushed with code (`39b584a`) before any outcome. One reported run (`20261008T141214Z-31395654`), executed as registered; all per-model checks passed.

**Design:**
- 64 frozen models × 68 continuous noise points × 3 budgets (256 / 1,024 / 4,096) × 20 replicates × A0–A4 = **1,305,600 rows**.
- Noise points: split-plot LHS on the anchor-severity scale; 17 gate plots × 4 readout points.
- Test rows (326,400) are sealed (`91b0a5b9…`).

**Preferred action** (cost-aware Oracle, ε = 0.10):

| Action | Train | Val |
|---|---|---|
| A0 none | 1.1% | 0.7% |
| A1 readout | 4.8% | 5.2% |
| A2 ZNE | 27.3% | 22.8% |
| A3 combined | **66.8%** | **71.3%** |
| A4 extra shots | 0% | 0% |

By region (val; `p5c_region_summary.csv`):
- **mixed:** A3 99%;
- **gate-dominated:** A2 68–73%, A3 the rest;
- **readout-dominated:** A1 60%, A3 40%;
- **near-clean:** all four of A0–A3 occur.

**Figure B** (`p5c_b_preferred_map.png`) shows the boundary: under gate noise, A2 at low readout severity (s_ro ≲ 0.6, mean readout error ≲ 0.003) and A3 above it; A1 only on the gate-free plot.

**Stability and budgets:**
- Split-half p\* agreement 0.978 (train) and 0.980 (val); replicate-bootstrap label instability 0.9%.
- The shot budget changes p\* in only 2.7–2.9% of (model, point) pairs; A4 is never preferred.

**Policies** (fitted on train, evaluated per replicate; val, all budgets; 95% two-stage cluster CIs; `p5c_policy_eval.csv`):

| Policy | Failure | Material failure | Rel. Brier regret vs Oracle | Extra shots vs Oracle (× S) | Total shots / inference |
|---|---|---|---|---|---|
| Always A0 | 0.993 | 0.976 | +99.6% | −1.88 | 1,792 |
| Always A1 | 0.948 | 0.869 | +36.2% | −1.88 | 1,792 |
| Always A2 | 0.772 | 0.645 | +57.2% | +0.12 | 5,376 |
| **Always A3** (best universal) | 0.287 [0.234, 0.343] | 0.059 [0.059, 0.061] | −1.2% | +0.12 | 5,376 |
| Always A4 | 1.000 | 0.988 | +98.8% | +0.12 | 5,376 |
| R_cat (5B rule) | 0.125 [0.102, 0.152] | 0.041 [0.028, 0.058] | +1.3% | +0.03 | 5,148 |
| **R_thr** (best simple rule) | **0.096 [0.080, 0.117]** | **0.020 [0.016, 0.027]** | **+0.3% [−0.4, +1.0]** | **+0.02** | 5,199 |
| R_obs (+ readout observable) | 0.097 [0.080, 0.122] | 0.019 [0.015, 0.026] | +0.2% | +0.02 | 5,196 |
| Oracle | 0 | 0 | 0 | 0 | 5,165 |

Total shots are mean per inference at S averaged over budgets, including 66·S/N probe shots for rules.

**Fitted R_thr:**
- readout probe error ≥ ≈ 0.0037–0.0044 → readout detected;
- gate contraction ≤ ≈ 0.97–0.98 → gate detected;
- cells: both → A3, gate → A2, readout → A1, none → A1 (A0 at 256 shots).

**Residual structure:**
- **Noise-only ceiling** (best model-agnostic action knowing the *true* noise point): 0.110 on train, driven by the mean-Z structure (0.59; other train structures 0.02–0.11), and **0.058 on val** (structures 0.03–0.10).
- **Structure association:** significant (p < 0.001) but small (conditional MI 0.04 nats on val).
- **Variance in ΔBrier:**
  - noise point η² 0.81–0.99, model 0.005–0.10 for A1–A3;
  - for A4 (tiny effect), model η² up to 0.65.

**Probe validity:**
- The readout probe tracks the true mean readout error almost perfectly (Spearman 0.999).
- The gate probe's contraction tracks depolarizing severity (−0.89 to −0.92) but **not thermal severity (−0.12)**. Thermal relaxation contracts the parity signal little, while ZNE still helps under it.
- The rule mostly needs gate *presence*, which depolarizing provides in all 16 noisy plots.

**Tolerance sensitivity** (val):

| ε | A3 share | R_thr material failure |
|---|---|---|
| 0.05 | 83% | 0.020 |
| 0.20 | 55% | 0.075 |

**G3C (registered rule): FAIL — `negligible_regret`.** The best simple rule's val material failure is 0.020, below 0.05.

| Criterion | Value | Threshold | Result |
|---|---|---|---|
| P1 useful actions | A2, A3 | ≥ 2 | holds |
| P2 rule failure | 0.096 | ≥ 0.15 | fails |
| P3 noise-only ceiling (val) | 0.058 | ≥ 0.10 | fails (3 val and 3 train structures ≥ 0.05) |
| P4 rule failure − label noise | 0.088 | ≥ 0.10 | fails |
| P5 material failure | 0.020 | ≥ 0.10 | fails |
| P6 support | — | — | holds |

**No learned controller is trained.**

**Interpretation:**
- **Continuous joint noise does not create a decision problem with material structure left for learning.** It *removes* most of the choice: in our continuous joint-noise design (16 of 17 gate settings carry gate noise), combined mitigation (A3) is almost always within tolerance. The remaining choice is "is readout noise large enough to add readout mitigation to ZNE?", which one probe threshold answers.
- **The best fixed policy, always A3**, never breaks the reliability tolerance and overspends materially in 5.9% of contexts.
- **R_thr** cuts that to 2.0% at Oracle-level mean Brier (CI includes 0); 4% of its choices exceed the 10% tolerance. It uses +0.02 S extra action shots per inference (excluding probes).
- **Model dependence is real but small.** It is concentrated in the mean-Z readout, which a one-descriptor rule (R_obs) absorbs.

**Runtime:** 24,542 s wall (6.8 h) on 15 workers; 95 CPU-h under memory pressure (≈ 25% of CPU time in compression); exact stage 75%, finite-shot 25%; main-process peak 2.6 GB.

### 3.14 Final held-out evaluation (results; one-time sealed test)

**Protocol:** [`PREREG_FINAL.md`](PREREG_FINAL.md), pushed with code (`b7df65f`). One implementation correction (`919ecdc`) was made before any output: JSON rule keys. The Phase 7 freeze (`5e09c85`) recorded the learned comparators' validation fingerprints.

**Unlock:** single, at 2026-10-08T21:28:24Z on `5e09c85`. Two logged reads, the 5C and 5B sealed test files, both matching their committed content hashes. The refitted comparators reproduced their frozen fingerprints.

**Primary environment: Phase 5C test** (16 unseen models, 4 unseen structures including one mean-Z; 65,280 decisions; all budgets):

| Policy | Failure | Material failure [95% CI] | Rel. Brier regret | Total shots / Oracle |
|---|---|---|---|---|
| Always A0 / A1 | 0.986 / 0.956 | 0.960 / 0.900 | +93% / +36% | 0.35 |
| Always A2 / A4 | 0.658 / 1.000 | 0.527 / 0.983 | +52% / +92% | 1.04 |
| Always A3 | 0.400 | 0.059 [0.059, 0.059] | −1.4% | 1.04 |
| R_cat | 0.249 | 0.045 | +1.0% | 0.99 |
| **R_thr (deployable)** | 0.219 | **0.020 [0.015, 0.026]** | **−0.03% [−1.7, +1.2]** | **1.006** |
| R_obs | 0.089 | 0.021 [0.017, 0.025] | +0.7% | 1.006 |
| L_logistic | 0.173 | 0.094 | +2.4% | 0.95 |
| L_tree3 | 0.086 | 0.026 | +0.7% | 1.008 |
| L_gbt | 0.065 | 0.021 [0.005, 0.044] | +0.3% | 1.009 |
| L_gbt_benefit | 0.150 | 0.026 | −0.26% | 1.013 |
| Oracle | 0 | 0 | 0 | 1 |

**Secondary environment: Phase 5B test** (categorical noise; 5,120 decisions):
- **R_thr:** material failure 0.088.
- **R_cat:** 0.064.
- **R_obs:** 0.119.
- **Learned comparators:** 0.12–0.44.
- **Universal policies:** ≥ 0.50.

**Hypotheses:** H1, H2, H3 and H4 are all **supported** (`final_metadata.json`).

**Per structure** (`final_by_structure_5c_test.csv`):
- **Parity test structures:** R_thr fails 7–11% (1.6–2.8% material).
- **Mean-Z test structure:** R_thr fails 62% but only 1.4% materially. It adds readout mitigation that mean-Z readouts do not need, at a cost of two calibration circuits.
- **R_obs** absorbs this (11%).
- **Learned comparators on mean-Z** reach 5–30% *material* failure. With one mean-Z structure in training, they do not generalize to a new mean-Z structure, while the coarse rule stays robust.

**Reading:**
- The confirmatory test reproduces validation for R_thr (material failure 0.020 on both). The learned comparators' material failure moved by up to 15 pp between validation and test (L_gbt 0.107 → 0.021; L_tree3 0.175 → 0.026).
- A two-threshold probe rule fitted once on 8 training structures is near-Oracle on unseen structures in both noise environments: within 0.03% of Oracle Brier, 0.6% more shots than the Oracle, and 3.4% fewer than always-combined mitigation.
- Learned comparators at best tie it, and generalize worse to an unseen readout type.

### 3.15 Robustness and ablations (validation only; exploratory)

**Data:** `scripts/ablations.py` → `ablation_probes.csv`, `ablation_probe_cost.csv`. The sealed test was not reused.

**Probe ablation:** rules refitted on 5C train like R_thr; material failure on validation.

| Variant | 5C val | 5B val |
|---|---|---|
| Both probes (R_thr) | 0.020 | 0.094 |
| **Gate probe only** | **0.018** | 0.094 |
| Readout probe only | 0.062 | 0.500 |
| No probe (fixed per budget) | 0.059 | 0.500 |

- The gate probe carries the material decision: whether to pay 3× for ZNE-based mitigation.
- The readout probe only chooses between A2 and A3, which differ by two calibration circuits.

**Probe-cost break-even.** R_thr saves, per inference against always-A3, about 0.1·S shots under continuous noise and about 0.8·S under categorical noise. The probes cost 66·S shots per batch. Probing therefore pays off only above **≈ 645–685 transactions per batch** (5C) or **≈ 80** (5B). Study batches were 28k–57k.

**Already registered:** shot budget (§3.13: < 3% of decisions change); tolerance ε 0.05–0.20 (§3.13); learned-model complexity (§3.14).

## 4. Execution

| Item | Specification |
|---|---|
| Basis gates / transpilation [ENG E09] | `{rz, sx, x, cx}` with noiseless `rz`. Transpile parametrized circuits once, then bind. Assert input-independent gate counts. Backend snapshots use their own basis (e.g. `cz`). |
| Simulator [ENG E07] | Aer `density_matrix`. Phase 0 smoke test confirmed on the development Mac (Qiskit 2.5.2, Aer 0.17.2). |
| Exact-distribution cache [ENG E08] | Exact noisy distribution, classical readout confusion, multinomial shot sampling. **Validated in Phase 3B** against direct Aer shots under the five registered tests (§3.9; E40). Phase 0 data point: total variation distance 0.014 at 4,096 shots. |
| Shots [OPEN O07] | [RR] 1024. Phase 3B pilot: 1,024 × 20 replicates (§3.9). Sensitivity budgets still to be decided. |
| Core-map mode [DEF A14] | Finite-shot core map with replicates versus exact-only. Deferred with the endpoint decision. |

## 5. Noise

### 5.1 Anchor grid [RR] (`configs/noise/anchors_rr_v1.yaml`)

| Family | Low | Medium | High | Role |
|---|---:|---:|---:|---|
| Depolarizing $p_1$ / $p_2$ | 0.0005 / 0.005 | 0.001 / 0.010 | 0.003 / 0.020 | anchor |
| Symmetric readout flip | 0.005 | 0.020 | 0.050 | **negative control** (A07) |
| Thermal $T_1$ / $T_2$ (µs) | 200 / 250 | 100 / 150 | 50 / 70 | anchor |
| Combined | all of the above at matched severity | | | anchor |

**Conventions [ENG], enforced by the schema:**
- $p_1$ and $p_2$ are Qiskit `depolarizing_error` parameters, not infidelities.
- Gate times are 35 ns and 300 ns.
- $T_2\le 2T_1$.
- $p_{01}+p_{10}<1$.
- Single-family profiles activate exactly one noise source.

**Limitation:** idle-qubit decoherence is not modelled unless circuits are scheduled with delays (§19).

### 5.2 Additions

- **[ACC A07]** Asymmetric readout ($p_{01}\ne p_{10}$) is supported. Anchor values must be justified, not invented [OPEN O20]. Phase 3B used three **synthetic asymmetric readout stress-test profiles** (`synthetic_asym_v1`: ar-005/020/050, $p_{10}=3p_{01}$); they are not device calibration data, and O20 stays open.
- **[DEF A05]** Continuous noise-parameter sampling is deferred.
- Backend-derived snapshots [RR]: 1–2, frozen to files.
- Held-out noise design for out-of-distribution tests [OPEN O16].

## 6. Mitigation actions

| Action | Procedure |
|---|---|
| None | Task execution at the nominal shot budget. |
| Readout [ENG E11] | Tensored per-qubit inversion from 2 calibration circuits (counts only), then Euclidean projection onto the simplex for rows with negative quasi-probabilities (Phase 4). Full $2^n$ calibration remains a variant. |
| ZNE [RR + ENG E10] | Global folding of the transpiled circuit, factors (1, 3, 5), linear least-squares extrapolation (Richardson diagnostic); equal shots per factor; parity clipped to [−1, 1] (O09, registered in Phase 4). Readout noise is not amplified by folding. |
| Combined | Readout correction at each scale factor, then extrapolation. |
| PEC | Exploratory only (`F03`). |

**Nesting [ENG].** All actions are derived from one set of raw runs per context, giving paired outcomes (common random numbers).

### 6.1 ZNE variance and resource-matched None [ACC A02] — derived, not a result

At factors (1, 3, 5) with equal shots per factor:

| Extrapolator | Weights | $\sum c^2$ |
|---|---|---:|
| Linear | $(13/12,\ 1/3,\ -5/12)$ | ≈ 1.46 |
| Richardson | $(15/8,\ -5/4,\ 3/8)$ | ≈ 5.22 |

**Toy model.** If noise uniformly contracts the signal by $(1-\kappa)$, linear ZNE beats None at equal per-factor shots only if $\kappa>0.17$. It beats None given the **same total shots** only if $\kappa>0.52$.

**Rule (A02).** Every action that consumes extra resources is compared against **both**:
1. None at the nominal shot budget;
2. **None with an equal total quantum execution/shot budget**, including calibration and probe resources where the comparison requires it.

## 7. Resource accounting [F25; ACC A01]

**Recorded raw, per observation** (`ResourceUsage`):

| Category | Fields |
|---|---|
| Probe | `probe_circuit_executions`, `probe_shots` |
| Task | `task_circuit_executions`, `task_shots` |
| Mitigation | `mitigation_circuit_executions`, `mitigation_shots` (scale-factor > 1 runs) |
| Calibration | `calibration_circuit_executions`, `calibration_shots` |
| Totals | `total_circuit_executions`, `total_shots` (validated equal to the sums) |
| Time | `depth_weighted_shots` (host-independent duration proxy); `simulator_execution_seconds`; `qpu_execution_seconds` |
| Wall clock | `wall_clock_seconds`: **stored separately; never a decision cost** |

**Accounting rules:**
- **Not collapsed.** There is no single or monetary cost field. Cost functions are computed later from the raw quantities [OPEN O08].
- **Probe cost** belongs to every policy that probes, which means Q-TRACE (A01). Never, Always and the fixed threshold incur none. Probe size [OPEN O19].
- **Closed form.** Under equal shots per factor and tensored calibration, the incremental **shot** counts are:
  - Readout: $2s_{cal}$;
  - ZNE: $2|b|s$;
  - Combined: $2|b|s+2s_{cal}$.

  Here $|b|$ is the batch size, $s$ the shots per circuit, and $s_{cal}$ the shots per calibration circuit. Readout is cheap for large batches, so the substantive decision concerns ZNE and Combined.

## 8. Q-TRACE inputs and leakage [ACC A01, A12]

The authoritative list is [`configs/features/registry.yaml`](../configs/features/registry.yaml). Tests snapshot the deployable set.

| Status | Features |
|---|---|
| **Deployable, pre-execution** | `p1`, `p2`, `readout_p01`, `readout_p10`, `t1_us`, `t2_us`, `n_qubits`, `circuit_depth`, `n_1q_gates`, `n_2q_gates`, `ansatz`, `ansatz_reps`, `shots_per_circuit` |
| **Deployable, probe** (label-free) | `probe_prediction_entropy`, `probe_shot_variance` |
| **Deployable, frozen at training** | `clean_val_auprc_at_freeze`. Measured once at freeze; never recomputed under the current noise or on a controller-test panel. |
| **Deployable for Q-TRACE-A only** | `recent_labelled_batch_performance`. Past batches with arrived labels only. |
| **Offline only** (never inputs) | `model_id`, `model_seed`, `noise_seed`, `shot_seed`, `noise_profile_id`, `noise_family`, `noise_severity`, `transaction_label`, `current_batch_accuracy`, `current_batch_auprc`, `mitigated_scores`, `zne_scaled_outputs`, `realized_delta`, `oracle_action` |

**Caveats:**
- **Sim-to-real gap.** Noise parameters are exact in simulation but estimated on hardware.
- **Low diversity.** Circuit features take only 4 values in the core pool, and `n_qubits` is constant.
- **Model features.** Additional candidates are still open [OPEN O13].

## 9. Counterfactual dataset (Phase 6)

**Contexts:**
- controller-train models × noise profiles;
- controller-val models × the same profiles (missing in [RR]'s matrix, but required);
- controller-test models × held-out profiles [OPEN O16], generated under lockbox.

**Targets.** Δ is recorded per replicate. The target is the replicate mean with its standard error [OPEN O10].

**Module boundary.** Records are written only by `qtrace.counterfactual` (rule R1).

## 10. Predictors (Phase 7) [RR]

**Predictors:**
- constant;
- noise-only linear;
- linear;
- random forest;
- **XGBoost (primary)**;
- MLP and quantum controller, both optional.

**Method:** grouped cross-validation by `model_id`; hyperparameters chosen on controller-validation only.

## 11. Policies

| Policy | Status |
|---|---|
| Never; Always-ZNE; Always-best-fixed | [RR] |
| Threshold (binary + multi-action variant), tuned on controller-train/val only | [RR] + [ACC A11] |
| **Resource-matched None** | [ACC A02] |
| **Zero-additional-quantum-cost classical correction**: threshold adjustment, probability calibration, monotonic recalibration where applicable. Fitted on training/validation data only, never on the locked test set. | **[ACC O22 → F26]**; method not frozen |
| **Q-TRACE-S** (probe → features → decision; probe cost charged) | [RR] + [ACC A01] |
| Q-TRACE-A | [RR], extension |
| Oracle: selects on an independent replicate; evaluation only | [RR] + [ACC A08] |

## 12. Metrics [ACC A03, A13]

**Fraud discrimination**
- AUPRC is the **provisional** principal metric: step-wise average precision, weighted where panels are weighted.
- AUROC.
- Precision@k.

**Probability and threshold sensitivity**
- Recall, precision, F1, F2 and recall@precision, at τ.
- Brier score and ECE.

**Ranking and distortion versus clean scores (A13)**
- Spearman ρ and Kendall τ.
- Fraction of threshold crossings.
- Mean absolute score shift.
- Clip fraction and ties.

**Predictor and policy metrics**
- Predictor: MAE, RMSE, R², Spearman.
- Policy: metric outcomes, intervention rate, raw resources and derived costs, oracle regret, $R_{oracle}$.

**[OPEN O14 / DEF A14] Endpoints.** The final primary and secondary endpoints are **not frozen** until the pilot shows which metrics respond meaningfully to noise and mitigation. They **must** be frozen before the locked evaluation (§17). To limit analytic flexibility, they should be frozen as early as the pilot evidence allows, and on **mechanistic** grounds rather than by picking whichever metric shows the larger effect.

## 13. Statistical analysis [RR]

**Unit hierarchy:** model → context → action → transaction → shots.

**Primary comparisons:** Q-TRACE versus Threshold, Always and Never. α = 0.05, Holm-corrected. Tested at pre-registered operating points [OPEN O11].

**Method:**
- Paired hierarchical bootstrap.
- Wilcoxon signed-rank test where distributions are non-normal.
- McNemar test as a supplement.
- Mixed effects for H1.
- Effect sizes always reported.

**Sample size [ACC-in-principle A06].** [RR]'s 8 held-out models give an effective n between 8 and 64, against a power target of 96–128 independent contexts. N follows the Phase 3B benchmark and a simulation-based power analysis [OPEN O15].

**Hypotheses** are as corrected in PROJECT_SPEC §4: H1 per A09; H3 per A10, with all three conditions confirmed by the PI. H3 is reported as *not applicable* wherever the reference does not clearly beat Never.

## 14. Ablations [RR]

**Planned:**
- remove model, circuit, noise, or probe/uncertainty features;
- noise-only;
- no cost awareness;
- binary actions;
- classical versus quantum controller;
- static versus adaptive;
- **probe versus no probe** (A01).

**Limitation.** With 4 architectures (A05 deferred), the circuit-feature ablation effectively tests *architecture identity*. Claims are limited to unseen **initializations** of seen architectures.

## 15. Generalization tests

| Test | Status |
|---|---|
| Unseen model seeds | Core |
| Held-out noise strengths and families | Core; meaningful continuous tests need deferred A05 |
| Backend snapshots | Core |
| 6 qubits | Extension; confounded with the k = 6 representation |
| BankSim | Extension |
| IBM hardware | Extension |

## 16. Go/no-go gates

| Gate | Phase | Question | If it fails |
|---|---|---|---|
| **G1** | 3B (evaluated 2026-10-07: **CONDITIONAL PASS**, §3.9) | **A13 classification**, for every major noise family (including the symmetric-readout negative control): is the effect mostly monotonic score transformation, ranking distortion, calibration distortion, threshold-crossing change, or genuine discrimination degradation? Plus heterogeneity beyond replicate noise. | If all families are monotonic and effects are uniform, revisit O01, O14 and A07 with the PI **before** Phase 6. Do not build a controller on a null premise. |
| **G2** | 4 (evaluated 2026-10-07: **CONDITIONAL PASS**, §3.10) | Does mitigation change metrics materially in some contexts but not uniformly, including against resource-matched None (A02)? Does the optimal action vary? | Shrink the action space. |
| **G3A** | 5A (2026-10-07: **PASS**, §3.11) | Is the independent pool large and diverse enough? | Stop |
| **G3B** | 5B (2026-10-07: **FAIL**, §3.12) | Is there a learned-controller decision problem beyond a probe-based fixed rule? | **Stop; no Q-TRACE training; reframe (PI)** |
| **G3C** | 5C (2026-10-08: **FAIL**, §3.13) | Under continuous joint noise and budgets, is there residual decision complexity (all six brief criteria) beyond the best simple probe rule? | **No controller; negative-result path with a frozen final test** |
| **Final (H1–H4)** | Final test (2026-10-08: **H1–H4 supported**, §3.14) | On sealed held-out structures, is the frozen simple probe rule near-Oracle, and does any fixed learned comparator add meaningful value? | **Use the simple rule; a learned controller is unnecessary** |
| **G3** | 7 | H2 on controller-validation. | Report as unpredictable. |
| **G4** | 8 | H3–H5 on the locked controller-test set. | Report honestly. Threshold ≈ Q-TRACE is a finding. |

## 17. Freeze and lockbox

1. **Freeze** these before any controller-test analysis:
   - endpoints (O14);
   - ε and the minimum meaningful resource saving (A10, O12);
   - cost function(s) (O08);
   - operating points (O11);
   - panel and partition design (O06, O21);
   - probe design (O19);
   - predictor and policy configs;
   - the controller-test context list.
2. Commit, then tag `protocol-v1.0`.
3. Controller-test outcomes live under the gitignored `results/lockbox/` and are read only by the single post-freeze evaluation script.

## 18. Hardware validation (Phase 10) [RR]

- **Scale:** about 24 logical bundles (None, Readout, ZNE), each with 16–32 transactions, on the IBM Open Plan quota (to be confirmed when run).
- **Metric:** score-level agreement with clean simulation. **Not AUPRC.**
- **Metadata:** record full backend metadata.
- **API check:** the [RR] snippet's `qiskit_ibm_runtime.executor_estimator` import path is unconfirmed; check it against the installed version.

## 19. Threats to validity

**From [RR]:**
- small qubit count;
- anonymized 2013 data;
- synthetic noise;
- simulator approximations;
- subsampled panels.

**Added here:**
- dataset-level PCA leakage;
- exact duplicates (1,081 removed before splitting);
- `Time`-only near-duplicate groups: kept, but held within one partition (O23), so they cannot leak across partitions;
- unmodelled idle decoherence;
- 4 architectures only (A05 deferred);
- noise features exact in simulation but estimated on hardware;
- the literature in [RR] is unverified;
- the probe adds cost and a design choice (O19) that could favour or penalize Q-TRACE.

## 20. Deviations log

| Date | Section | Change | Reason | Approved by |
|---|---|---|---|---|
| — | — | (none; protocol not frozen) | — | — |
