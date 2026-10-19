# Phase 3B — Pre-registration: controlled quantum-noise characterization

| | |
|---|---|
| **Status** | PRE-REGISTERED. Committed and pushed before the real experiment. |
| **Date** | 2026-10-07 |
| **Machine-readable** | [`configs/noise_study/p3b_v1.yaml`](../configs/noise_study/p3b_v1.yaml) (authoritative), [`configs/noise/anchors_rr_v1.yaml`](../configs/noise/anchors_rr_v1.yaml), [`configs/noise/synthetic_asym_v1.yaml`](../configs/noise/synthetic_asym_v1.yaml), [`configs/experiments/phase3b_noise.yaml`](../configs/experiments/phase3b_noise.yaml) |
| **Exclusions** | No mitigation (ZNE, readout mitigation, combined, PEC). No Q-TRACE controller, predictor, policy, bandit or RL. No retraining. Controller partitions locked. |

## 1. Questions

1. Which noise families reduce fraud discrimination?
2. Which distort ranking?
3. Which mainly change calibration or score scale?
4. Which create threshold instability?
5. How do the effects change with severity?
6. Is the degradation heterogeneous enough to justify QEM experiments? This ends in a formal **G1** verdict.

## 2. Models (frozen; never modified)

| Role | Model | Artifact SHA-256 | Circuit |
|---|---|---|---|
| **Primary** | P3A-R `e3-r2-par` | `1da69395…0855a` | E3 encoder, ZZFeatureMap (reps 1, full) + RealAmplitudes reps 2 (linear), parity. Transpile seed 1154577741. |
| Exploratory pilot-model contrast | P3A-original `vqc3a_top4_ra1` | `9c7fc390…100c` | E0 encoder, RealAmplitudes reps 1, parity. Transpile seed 1824407106. |

- **Artifact integrity.** The artifact hashes are verified before and after the run, and the files must remain byte-identical.
- **Use of the contrast model.** P3A-original has known encoding defects. Its results are an *exploratory pilot-model contrast* and are **never** evidence for H1. Systematic model-specific heterogeneity requires the later independently trained pool.
- **Known limitation (O25).** P3A-R is optimizer-budget-limited. This is accepted, and no optimizer study is run.

## 3. Data

- **Partition:** `vqc_val` only (28,372 rows, 47 frauds), in `row_id` order. Access phase `phase3b` allows `vqc_val` and nothing else, since `vqc_train` is not needed.
- **Persistence:** transaction-level scores and distributions are stored only in gitignored storage.

## 4. Noise construction (on the transpiled circuit)

- **Transpilation:** each frozen circuit is transpiled once, still parametrized, to `{rz, sx, x, cx}` with optimization level 1 and its recorded seed. Parameters are bound per transaction.
- **One-qubit gates** (`sx`, `x`): `depolarizing_error(p1, 1)` composed with `thermal_relaxation_error(T1, T2, 35 ns)`, in that order.
- **Two-qubit gates** (`cx`): `depolarizing_error(p2, 2)` composed with thermal(T1, T2, 300 ns) ⊗ thermal(T1, T2, 300 ns).
- **Inactive sources:** a noise source a profile does not activate is omitted. `p1` and `p2` are Qiskit depolarizing *parameters*.
- **Not modelled** (stated limitation): `rz` noise (virtual, noiseless), idle-qubit decoherence, crosstalk, leakage.
- **Readout:** an identical per-qubit confusion matrix `[[1−p01, p01], [p10, 1−p10]]` is applied classically to the exact output distribution in Stage 1. This is mathematically equivalent to Aer's independent per-qubit `ReadoutError` and is validated against direct Aer shots (§9).
- **Score:** z = ⟨Z⊗Z⊗Z⊗Z⟩ from the measured distribution, and **p_fraud = (1 − z)/2**.

## 5. Noise matrix (15 conditions + clean)

