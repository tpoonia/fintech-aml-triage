# Phase 4 — Pre-registration: mitigation characterization

| | |
|---|---|
| **Status** | PRE-REGISTERED. Committed and pushed before the real experiment. |
| **Date** | 2026-10-07 |
| **Machine-readable** | [`configs/mitigation_study/p4_v1.yaml`](../configs/mitigation_study/p4_v1.yaml) (authoritative), [`configs/experiments/phase4_mitigation.yaml`](../configs/experiments/phase4_mitigation.yaml), [`configs/mitigation/`](../configs/mitigation/) |
| **Exclusions** | No Q-TRACE controller, predictor, policy, utility or training. No model pool. No PEC. No retraining, retuning, re-encoding or threshold change. Controller partitions locked. |

## 1. Question

**Main question:** under which noise conditions and shot budgets does mitigation improve downstream fraud-detection behavior enough to justify its extra quantum execution cost?

**Deliverables:**
- a counterfactual benefit vector for every (condition × shot budget × replicate) context and every action;
- G2, which decides whether a selective controller is scientifically justified.

A negative result is a valid result. Phase 4 is not an attempt to obtain a positive QEM result.

## 2. Known before registration (disclosure)

1. **All Phase 3B results.** Exact noise leaves discrimination unchanged and mainly contracts the scores. Finite shots amplify that contraction; comb-high is the clearest discrimination loss.
2. **An engineering prototype of global folding** on the frozen P3A-R circuit, run with **synthetic parameter values only** (no transaction data):
   - U⁻¹ translated at optimization level 0 has the same noisy gates as U (18 CX, 28 SX).
   - λ = 1 / 3 / 5 gives 18 / 54 / 90 CX and 28 / 84 / 140 SX, with depth 35 / 133 / 231.
   - The ideal unitary is preserved to ≤ 6e-15.
   - Under comb-high **gate** noise (no readout), mean |z| on uniform(−π/4, π/4) angles falls from 0.105 to 0.041 to 0.018 for λ = 1, 3, 5.
   - Timing: 0.46 / 1.53 / 2.52 ms per row.

**Not done:** no mitigation of any kind was run on `vqc_val`, and no mitigation metric exists yet.

## 3. Frozen assets

| Asset | Value |
|---|---|
| Model | Frozen P3A-R `e3-r2-par`, artifact content SHA-256 `1da69395…0855a`, transpile seed 1154577741. Verified before and after the run. Never retrained, retuned or re-encoded. |
| Threshold | Frozen clean τ = 0.3770787869373289 (max-F1 on exact clean `vqc_val` scores; Phase 3B). Recomputed once and asserted equal. One τ is used for every action, condition, arm and replicate. |
| Data | `vqc_val` only (28,372 rows, 47 frauds), in `row_id` order. New access phase `phase4` allows `vqc_val` and nothing else; `ctrl_*` stay unread. |
| P3A-original | **Not used.** It is optional, cheap diagnostics only, and is omitted entirely. |

## 4. Noise conditions

Eight registered conditions, a subset of Phase 3B with identical parameters. Nothing is stronger and nothing is new.

| Condition | Phase 3B parameters | Why it is included |
|---|---|---|
| clean | none | Reference; every action is a negative control here. |
| ro-sym-high | symmetric readout p = 0.05 | Ranking-preserving calibration-distortion control (exact affine contraction). |
| ar-020 | p01 / p10 = 0.010 / 0.030 | Non-affine readout, medium. *Synthetic asymmetric readout stress-test profile* (not device data; O20 open). |
| ar-050 | p01 / p10 = 0.025 / 0.075 | Non-affine readout, high (same synthetic caveat). |
| dep-high | p1 / p2 = 0.003 / 0.020 | Gate noise. |
| th-high | T1 / T2 = 50 / 70 µs | Thermal relaxation. |
| comb-medium | dep-medium + th-medium + ro-sym-medium | Combined. |
| comb-high | dep-high + th-high + ro-sym-high | Combined; the strongest Phase 3B finite-shot degradation. |

## 5. Actions and baselines

| ID | Action | Main comparison? |
|---|---|---|
| **A0** | None: base circuit, S shots per circuit | yes |
| **A1** | Readout mitigation (§7) | yes |
| **A2** | ZNE (§8) | yes |
| **A3** | Combined: readout mitigation applied to each folded circuit, then ZNE | yes |
| **RM3** | None with 3S shots on the base circuit (**shot-matched**) | yes: the resource-matched comparator for A2 and A3 |
| RM9 | None with 9S shots (**two-qubit-exposure-matched**: 9S × 18 CX = (1+3+5)S × 18) | diagnostic only |
| A1-oracle | Readout inversion with the *true* confusion matrix | diagnostic upper bound; never in G2 or the main tables |
| A2-rich / A3-rich | Richardson (quadratic) extrapolation | diagnostic only |

