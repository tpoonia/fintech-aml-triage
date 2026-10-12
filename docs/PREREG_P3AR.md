# Phase 3A-R — Pre-registration: VQC encoding/architecture repair

| | |
|---|---|
| **Status** | PRE-REGISTERED. Committed before any candidate was trained or cross-validated. |
| **Date** | 2026-10-07 |
| **Machine-readable** | [`configs/repair/p3ar_v1.yaml`](../configs/repair/p3ar_v1.yaml) (authoritative), [`configs/experiments/phase3ar_vqc.yaml`](../configs/experiments/phase3ar_vqc.yaml) |
| **Baseline kept immutable** | **P3A-original** = `vqc3a_top4_ra1` (commit `cca6877`): V17, V14, V12, V10; ±3 clip; θ ∈ [−π, π]; ZZFeatureMap reps 1; RealAmplitudes reps 1; parity; COBYLA; `vqc_val` AUPRC 0.104. Its files are never modified. |

## 1. Purpose and non-purpose

**Purpose.** Repair two structural problems found in Phase 3A:
1. clipping collapses many frauds onto identical encoded inputs;
2. the [−π, π] range interacts with the ZZFeatureMap's period-π single-qubit phase (aliasing).

A secondary question is whether the reps-1 ansatz is under-expressive.

**Not the purpose:** searching until the VQC is strong. A repaired VQC near AUPRC 0.10 is an acceptable outcome. No further architecture search follows without PI approval.

## 2. What was known before registration (disclosure)

Only **`vqc_train` descriptives of the encoding** were examined: clipping rates, collisions and state fidelities. No candidate was trained and no cross-validation was run. `vqc_val` was not touched.

| Clip (IQR) | Fraud values clipped | Frauds sharing an encoded vector | Distinct fraud vectors |
|---|---:|---:|---:|
| ±3 (E0/E1) | 75.0% | 123 / 213 | 91 |
| ±5 (E2) | 58.8% | 80 / 213 | 134 |
| ±15 (E3) | 9.6% | 2 / 213 | 212 |

Fraud |r| medians are 4.6–7.2 IQR, and 90th percentiles are 13–21. **E3 was added because of this table**, beyond the PI's minimum (E0, E1, E2): ±5 still clips most fraud values.

A state-collision probe (all frauds plus 3,000 legitimate rows) found 0 exact state collisions for every encoding. Near-identical pairs (fidelity > 0.999) numbered 15 / 21 / 37 / 273 for E0 / E1 / E2 / E3. E3 compresses the legitimate bulk into small angles.

## 3. Encodings

All use θ = (hw / c) · clip((x − median)/IQR, −c, c), with the P3A-original median and IQR fitted on `vqc_train`.

| ID | Clip c | Range [−hw, hw] | Role |
|---|---|---|---|
| E0 | 3 | [−π, π] | control (P3A-original) |
| E1 | 3 | [−π/4, π/4] | aliasing repair only (input collisions unchanged by design) |
| E2 | 5 | [−π/4, π/4] | wider clip, alias-safe range (PI) |
| E3 | 15 | [−π/4, π/4] | near-complete removal of fraud input collisions |

**Why hw = π/4.** The ZZFeatureMap applies P(2θ) per qubit. With θ ∈ [−π/4, π/4], the phase lies in [−π/2, π/2]. That is injective, and the two saturated extremes are antipodal rather than aliased. With hw = π/2 the extremes would alias (±π).

The pair terms 2(π − θᵢ)(π − θⱼ) still span more than 2π on any useful range. That is an inherent property of the ZZ map: no encoding makes it injective without collapsing separability (it would need |θ| ≲ 0.25). It is recorded, not repaired.

## 4. Candidate matrix (10 configurations; cap 12)

All candidates use the ZZFeatureMap (4 qubits, reps 1, full entanglement), RealAmplitudes with linear entanglement, p_fraud = (1 − z)/2, BCE with ε = 1e-7, and COBYLA (1,000 evaluations, rhobeg 1.0, tol 1e-4). No trainable classical scale or bias head.

| # | ID | Encoding | Ansatz reps | Observable | Eligible? |
|---|---|---|---|---|---|
| 1 | e0-r1-par | E0 | 1 | parity | control |
| 2 | e0-r2-par | E0 | 2 | parity | control |
| 3 | e1-r1-par | E1 | 1 | parity | by rule (§6) |
| 4 | e1-r2-par | E1 | 2 | parity | by rule |
| 5 | e2-r1-par | E2 | 1 | parity | by rule |
| 6 | e2-r2-par | E2 | 2 | parity | by rule |
| 7 | e3-r1-par | E3 | 1 | parity | by rule |
| 8 | e3-r2-par | E3 | 2 | parity | by rule |
| 9 | e2-r1-z0 | E2 | 1 | first-qubit Z | by rule (limited observable ablation) |
| 10 | e3-r1-z0 | E3 | 1 | first-qubit Z | by rule (limited observable ablation) |

