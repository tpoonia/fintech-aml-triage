# Pre-registration: Phase 7 validation comparison and the one-time final test

| | |
|---|---|
| **Status** | PRE-REGISTERED 2026-10-08. Committed and pushed, **with all evaluation code**, before any learned comparator is fitted and before the sealed test is read. |
| **Authority** | Completion brief (A16), negative-result path after G3B = FAIL and G3C = FAIL (O30). |
| **Machine-readable** | `configs/final_test/final_v1.yaml` |
| **Code** | `src/qtrace/controller/final_eval.py`, `src/qtrace/controller/learned.py`, `src/qtrace/controller/lockbox.py`, `scripts/phase7_validate.py`, `scripts/final_test.py` |

## 1. Final scientific hypothesis (frozen)

> Under the studied setting, selecting quantum error mitigation for noisy VQC fraud classifiers reduces to a **simple observable probe rule**. Learned control adds no practically meaningful reliability or resource improvement.

The confirmatory evidence is one evaluation on **sealed, held-out model structures** that no step has ever read:

| Environment | Role | Content |
|---|---|---|
| **Phase 5C test** | primary | continuous joint noise: 16 models × 68 points × 3 budgets × 20 replicates |
| **Phase 5B test** | secondary | near-categorical noise: 16 models × 8 conditions × 2 budgets × 20 replicates |

## 2. Frozen policies

| Policy | Definition | Source |
|---|---|---|
| **R_thr (deployable policy)** | Phase 5C threshold rule: per budget, readout-probe error ≥ t_r and/or gate contraction ≤ t_g → 4 cells → action | `p5c_metadata.json` `rules.R_thr` (fitted on 5C train) |
| R_cat | Phase 5B category thresholds (0.005 / 0.90), cell actions refitted on 5C train | `p5c_metadata.json` |
| R_obs | R_thr fitted per readout observable (parity / mean-Z) | `p5c_metadata.json` |
| Always A0 … A4 | universal policies | — |
| **L_logistic** | multinomial logistic regression (C = 1, standardized numeric features, one-hot categorical) predicting p\* | `final_eval.LEARNED_SPECS` |
| **L_tree3** | decision tree, depth 3, min leaf 50, predicting p\* | 〃 |
| **L_gbt** | histogram gradient boosting (depth 4, learning rate 0.1, 200 iterations) predicting p\* | 〃 |
| **L_gbt_benefit** | the same gradient boosting predicting each action's log Brier ratio to A0, then the registered constrained rule | 〃 |
| Oracle | upper bound (true context-mean outcomes) | — |

**Learned comparators:**
- **Fit:** on 5C **train** replicates only (130,560 rows), with **fixed** hyperparameters (no tuning).
- **Inputs:** the 27 registered controller inputs (16 static + 11 probe) via `mixed_controller_table`; the registry and prohibited-feature guard apply.
- **Seed:** the `policy` stream, key `p7-learned-comparators`.
- **Freeze (Phase 7):** each comparator's decisions on 5C val and 5B val are fingerprinted (SHA-256) and committed in `p7_frozen_policies.json`.
- **Reproduction check:** the final evaluation refits them deterministically and **refuses to continue** unless the 5C-val fingerprints reproduce exactly.

**Fixed as in Phases 5B/5C:**
- the probe design;
- the action implementations;
- the cost order A0 < A1 < A4 < A2 < A3;
- total deployment cost = probe cost (66·S shots per batch; probing policies only) + action cost.

## 3. Decision formulation and endpoints (frozen)

- **Oracle p\*:** the cheapest action within (1 + ε) of the minimum context-mean Brier, ε = 0.10. Failure ≡ choice ≠ p\*.
- **Material failure:** Brier > (1 + 2ε)·min, **or** ≥ 1·S extra shots per inference.