- **A1's resource-matched comparator is A0.** A1 runs the base circuit with S shots plus two calibration circuits per batch of N = 28,372 inferences. ⌊(NS + 2S)/N⌋ = S, so the shot-matched comparator *is* A0. The calibration cost is reported separately and never hidden (§10).
- **PEC is not implemented** (deferred).

## 6. Applicability matrix (a priori, from physics)

| Condition | A1 readout | A2 ZNE | A3 combined |
|---|---|---|---|
| clean | negative control | negative control | negative control |
| ro-sym-high, ar-020, ar-050 | **applicable** | negative control | partial (readout component) |
| dep-high, th-high | negative control | **applicable** | partial (ZNE component) |
| comb-medium, comb-high | partial (ablation) | partial (gate part) | **applicable** |

**Every cell is executed.** A Q-TRACE controller never observes the noise family (A12), so the counterfactual record needs every action in every context. The label decides:
- how the main tables are organized;
- whether a cell can count toward G2 (applicable and partial: yes; negative control: no).

No cell is "not applicable": every action is physically executable in every context. PEC is the only not-applicable action.

## 7. Readout mitigation (A1; also inside A3)

1. **Calibration circuits.**
   - Prepare |0000⟩ (no gates) and |1111⟩ (one `x` per qubit), then measure.
   - They experience the profile's gate noise on `x` and its readout noise. That is what a real calibration would observe.
   - Each uses the arm's per-circuit shot setting S.
   - A fresh calibration is drawn for every (condition, arm, replicate).
2. **Estimate.** Per qubit q:
   - p̂01_q = fraction of |0000⟩ shots that read qubit q as 1;
   - p̂10_q = fraction of |1111⟩ shots that read it as 0.

   The estimator receives **counts only**, never the profile parameters. All per-qubit estimates are recorded.
3. **Inversion.** Each qubit's estimated 2×2 response is inverted and applied to the measured distribution (tensored; E11). This yields a quasi-distribution.
4. **Stability.** If any qubit has 1 − p̂01 − p̂10 < 0.5, the result is flagged unstable and reported; there is no fallback.
5. **Projection.** The quasi-distribution is projected to the nearest probability vector in Euclidean distance: the Smolin–Gambetta–Smith projection onto the simplex (literature UNVERIFIED per Q3; the algorithm itself is tested against a brute-force quadratic program). The fraction of rows needing projection, and the moved mass, are reported.
6. **Score.** z from the projected distribution; p = (1 − z)/2.
7. **Oracle diagnostic.** The same steps with the true confusion matrix, labelled oracle and kept out of the main comparison.

## 8. ZNE (A2; also inside A3)

1. **Folding.**
   - Global unitary folding of the **transpiled** circuit U: U(U⁻¹U)^k with k = 0, 1, 2 gives λ = 1, 3, 5.
   - U⁻¹ is `U.inverse()` translated to {rz, sx, x, cx} at optimization level 0.
   - The composite is **never re-transpiled**, so nothing cancels.
   - Every gate is folded. Noise sits on sx, x and cx; rz is virtual. The transpile seed is fixed and λ = 1 is the original circuit.
2. **Gate growth** (from the circuits; recorded in `p4_circuits.csv` together with a circuit hash):

   | λ | CX | SX | Depth |
   |---|---|---|---|
   | 1 | 18 | 28 | 35 |
   | 3 | 54 | 84 | 133 |
   | 5 | 90 | 140 | 231 |

3. **Shots.** Equal: S shots for each of the 3 circuits, so 3S per logical inference.
4. **Primary extrapolator: linear least squares** through (1, z₁), (3, z₃), (5, z₅), evaluated at λ = 0.
   - Weights (13/12, 1/3, −5/12).
   - Shot-variance amplification Σw² = 1.458.
5. **Diagnostic extrapolator: Richardson** (quadratic through the three points).
   - Weights (15/8, −5/4, 3/8); Σw² = 5.22.
   - Diagnostic only, never selected after the fact.
