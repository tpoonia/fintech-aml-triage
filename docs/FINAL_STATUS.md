# Q-TRACE final project status

| | |
|---|---|
| **Date** | 2026-10-08 |
| **State** | **Research complete.** The sealed controller test was opened once under a pre-registered protocol. All deliverables are in the repository. |
| **Authoritative commit** | see `git log` on `origin/main`; the final-evaluation commit is `4865857` |

## Final research question

When should a noisy quantum-machine-learning fraud classifier spend additional quantum resources on error mitigation, and is learning that decision better than a simple observable rule?

## Final answer

**Use a simple probe rule. A learned controller (Q-TRACE) is unnecessary in this setting.**

The deployable rule, R_thr:
1. Run two cheap label-free probes per batch: the readout calibration, which readout mitigation reuses, and a fixed 32-binding gate probe.
2. If the gate probe detects gate noise, use ZNE.
3. Add readout mitigation to ZNE when the readout probe exceeds about 0.4% error.
4. Without gate noise, use readout mitigation alone (none at 256 shots).
5. Never buy extra shots to fix calibration.
6. For batches under about 645–685 transactions (budget-dependent; ≈ 80 under categorical noise), skip the probes and always use combined mitigation. This break-even scales with the share of gate-free batches (1 of 17 gate settings in our design).

The thresholds are fitted to these simulated 4-qubit circuits and probes and would need refitting for another device or circuit family.

## Final contribution

1. **Mitigation characterization.** Noise damages calibration and fixed-threshold decisions, not discrimination (AUPRC/AUROC) or the top-ranked frauds. Mitigation repairs calibration but never AUPRC beyond a shot-matched baseline. Extra shots are no substitute.
2. **A leakage-safe counterfactual benchmark:**
   - 64 independently trained 4-qubit VQCs;
   - categorical and continuous joint noise;
   - five actions, including extra shots;
   - label-free probe context: true noise parameters are never policy inputs (a feature-registry guard with tests), and the probes are deployable measurements that estimate the noise by design;
   - structure-level held-out models.
3. **A pre-registered, three-stage test of learned selective mitigation**, ending in a one-time sealed held-out evaluation. **The answer is negative:** a two-threshold rule is near-Oracle, and fixed learned comparators did not reduce material failure.

## Hypotheses

| Hypothesis | Outcome |
|---|---|
| H1 (Phase 3B): noise degrades VQC discrimination | **Not supported** at the studied severities. G1 conditional: ranking reordering in the legitimate bulk, calibration and threshold distortion; no discrimination degradation. |
| H4.1 / H4.2: readout mitigation repairs calibration; symmetric readout is rank-neutral | **Supported** |
| H4.3: mitigation improves AUPRC beyond resource-matched shots | **Not supported** (G2 conditional) |
| H4.4: the best action depends on noise context | **Supported** |
| Learned-controller hypothesis, categorical noise (G3B) | **Not supported** (gate failed): a fixed probe rule suffices |
| Learned-controller hypothesis, continuous joint noise (G3C) | **Not supported** (gate failed): negligible material regret |
| Final H1: the simple rule is near-Oracle on held-out structures | **Supported** (5C test material failure 0.020) |
| Final H2: learning adds no meaningful value (non-superiority on material failure) | **Supported** (best learned paired difference, R_thr − L_gbt, −0.0005 [−0.027, 0.016]) |
| Final H3: the rule beats fixed policies | **Supported** (always-combined 0.059, exactly the 1/17 gate-free design share) |
| Final H4: the rule transfers to categorical noise | **Supported** (5B test 0.088 ≤ 0.10) |

## Final test results (one unlock, 2026-10-08T21:28:24Z)

| Policy | 5C test material failure | 5C test Brier regret | Shots vs Oracle | 5B test material failure |
|---|---|---|---|---|
| **R_thr (deployable)** | **0.020** | **−0.03%** | **+0.6%** | **0.088** |
| R_obs (+ readout observable) | 0.021 | +0.7% | +0.6% | 0.119 |
| L_gbt, gradient boosting (best learned on 5C test) | 0.021 | +0.3% | +0.9% | 0.363 |
| L_tree3, depth-3 tree (best learned on 5B test) | 0.026 | +0.7% | +0.8% | 0.118 |
| Always combined (A3) | 0.059 | −1.4% | +4.1% | 0.500 |
| Never mitigate (A0) | 0.960 | +93% | −65% | 0.813 |