| ID | Family | Severity | p1 | p2 | p01 | p10 | T1 / T2 (µs) | Role |
|---|---|---|---:|---:|---:|---:|---|---|
| clean | — | — | 0 | 0 | 0 | 0 | — | reference |
| dep-low | depolarizing | low | 0.0005 | 0.005 | 0 | 0 | — | anchor |
| dep-medium | depolarizing | medium | 0.001 | 0.010 | 0 | 0 | — | anchor |
| dep-high | depolarizing | high | 0.003 | 0.020 | 0 | 0 | — | anchor |
| ro-sym-low | readout (symmetric) | low | 0 | 0 | 0.005 | 0.005 | — | **negative control** |
| ro-sym-medium | readout (symmetric) | medium | 0 | 0 | 0.020 | 0.020 | — | **negative control** |
| ro-sym-high | readout (symmetric) | high | 0 | 0 | 0.050 | 0.050 | — | **negative control** |
| th-low | thermal | low | 0 | 0 | 0 | 0 | 200 / 250 | anchor |
| th-medium | thermal | medium | 0 | 0 | 0 | 0 | 100 / 150 | anchor |
| th-high | thermal | high | 0 | 0 | 0 | 0 | 50 / 70 | anchor |
| comb-low | combined | low | 0.0005 | 0.005 | 0.005 | 0.005 | 200 / 250 | anchor |
| comb-medium | combined | medium | 0.001 | 0.010 | 0.020 | 0.020 | 100 / 150 | anchor |
| comb-high | combined | high | 0.003 | 0.020 | 0.050 | 0.050 | 50 / 70 | anchor |
| ar-005 | readout (asymmetric) | low | 0 | 0 | 0.0025 | 0.0075 | — | **synthetic asymmetric readout stress-test** |
| ar-020 | readout (asymmetric) | medium | 0 | 0 | 0.010 | 0.030 | — | **synthetic asymmetric readout stress-test** |
| ar-050 | readout (asymmetric) | high | 0 | 0 | 0.025 | 0.075 | — | **synthetic asymmetric readout stress-test** |

- **The 12 anchors** are unchanged from [RR] (`anchors_rr_v1`).
- **The three AR profiles** are *synthetic asymmetric readout stress-test profiles*. They are **not** IBM or device calibration measurements, and O20 stays open.

## 5b. Disclosure

No noisy simulation of either model was run before registration. Prior expectation from theory (protocol §3.2): exact symmetric readout is an affine contraction of parity, so ranking metrics should be invariant to it.

## 6. Clean reference and threshold

- **Clean reference:** exact clean scores computed once per model through the same Aer density-matrix pipeline with no noise. They are cross-checked against the frozen exact engine to within 1e-10.
- **Pairing:** every condition is paired with the clean reference on the identical ordered rows.
- **Frozen clean threshold τ:** the max-F1 threshold on exact clean `vqc_val` scores, with ties going to the highest threshold. This is the same procedure as in the Phase 3A-R and 3A evaluations. τ is **never re-tuned** per condition.

## 7. Stage 1: exact noisy distributions (A13 diagnostics)

Aer `density_matrix` method, with `save_probabilities` for every transaction and condition (no shots). Per condition and model:

| Group | Measures |
|---|---|
| Discrimination | AUPRC, ΔAUPRC, AUROC, ΔAUROC (Δ = noisy − clean) |
| Ranking | Spearman and Kendall τ versus clean scores; top-K overlap for K ∈ {47, 100, 284} (47 = number of frauds; 284 = top 1%) |
| Score distortion | mean, median and mean-absolute score shift; variance change and ratio |
| Calibration | Brier, ΔBrier, ECE, ΔECE (10 equal-width bins, scikit-learn binning) |
| Threshold at frozen τ | fraction of rows crossing τ; fraud and legitimate crossing rates; precision and recall at τ (exploratory) |

**Paired uncertainty.** Stratified bootstrap with fixed class counts and 1,000 resamples. It uses the **shared Phase 2 `vqc_val` resamples**, and the clean and noisy metrics are computed on the same resample each time. 95% percentile intervals for ΔAUPRC, ΔAUROC, ΔBrier and ΔECE.

**Reading.** With only 47 frauds, intervals will be wide. Effect sizes are reported; no significance claims beyond the intervals.

## 8. A13 labels (multi-label; pilot-indicative; continuous evidence is primary)