6. **Clipping.** The extrapolated z is clipped to [−1, 1], and the clipping rate is reported. The extrapolation operates on the parity expectation of each transaction.
7. **Known limitation, recorded and not acted on.** Under comb-high, λ = 5 is close to full decoherence (§2). Linear extrapolation will be biased toward zero there. The factors stay (1, 3, 5) as registered ([RR], E10); there is no post-hoc selection.

## 9. Shot budgets, replicates, sampling and pairing

- **Arms.** S = 1,024 per circuit (primary) and S = 4,096 per circuit (secondary). O07 was resolved by the PI.
- **Replicates.** 20 per (condition × arm × action).
- **Exact distributions.** Aer density-matrix distributions for every gate-noise signature (clean, dep-high, th-high, the comb-medium gate part, the comb-high gate part) at λ ∈ {1, 3, 5}, plus the two calibration circuits. Readout is applied classically. Sampling is multinomial from these cached distributions (E08 sampler, E40).
- **Draws per (condition, arm, replicate):**
  - n₁, n₃, n₅ with S shots each (λ = 1, 3, 5);
  - extra base-circuit draws of 2S (RM3) and 6S (RM9);
  - calibration draws c₀ and c₁ with S shots each.
- **Seeds.** `shots` stream, key (`p4-shots`, condition, arm, replicate, component), with component ∈ {lam1, lam3, lam5, rm_extra2, rm_extra6, cal0, cal1}.
- **Pairing within a context** (common random numbers):
  - A0 uses n₁.
  - A1 uses n₁ + c.
  - A2 uses n₁, n₃, n₅. In practice the λ = 1 run *is* the unmitigated run.
  - A3 uses n₁, n₃, n₅ + c.
  - RM3 uses n₁ + 2S extra; RM9 uses n₁ + 8S extra (nested).
- **Across** conditions, arms and replicates, draws are independent.

## 10. Cost accounting (raw; nothing collapsed)

**Recorded per action and arm**, per batch of N = 28,372 logical inferences and per inference (field names mirror `ResourceUsage`):
- logical inferences;
- task, mitigation and calibration circuit executions and shots;
- totals;
- noisy one-qubit gate-shots (Σ shots × (sx + x));
- two-qubit gate-shots (Σ shots × cx);
- depth-weighted shots (Σ shots × depth);
- simulator runtime and wall-clock time, kept separately (raw `runtime.json` only).

**Primary cost unit:** total shots per logical inference, including amortized calibration. Circuits per inference and gate-shots are secondary.

| Per inference (S = per-circuit shots) | Circuits | Shots | CX-shots |
|---|---|---|---|
| A0 | 1 | S | 18S |
| A1 | 1 + 2/N | S + 2S/N | 18S |
| A2 | 3 | 3S | 162S |
| A3 | 3 + 2/N | 3S + 2S/N | 162S |
| RM3 | 1 | 3S | 54S |
| RM9 | 1 | 9S | 162S |

Wall-clock time is never a decision cost.

## 11. Metrics (benefit vector; O14 resolved by the PI)

Per (context, action), on all 28,372 rows:

| Group | Measures |
|---|---|
| Discrimination | **AUPRC** (primary), AUROC |
| Calibration | Brier, ECE (10 equal-width bins) |
| Threshold at the frozen τ | precision, recall, F1, F2; crossing rate against the **exact clean** decisions (all, fraud, legitimate) |
| Ranking against exact clean scores | Spearman, Kendall, top-K overlap (K = 47, 100, 284) |
| Diagnostics | clipping rate, projected-row rate, calibration estimates |
| Cost | as in §10 |

**Deltas:**
- action − A0 (Table B);
- action − its resource-matched comparator (Table C): A1 vs A0, A2 and A3 vs RM3; RM9 is diagnostic.

**No scalar utility is defined** (§15 of the PI instruction).

## 12. Uncertainty

**Finite-shot deltas: two-stage bootstrap**, B = 1,000.
- Draw b uses the b-th resample of the **shared Phase 2 `vqc_val` stratified sequence** (fixed class counts), plus a replicate index r_b.
- r_b is drawn uniformly from the 20 replicates using the `bootstrap` stream, key (`p4-replicate-draw`). It is the same sequence for every context, so all actions are paired within a draw.
- Δ_b is computed on replicate r_b with weights w_b.
- **Interval:** 2.5 / 97.5 percentiles.
- **Point estimate:** mean over the 20 replicates of Δ on the unweighted full set.
- **Applies to:** A1−A0, A2−A0, A3−A0, RM3−A0, A2−RM3 and A3−RM3, for ΔAUPRC, ΔAUROC, ΔBrier, ΔECE, Δprecision@τ, Δrecall@τ and ΔF1@τ.