First-qubit Z means Z on qubit 0, the qubit carrying V17.

## 5. Cross-validation (`vqc_train` only)

**Folds**
- 5 folds over `vqc_train` (127,677 rows, 213 frauds).
- **Group-aware:** rows sharing `V1`–`V28` + `Amount` stay together.
- **Stratified:** by any-fraud group.
- Deterministic, with the `split` seed stream and key `p3ar-folds`. Fold hashes are recorded.

**Per fold**
- **Training rows:** all fold-train frauds plus 4 legitimate per fraud, drawn from fold-train with the `undersample` stream (key `p3ar-cv`, fold). This mirrors the 3A subset rule, and the same rows are used for every candidate.
- **Evaluation rows:** the whole held-out fold at natural prevalence.

**Restarts**
- 3 initializations per candidate per fold, with identical seeds for every candidate (`model` stream, key `p3ar-restart`, restart index).
- The kept restart per fold is the one with the **lowest final training BCE**: the training objective, never held-out data.

**Recorded per (candidate, fold, restart)**
- initialization, trace length, final training BCE, convergence status;
- training AUPRC;
- held-out AUPRC, ROC-AUC and BCE;
- score variance, unique-score fraction, and fraud/legitimate separation (difference of mean scores).

## 6. Selection rule (deterministic)

**Eligibility,** computed mechanically from the `vqc_train` encoding diagnostics. A candidate is eligible only if its encoding
- (a) is single-qubit-phase injective (hw < π/2), **and**
- (b) leaves strictly fewer frauds sharing an encoded vector than the control E0.

This means E0 is excluded by (a) and E1 by (b), by design. E0 and E1 remain in the matrix as controls and diagnostics.

**Primary metric:** mean, over the 5 folds, of the held-out AUPRC of the kept restart.

**Ties:** eligible candidates within **0.005** of the best mean CV AUPRC are tied. Ties are broken, in order, by:
1. lower CV standard deviation across folds;
2. fewer ansatz repetitions;
3. fewer trainable parameters;
4. matrix order.

**Not used for selection:** BCE and calibration.

## 7. After selection

1. **Freeze** the encoding, observable, ansatz depth, restart rule, optimizer and budget.
2. **Final training:** retrain on the fixed **P3A subset** (`p3a-lpf4`, 1,065 rows, hash `4e04298d…`) with the same 3 restart seeds, keeping the lowest training BCE. Persist and hash the result.
3. **One-time evaluation on `vqc_val`,** reported regardless of outcome. Compare against:
   - P3A-original (replayed from its frozen artifact);
   - LR, RF and HGB trained on the same 1,065 rows and the selected encoding's angles.

   Primary metric: AUPRC (paired bootstrap, the Phase 2 resamples). Secondary: ROC-AUC, ranking, exploratory F1/F2, BCE, Brier/calibration.
4. **No return to selection** after seeing `vqc_val`.

## 8. Decision after evaluation (PI)

| Outcome | Action |
|---|---|
| Materially healthier | Becomes the Phase 3B base model |
| Weak but passing sanity | Still proceed to Phase 3B; no new search without approval |
| Pathological | Stop and report |

The pre-registered sanity conditions are those of Phase 3A (E33).

---

## Execution record (appended after execution; sections 1–8 unchanged)

**Registration** was committed at `05b1435` before any candidate ran. The candidate matrix and rules were executed exactly as registered: **no candidates added, no budget changed, no rule changed.**

**Implementation fixes made before any real candidate was trained** (no CV result existed at the time of either fix):
1. A parameter name in `run_cv` shadowed the training function. It was caught by the synthetic-data tests.
2. The first real invocation stopped with a `KeyError` before any training: the processed feature file has no raw `Amount` column for the group keys. Folds now reuse the stored Phase 1 group keys, which are tested to equal the recomputed ones.

**Selection** (`vqc_train` only): eligible candidates were e2-*, e3-* and the two first-qubit-Z variants. **Selected: `e3-r2-par`** (mean CV AUPRC 0.573, standard deviation 0.108), decided by the primary metric with no tie within 0.005. The best ineligible candidate was e1-r2-par at 0.558. Results: `results/tables/p3ar_cv_summary.csv` and `p3ar_selection.json`.

**One-time `vqc_val` evaluation** of the frozen selection: AUPRC 0.507 [0.363, 0.661], ROC-AUC 0.957. P3A-original: 0.104. After the first evaluation run, only a JSON boolean-formatting fix was made. Re-runs, including the reported run, reproduce identical numbers. Selection was not revisited.

**Finding to carry forward (O25):** the pre-registered 1,000-evaluation budget was binding for depth-2 candidates and for all final-training restarts.