**Per decision** (each context replicate, using that replicate's probes):
- failure;
- material failure;
- reliability failure;
- Brier;
- relative Brier regret (Brier(a) − Brier(p\*)) / min;
- cost regret (shots(a) − shots(p\*)) / S;
- total shots per inference (including probes);
- CX-shots per inference;
- the chosen action's ECE, F1@τ and AUPRC (secondary).

## 4. Phase 7 (validation; reported, not confirmatory)

1. Fit the learned comparators on 5C train.
2. Evaluate **every** frozen policy on 5C val and on 5B val.
3. Commit the tables, the fingerprints and a validation preview of §6.

**Validation results do not change any policy, hypothesis or threshold.**

## 5. Statistics (frozen)

- **Unit:** models within structures. Two-stage cluster bootstrap (resample structures, then models within structure), 2,000 resamples, `bootstrap` stream key `final-bootstrap`.
- **Comparisons:** paired, per decision, R_thr minus comparator, with cluster-bootstrap 95% CIs.
- **Breakdowns:** per structure and per budget.
- **Power caveat (stated in advance):** the test has 4 structures, including one mean-Z, so structure-level uncertainty is large.

## 6. Hypotheses on the 5C test (frozen thresholds; `final_v1.yaml`)

| ID | Hypothesis | Supported if |
|---|---|---|
| **H1** | The simple rule is near-Oracle on unseen structures | R_thr material failure ≤ 0.05 **and** mean relative Brier regret ≤ 0.02 |
| **H2** | Learning adds no practically meaningful value | No learned comparator is *meaningfully better* than R_thr. Meaningfully better means either (a) its material failure is lower by ≥ 0.02 with the paired CI excluding 0, or (b) it saves ≥ 5% of total shots per inference while raising material failure by ≤ 0.005 |
| **H3** | The rule beats fixed policies | R_thr material failure < every universal policy's, **and** R_thr total shots ≤ always-A3's |
| **H4** (secondary, 5B test) | The rule transfers to categorical noise | R_thr material failure ≤ 0.10 |

## 7. Pre-written interpretation

| Outcome | Conclusion |
|---|---|
| H1 ∧ H2 ∧ H3 | **"Use the simple rule; a learned controller is unnecessary"**, confirmed on held-out structures |
| ¬H2 | A learned comparator outperformed the frozen rule on held-out models. The negative claim is **not** supported, and is reported as such. No controller is tuned after the fact. |
| ¬H1 | The simple rule is not near-Oracle on unseen structures (e.g. the mean-Z test structure). Reported, with the per-structure breakdown. |
| ¬H3 | A fixed universal policy is as good as the rule. Reported: "always combined mitigation" would be the deployable answer. |
| H4 | Reported as a secondary generalization result in either direction. |

Contradictions between validation and test are reported, not reconciled.

## 8. Outputs (frozen list)

**Tables** (`results/tables/`):
- Phase 7:
  - `p7_policies_{5c_val,5b_val}.csv`
  - `p7_paired_vs_rthr_{5c_val,5b_val}.csv`
  - `p7_by_structure_{5c_val,5b_val}.csv`
  - `p7_frozen_policies.json`
  - `p7_metadata.json`
- Final:
  - `final_policies_{5c_test,5b_test}.csv`
  - `final_paired_vs_rthr_{5c_test,5b_test}.csv`
  - `final_by_structure_{5c_test,5b_test}.csv`
  - `final_metadata.json` (hypotheses, unlock record, verification flags)

**Figures** (from committed tables only):
- `final_a_policies.png`: failure, material failure and shots per policy, both test environments;
- `final_b_structures.png`: R_thr and learned comparators per test structure.

## 9. Procedure and integrity checklist (brief "FINAL TEST PROTOCOL")

| # | Item | How |
|---|---|---|
| 1 | Final hypothesis frozen | §1 |
| 2 | Policy implementation frozen | §2; code in this commit |
| 3 | Model weights frozen | Fixed specs + deterministic refit + Phase 7 fingerprints, committed before unlock |
| 4 | Probe design frozen | Phase 5B probes, unchanged |
| 5 | Utility and cost frozen | §3 |
| 6 | Thresholds frozen | R_thr parameters (`p5c_metadata.json`); hypothesis thresholds (`final_v1.yaml`) |
| 7 | Statistical tests frozen | §5 |
| 8 | Figures and tables frozen | §8 |
| 9 | Commit and push this protocol; then commit and push the Phase 7 freeze | Two pushed commits before step 11 |
| 10 | Clean tree | `scripts/final_test.py` refuses unless the protocol, config and freeze record are committed and unchanged. The unlock guard refuses a dirty tree or a commit not on `origin/main`. |
| 11 | No prior test access | **No `UNLOCK_RECORD.json` and no `ACCESS_LOG.jsonl` exist.** Every analysis loader refuses the `test` split. The sealed files were written only by the 5B/5C build runs. Their committed content hashes (`c9ecc091…`, `91b0a5b9…`) are verified at read time. |
| 12 | One unlock | `qtrace.controller.lockbox.unlock` writes the single record. A second unlock is refused; later reproduction reads are logged. |

Never retune after the test.

---

## Execution record (appended; sections 1–9 unchanged)

**Registration:** pushed with code at `b7df65f`.

**Implementation correction** (`919ecdc`, before any output was written). The first Phase 7 run stopped with an error: rules read back from `p5c_metadata.json` carried string cell keys after the JSON round trip. The loader now converts them to integers. Rule values are unchanged, and a regression test proves identical decisions.

**Phase 7 (validation; not confirmatory):** committed with the frozen fingerprints (`p7_frozen_policies.json`).
- **Consistency check:** the frozen R_thr reproduces its registered Phase 5C validation numbers exactly.
- **Learned comparators on 5C val:** all have higher material failure than R_thr (2.0%): benefit GBT 3.7%, logistic 6.6%, GBT 10.7%, depth-3 tree 17.5%.
- **Validation preview:** H1–H4 all hold.

**Final evaluation** (single unlock 2026-10-08T21:28:24Z at commit `5e09c85`; two logged reads):
- **Integrity:** the sealed contents matched their committed hashes, and all four learned comparators reproduced their frozen fingerprints.
- **Results:** `results/tables/final_*`, `results/figures/final_*`.

**Hypotheses (5C test, primary):**

| Hypothesis | Result | Evidence |
|---|---|---|
| **H1** | **supported** | R_thr material failure 0.020 [0.015, 0.026]; relative Brier regret −0.03% [−1.7, +1.2] |
| **H2** | **supported** | No learned comparator meaningfully better. Paired material difference R_thr − comparator: L_gbt −0.0005 [−0.027, +0.016]; L_tree3 −0.006; L_gbt_benefit −0.006; L_logistic −0.074 |
| **H3** | **supported** | always-A3 material failure 0.059; R_thr uses 3.4% fewer shots |
| **H4** (secondary, 5B test) | **supported** | R_thr material failure 0.088 ≤ 0.10 (R_cat 0.064; learned comparators 0.12–0.44) |

**Disclosure.** R_thr's raw failure on the 5C test (0.219) is higher than on validation (0.096), with an unchanged material failure. The excess comes from the unseen mean-Z test structure (0.62 raw, **0.014 material**): R_thr adds readout mitigation where ZNE alone suffices, which costs only two calibration circuits. The pre-registered R_obs comparator absorbs it (0.11 raw).

**Verdict per §7:** **"Use the simple rule; a learned controller is unnecessary"**, confirmed on sealed held-out structures in both noise environments.