**Replicate quantiles:** 5 / 50 / 95% of Δ across replicates are reported for every comparison, diagnostics included.

**Exact deltas:** one-stage paired bootstrap, the Phase 3B procedure.

**Reading:** with 47 frauds, intervals are wide. Effect sizes are reported, and there are no significance claims beyond the intervals.

## 13. G2 rule (finite-shot, registered now; pilot-indicative minimum effects)

**G2 endpoints:** AUPRC (discrimination), Brier (calibration), F1@τ (threshold decisions). ECE, AUROC, precision, recall, crossings and ranking are reported but are not G2 endpoints.

**Resource-robust benefit (RRB)** for a cell (condition, arm, action) on an endpoint means: compared with the cell's resource-matched comparator (A1 → A0; A2, A3 → RM3), both of the following hold:

| Endpoint | Point estimate | Two-stage 95% interval |
|---|---|---|
| AUPRC | ΔAUPRC ≥ +0.01 | lower bound > 0 |
| Brier | ΔBrier ≤ −10% of the comparator's mean Brier | upper bound < 0 |
| F1@τ | ΔF1@τ ≥ +0.05 | lower bound > 0 |

**Harm** is the mirror image.

**Qualifying cells:** applicable and partial cells. Negative-control cells never qualify; any RRB there is reported as a finding and examined.

**Table D (descriptive best action per context):**
- For each of the 16 contexts (8 conditions × 2 arms) and each G2 endpoint, take the **cheapest** of A0 < A1 < A2 < A3 whose replicate-mean endpoint is within the endpoint's minimum effect of the best replicate-mean. For Brier, "within" means within 10% of the best value.
- Table D is descriptive only; it never trains anything.

**Verdict:**

| Verdict | Condition |
|---|---|
| **FAIL** | (i) no qualifying cell has RRB on any G2 endpoint; **or** (ii) for every G2 endpoint, Table D picks the same action in all 16 contexts (universal dominance, so no selective problem). → **STOP**; report the negative result and recommend reframing. |
| **PASS** | Not FAIL, **and** AUPRC RRB in at least **2** qualifying cells (discrimination improvement not explained by extra shots, and not a single isolated cell). |
| **CONDITIONAL PASS** | Not FAIL and not PASS. For example: mitigation fixes calibration or threshold behavior only, or AUPRC RRB appears in exactly one cell. |

G2 is **not issued** if any stopping rule (§16) has triggered.

## 14. Hypotheses (tested as registered, whatever the result)

| ID | Hypothesis | Operational test |
|---|---|---|
| H4.1 | Readout mitigation substantially improves calibration under readout noise. | A1 vs A0, Brier RRB, in ro-sym-high, ar-020 and ar-050 × both arms. Supported in 6/6, partial in 1–5, not supported in 0. |
| H4.2 | Under symmetric readout, exact readout mitigation does not improve ranking-based discrimination. | **Exact:** \|ΔAUPRC\|, \|ΔAUROC\| ≤ 1e-9 and max\|z_A1 − z_clean\| ≤ 1e-10 (also a negative control, §15). **Finite-shot:** the A1−A0 ΔAUPRC interval contains 0 in both arms. |
| H4.3 | Mitigation may improve finite-shot discrimination where contraction amplifies sampling noise. | AUPRC RRB (against the resource-matched comparator) in any of dep-high, th-high, comb-medium or comb-high, for A2 or A3, or A1 in comb-*. |
| H4.4 | Benefit varies across family, severity, action and shot budget. | Table D is not constant across contexts for at least one G2 endpoint, **and** the RRB status of some action differs between families, severities (comb-medium vs comb-high; ar-020 vs ar-050) or arms. Reported with the range of mean Δ across contexts. |
| H4.5 | Some actions cost more than their improvement justifies. | Some A2 or A3 qualifying cell (≥ 3× shots) has no RRB on any G2 endpoint, or shows harm. |

**Prior expectations from theory**, recorded so they cannot be invented afterwards:
- **(a) Symmetric readout.** With one calibration per replicate, A1 is nearly a common affine map on z, so finite-shot ΔAUPRC under symmetric readout is expected to be about 0. The projection and per-qubit calibration noise add only small perturbations.
- **(b) ZNE vs RM3.** Per transaction, ZNE combines three noisy estimates with weights of total variance 1.458/S, around a signal that decays with λ. RM3 averages 3S shots of the least-decayed circuit, variance 1/(3S). The per-transaction signal-to-shot-noise ratio of ZNE is therefore expected to be *lower* than RM3's. So **H4.3 is expected NOT to hold against RM3**, even where ZNE reduces bias (calibration). This expectation does not change the test.