| Label | Rule |
|---|---|
| `ranking_preserving` | Spearman ≥ 0.999 **and** Kendall ≥ 0.995 **and** the ΔAUPRC CI contains 0 **and** the ΔAUROC CI contains 0 |
| `ranking_distortion` | Spearman < 0.999 **or** Kendall < 0.995 **or** top-47 overlap < 0.95 |
| `calibration_distortion` | Spearman ≥ 0.99 **and** either (\|ΔBrier\| ≥ 10% of clean Brier with the ΔBrier CI excluding 0) or (\|ΔECE\| ≥ 0.01 with the ΔECE CI excluding 0) |
| `threshold_distortion` | Spearman ≥ 0.99 **and** (crossing fraction ≥ 0.01 **or** fraud crossing rate ≥ 0.05) |
| `discrimination_degradation` | (ΔAUPRC CI upper bound < 0 **or** ΔAUROC CI upper bound < 0) **and** Spearman < 0.999 |

These thresholds are fixed **now** as pilot indicators. They are **not** the publication-level definition of "meaningful", which Phase 3B informs (PI §12).

## 9. E08: finite-shot sampler validation (before Stage 2)

**Setup**
- **Rows:** the first 256 `vqc_val` rows in `row_id` order.
- **Profiles:** {clean, ar-050, th-high, comb-high}, at 1,024 shots.
- **Comparison:** direct Aer execution (density matrix; full noise model including `ReadoutError`; `measure_all`; seed from key `p3b-e08`) against the cached exact distribution sampled multinomially (independent seed).

**All of the following must pass for every profile** (primary model):

| # | Test | Pass condition |
|---|---|---|
| 1 | Standardized parity residual u = (z_Aer − z_exact)/√((1 − z_exact²)/1024) | \|mean u\| ≤ 0.25 and var u ∈ [0.7, 1.3] |
| 2 | Pooled Pearson χ² of Aer counts against exact probabilities (bins with expected count < 5 merged per row) | p ≥ 0.001 |
| 3 | \|mean p_Aer − mean p_exact\| | ≤ 4 SE, with SE from the exact per-row variances |
| 4 | Mean per-row TVD (Aer vs exact) / mean per-row TVD (multinomial vs exact) | ∈ [0.9, 1.1] |
| 5 | Two-sample KS test between the Aer and multinomial residuals u | p ≥ 0.001 |

**If any test fails, Stage 2 does not run.**

## 10. Stage 2: finite-shot pilot (O07 pilot only)

- **Model:** primary only.
- **Conditions:** the clean condition plus all 15 noisy ones. Each uses 1,024 shots per transaction circuit and 20 replicates.
- **Seeds:** `shots` stream, key (`p3b-shots`, condition, replicate), independent across conditions and replicates.
- **Per replicate:** AUPRC, AUROC, Brier, and Spearman versus exact clean.
- **Comparisons:**
  1. exact noisy vs exact clean (Stage 1);
  2. finite-shot noisy vs **finite-shot clean of the same replicate index**.
- **Summaries:** mean, SD, minimum, maximum, and 5/50/95% quantiles across replicates.
- **Ties:** finite-shot scores lie on a 1/2048 grid. Ties are handled by scikit-learn's conventions.
- **Interpretation:** finite-shot ranking changes are expected and are **not** negative-control failures.
- **Not a decision:** these numbers do not freeze the final shot protocol.

## 11. Negative control (Stage 1, exact)

For ro-sym-low, ro-sym-medium and ro-sym-high, the noisy scores must be an exact affine image of the clean scores, z_noisy = (1 − 2p)⁴ z_clean.

| Check | Tolerance |
|---|---|
| max \|z_noisy − (1 − 2p)⁴ z_clean\| | ≤ 1e-10 |
| \|ΔAUPRC\| and \|ΔAUROC\| | ≤ 1e-9 |
| Spearman | ≥ 1 − 1e-9 |

Exact bitwise equality is not required. If the control fails, the run stops for an implementation review and no G1 verdict is issued.

## 12. G1 decision rule (primary model, Stage 1, negative controls excluded)

**Families:** depolarizing, thermal, combined, and synthetic asymmetric readout (low, medium, high).

**Severity trend.** A family has a severity trend if, from low to medium to high, ΔAUPRC is non-increasing or Spearman is non-increasing (tolerance 1e-9).