**Definitions.**
- The Oracle picks the cheapest action whose Brier is within 10% (ε = 0.10) of the best. A *failure* is any disagreement with the Oracle; it is **material** when the chosen action's Brier exceeds (1 + 2ε)× the best, or it costs at least S more action shots per inference than the Oracle's action.
- Brier regret is measured against the Oracle's action, which may sit up to 10% above the best Brier, so a policy that overspends (e.g. always-A3) can have negative regret.
- Paired differences are R_thr − comparator; negative values favour R_thr.
- "Shots vs Oracle" includes probe shots. The cost regret (+0.02 S on validation) and the overspend test count action shots only.

**Statistical caveats.**
- The test CIs come from a cluster bootstrap over only 4 held-out structures and are likely too narrow; always-A3's is degenerate ([0.059, 0.059]).
- H2 is a non-superiority result on material failure. On raw failure (any disagreement with the Oracle), L_gbt, L_tree3 and R_obs were significantly better than R_thr on the 5C test (paired R_thr − comparator: L_gbt 0.154 [0.028, 0.391]; L_tree3 0.133 [0.003, 0.387]; R_obs 0.130 [0.001, 0.384]); R_thr's extra disagreements were not material.
- The learned comparators were much worse on validation than on test (material failure: L_gbt 0.107 → 0.021; L_tree3 0.175 → 0.026); R_thr scored 0.020 on both.
- On the 5B test, the 5B category rule R_cat (0.064) was significantly better than R_thr (0.088): paired R_thr − R_cat 0.024 [0.011, 0.037].

## Did the Q-TRACE learned controller survive?

**No.** It was not trained, as decided by two registered gates (G3B, G3C). On held-out models, the pre-specified learned comparators did not beat the simple rule on material failure.

## Resource savings of the deployable rule

| Comparison | Effect |
|---|---|
| vs always-combined mitigation (5C test) | 3.4% fewer shots per inference, and material failure 0.020 instead of 0.059. Always-A3's 0.059 is exactly the 1/17 share of contexts on the gate-free setting, so this margin and the saving scale with the share of gate-free batches; in our continuous joint-noise design, 16 of 17 gate settings carry gate noise |
| vs the Oracle | within 0.6% of its shots |
| vs never mitigating | ≈ 2.9× more shots, which buys calibrated decisions: Brier regret −0.03% instead of +93% |
| Probe overhead | 66·S shots per batch; worthwhile above ≈ 645–685 transactions per batch (budget-dependent; ≈ 80 under categorical noise). The 66·S include the 2 calibration circuits that always-A3 already pays, so the break-even is conservative |

## Limitations

- **Simulation only.** No hardware run; the asymmetric readout is synthetic.
- **Scale.** 4 qubits and one public fraud dataset (0.17% prevalence; inherited PCA).
- **Models.** VQCs remain weaker than classical models. **There is no quantum advantage.**
- **Methods.**
  - Mitigation is limited to readout inversion and linear ZNE.
  - The gate probe is insensitive to thermal noise.
  - Per-model thresholds are optimistic (tuned on `vqc_val`).
- **Statistical power.** The held-out test spans 4 structures. The ≈ 0.70 SD detectable effect assumed 16 independent models; at the structure level, power is low and the cluster-bootstrap intervals are likely too narrow.
- **Design dependence.** The advantage over always-combined mitigation and the probing break-even scale with the share of gate-free batches in the design.

Details: `FINAL_REPORT.md` §16.

## Publication readiness

| Item | State |
|---|---|
| Manuscript | complete draft (`MANUSCRIPT.md`) |
| Figures and tables | final (`results/`) |
| Pre-registrations and execution records | complete |
| Reproducibility guide | `REPRODUCIBILITY.md` |
| **Before submission** | 1. Team confirmation of the agent-checked references (`LITERATURE.md`, E61).<br>2. Choose a venue and adapt the format.<br>3. PI and co-author review of the claims and the novelty boundary (`LITERATURE.md` §F). |

## Optional future work

- **Hardware.** Same probes and actions on a real device (drift, crosstalk, real readout asymmetry). This is the main external-validity gap.
- **Richer mitigation.** PEC, CDR, dynamical decoupling and their costs. A thermal-sensitive gate probe.
- **Larger circuits and other datasets,** where noise may also damage discrimination.
- **Optional compute.** The Colab GPU benchmark (`REMOTE_COMPUTE.md`) can be run for completeness. The recommendation is to stay local.