## 15. Implementation validation (before the real experiment) and negative controls

**Unit tests, synthetic only; must pass before execution:**

| Area | Checks |
|---|---|
| Folding | λ = 1 is the identical circuit. The folded ideal unitary equals U for random bindings (≤ 1e-10). CX and SX counts are exactly λ×. Depth is recorded. Noise exposure (mean \|z\|) strictly decreases with λ. An independent engine (explicit channel evolution with `qiskit.quantum_info`) equals Aer for a noisy folded circuit. |
| Extrapolation | Linear is exact on linear data; Richardson is exact on quadratic data; constant data gives the constant. Vectorized over rows. |
| Clean ZNE | Exact: identity. Finite-shot: no systematic gain. |
| Readout | Calibration estimates converge to the truth. Tensored inversion exactly inverts the per-qubit confusion, including distinct per-qubit matrices and bit order. Projection is valid, idempotent on valid inputs and equals a brute-force quadratic program. The stability flag works. |
| No oracle leak | A1 and A3 are unchanged when the oracle input changes. |
| Costs | Resource accounting is checked by hand. The RM3 and RM9 shot totals are correct. Nested draws are correct. |
| Determinism | Seeded draws are deterministic. |
| Access | `phase4` refuses everything except `vqc_val`. The static guard covers `qtrace.mitigation` and the Phase 4 scripts. |
| Threshold | τ cannot be re-tuned per action: one τ is passed everywhere, and an AST check confirms it. |

**Run-time checks** (hard stop if violated):
1. The artifact hash is verified and the frozen τ reproduces to ≤ 1e-12.
2. Clean folded λ = 3, 5 distributions equal λ = 1 on all 28,372 rows to ≤ 1e-10 (ideal computation preserved on the real bindings).
3. Exact λ = 1 AUPRC, AUROC, Brier and ECE equal the committed `p3b_exact_metrics.csv` to ≤ 1e-9 for every condition.
4. Exact mean |z| strictly decreases with λ for every gate-noise condition.
5. **Exact negative controls:**
   - **NC1:** A1 with infinite-shot calibration under ro-sym-high, ar-020 and ar-050 recovers the clean scores: max|z − z_clean| ≤ 1e-10. For ro-sym-high, |ΔAUPRC| and |ΔAUROC| vs exact A0 are ≤ 1e-9 (H4.2).
   - **NC2:** A2 under clean equals clean to ≤ 1e-10.
   - **NC3:** A2 under pure readout equals A0 to ≤ 1e-10 (folding does not touch readout).
   - **NC4:** A1 under clean is the identity to ≤ 1e-10.
6. **E08 on folded circuits** (comb-high, λ = 3 and 5): 256 rows, 1,024 shots, direct Aer shots against the cached distribution sampler. Phase 3B's five criteria with identical thresholds.
7. **Calibration circuits** (comb-high and ar-050): 100,000 direct Aer shots against the cached exact distribution; merged χ² p ≥ 0.001.

**Finite-shot negative-control flag** (not a hard stop):
- Under clean, an RRB *improvement* in AUPRC for A1, A2 or A3 against its comparator is treated as a likely implementation error and investigated before G2.
- Finite-shot variability of the symmetric-readout control is expected and is not a failure.

## 16. Stopping rules

| Trigger | Consequence |
|---|---|
| A unit test, or run-time checks 1–5, fail | Stop; implementation review; no G2. |
| Check 6 or 7 fails | No finite-shot study; report. |
| The finite-shot clean flag fires and is unexplained | No G2 until resolved. |
| **G2 FAIL** | Stop; report the negative result; recommend reframing. No controller is built because of the project title. |

Noise is never increased, conditions are never added after results, and ZNE factors and extrapolators are never re-selected.

## 17. Outputs (aggregate only; transaction-level data gitignored)

**Tables** in `results/tables/p4_*`:
- `noise_action_matrix`
- `circuits`
- `costs`
- `validation` (JSON)
- `exact_diagnostics`
- `calibration_estimates`
- `replicates`: the per-context counterfactual outcomes for Phase 5
- `summary` (Table A)
- `deltas_vs_none` (Table B)
- `resource_matched` (Table C)
- `best_action` (Table D)
- `calibration_bins`, `score_histogram`
- `metadata` (JSON), including G2 and the hypothesis outcomes