| Verdict | Condition |
|---|---|
| **PASS** | Some condition is labelled `discrimination_degradation`, **or** labelled `ranking_distortion` with top-47 overlap < 0.95, **and** its family shows a severity trend. |
| **CONDITIONAL PASS** | Not PASS, but some condition is labelled `calibration_distortion`, `threshold_distortion`, or `ranking_distortion` without the top-47 criterion. |
| **FAIL** | Otherwise. Stop, report the negative result, and propose how to reconsider the research question. **Noise is never increased to rescue the hypothesis.** |

## 13. Exploratory pilot-model contrast

P3A-original goes through the same Stage 1 diagnostics. It is reported separately, never in G1 and never as H1 evidence.

## 14. Runtime measurements

- exact clean simulation time;
- noisy simulation time per example and per profile;
- total Stage 1 time;
- E08 time;
- finite-shot sampling time;
- peak resident memory.

These feed O15, the noise-matrix size, seed counts, shot budgets and the power analysis.

## 15. Outputs (aggregate only; transaction-level data gitignored)

**Tables** in `results/tables/p3b_*`:
- noise matrix;
- exact metrics per model;
- A13 labels;
- negative control;
- E08 validation;
- finite-shot replicates and summary;
- 2-D clean-vs-noisy score histograms;
- 1-D score histograms and calibration bins for the representative conditions (ro-sym-high, dep-high, th-high, comb-high, ar-050);
- metadata including the G1 verdict.

**Figures** A–E, drawn from the committed tables:
- **A:** ΔAUPRC against severity, by family;
- **B:** Spearman and Kendall against severity;
- **C:** clean-vs-noisy score density for representative conditions;
- **D:** score distributions and calibration;
- **E:** finite-shot variability.

---

## Execution record (appended after execution; sections 1–15 unchanged)

**Registration** was committed and pushed at `b5a14bb` before any noisy simulation of either model. The noise matrix, models, thresholds, A13 rules, E08 criteria, negative-control tolerances and G1 rule were executed **exactly as registered**. No condition was added or removed, no threshold changed, and no noise level was raised.

**Run order:** Stage 1 → negative control → E08 → Stage 2 → labels and G1.
- The negative control passed on both models (max affine residual ≤ 4.4e-16).
- E08 passed all five tests on all four profiles, so Stage 2 ran.
- The frozen artifacts were byte-identical before and after the run (file SHA-256 recorded in `p3b_metadata.json`).

**Implementation details not fixed by the text** (decided before any real result; tested on synthetic inputs):
1. **χ² bin merging (§9, test 2).** Per row, bins are sorted by expected count. All bins with expected count < 5 form one group, which absorbs the next-smallest bins while its expectation is still < 5. A row reduced to one group contributes nothing.
2. **Residuals (§9, test 1).** Rows with 1 − z² ≤ 1e-12 would be excluded from the residuals; none occurred (256 of 256 used). Residual variance uses ddof = 1.
3. **Round-off.** Scores p = (1 − z)/2 are clipped to [0, 1], and negative probabilities from simulator round-off are clipped (rows renormalized) before multinomial sampling.
4. **Seeds.** Aer seed = `derive_seed(shots, "shots", "p3b-e08", profile, "aer") mod 2³²`. The independent multinomial seed uses key (`p3b-e08`, profile, `multinomial`). Stage 2 uses (`p3b-shots`, condition, replicate) as registered.
5. **Clean cross-check (§6).** Compared on the parity scale z: max |Δz| = 1.9e-15 (P3A-R) and 1.3e-15 (P3A-original).
6. **Two development issues, neither a scientific change.**
   - The configuration loader was first called with the repository root instead of the configuration root. This was caught by the unit tests before any data were read.
   - The static controller-partition guard flagged a metadata string containing a `ctrl_*` pattern, which was reworded.

**Erratum (wording only; no rule affected).** §10 says finite-shot scores lie on a 1/2048 grid. The fraud score p = n_odd/1,024 lies on a **1/1,024** grid; z lies on a 2/1,024 grid.

**Results:** `docs/EXPERIMENT_PROTOCOL.md` §3.9 and `results/tables/p3b_*`. Briefly:
- No condition is labelled `discrimination_degradation` for the primary model.
- All 12 non-control conditions are labelled `ranking_distortion` through Kendall τ < 0.995; top-47 overlap is ≥ 46/47.
- 11 are labelled `calibration_distortion` and 3 `threshold_distortion`.
- Every family shows a severity trend.
- **G1 = CONDITIONAL PASS.**