**Figures** A–E:
- **A:** ΔAUPRC by condition;
- **B:** Brier and ECE before and after;
- **C:** performance against cost (Pareto view);
- **D:** benefit at 1,024 vs 4,096 shots;
- **E:** representative calibration and score distributions.

The runtime benchmark goes to raw `runtime.json` and is copied into the docs.

## 18. Not done in Phase 4

- no Q-TRACE training;
- no utility definition;
- no model pool (O15: PI, temporary);
- no counterfactual dataset scaling;
- no hardware calibration fetch (O20);
- no P3A-original;
- no PEC.

---

## Execution record (appended after execution; sections 1–18 unchanged)

**Registration** was committed and pushed at `9d377d0` before any mitigation was run on `vqc_val`.

**Executed exactly as registered:** the 8 conditions, actions A0–A3, the RM3 comparator, factors (1, 3, 5), the linear primary extrapolator, the calibration procedure, both shot arms, 20 replicates, the seeds, the metrics, the two-stage bootstrap, the minimum effects, H4.1–H4.5 and the G2 rule. Nothing was added, removed or re-selected; noise was not increased.

**Run order and outcome:**
- Every registered unit test and run-time check passed, as did every exact negative control (NC1–NC4, ≤ 1.4e-15), E08 on folded circuits (comb-high, λ = 3 and 5) and the calibration-circuit χ² checks (p 0.031–0.977).
- The finite-shot clean flag did not fire, and no negative-control cell showed an RRB.
- The frozen artifact was byte-identical before and after.
- **G2 = CONDITIONAL PASS.**

**Implementation details not fixed by the text** (decided before any real result):
1. **Parallelism.** The 15 exact Aer runs (5 gate-noise signatures × 3 factors) and the 16 finite-shot contexts run in parallel processes (joblib). Each unit is deterministic; the outputs are byte-identical across reruns (slow test).
2. **Seeds not spelled out in §9 and §15:**
   - E08 on folded circuits: `shots` stream, key (`p4-e08`, profile, factor, `aer` or `multinomial`); the Aer seed is taken mod 2³².
   - Calibration checks: key (`p4-calcheck`, profile, circuit).
   - Replicate draws for the bootstrap: `make_rng(bootstrap, "bootstrap", "p4-replicate-draw").integers(0, 20, 1000)`.
3. **Projection.** The simplex projection is applied only to rows with a negative quasi-probability; valid rows are returned unchanged.
4. **Exact readout calibration.** In the exact diagnostics, A1 uses the per-qubit marginals of the *exact* calibration-circuit distributions. These include the `x`-gate noise of |1111⟩ preparation: under dep-high, the estimated p̂10 = 0.0015 is entirely state-preparation error.
5. **Table D Brier tolerance.** "Within 10% of the best value" is implemented as ≤ 1.1 × the best mean.
6. **Output layout.** The `replicates` and `deltas_vs_none` tables (§17) are written as one file per shot arm (`*_s1024.csv`, `*_s4096.csv`). The repository's hygiene test caps committed aggregate tables at 2,000 rows as a guard against transaction-level dumps, and that guard was kept. The content is unchanged.
7. **Development fix before any real run.** One synthetic unit test wrongly expected readout mitigation to lower the Brier score of arbitrary synthetic scores. Mitigation restores the clean scores, which need not be better calibrated. It was replaced by a recovery-to-clean test.

**Disclosures from the results** (no rule changed):
- **Knife-edge threshold row.** The max-F1 τ equals one transaction's clean score. In the *exact* diagnostics, floating-point arithmetic of order 1e-16 in ZNE/A3 moves that single row across τ under clean and pure readout. The exact F1@τ is then 0.593 instead of 0.606, while the scores agree with clean to 1.4e-15. Finite-shot scores never sit exactly on τ, so G2 is unaffected.
- **H4.5 operationalization.** H4.5 was registered as "an A2/A3 qualifying cell without any RRB against RM3, or with harm". Its outcome is *not supported*: RM3 cannot remove calibration bias, so every qualifying A2/A3 cell beats it on Brier. The registered comparator does not express "a cheaper mitigation achieves the same benefit". Descriptively, Table D shows exactly that: A1 is chosen over A3 under pure readout, A2 over A3 under pure gate noise, and A1 for F1 under comb-medium. This is reported as a limitation of the registered test, not re-tested.

**Results:** `docs/EXPERIMENT_PROTOCOL.md` §3.10 and `results/tables/p4_*`.
