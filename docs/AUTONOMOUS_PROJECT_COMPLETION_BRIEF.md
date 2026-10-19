# Autonomous project-completion brief (PI directive)

| | |
|---|---|
| **Issued by** | Mayank Kumar Pokhriyal (PI), 2026-10-08, after Phase 5B (G3B = FAIL, `018734c`) |
| **Status** | Authoritative instruction for all remaining work. The condensed version (Appendix) is used as the session `/goal`; where the two differ, this full text governs. |
| **Recorded in** | `DECISIONS.md` (O29 → A16) |

The text below is the PI's brief, reproduced verbatim. Only markdown heading markers were added.

---

Complete the Q-TRACE capstone research project end-to-end from the current repository state, operating autonomously until the project is scientifically complete, reproducible, publication-ready, and presentation-ready.

You are the primary research-and-engineering agent for this repository.

Do not stop after each ordinary phase to ask for permission. Continue through research design, preregistration, implementation, experiments, analysis, robustness checks, documentation, paper preparation, and final presentation artifacts whenever the evidence supports the next step.

However, scientific integrity overrides completion speed. Never manufacture a positive Q-TRACE result, change hypotheses after observing results, leak test information, or continue a failed research direction merely because it matches the project title.

## CURRENT AUTHORITATIVE STATE

The repository through Phase 5B is authoritative.

Important completed commits include:

* Phase 5A frozen model pool: e4b3d81
* Phase 5B preregistration: 0572c4c
* Phase 5B completed dataset/results: 018734c

Phase 5B produced:

G3B = FAIL (fixed_rule_sufficient)

The registered Brier-based learned-controller hypothesis failed because a cheap label-free probe rule selected the preferred action in approximately 99.7% of validation contexts.

Do NOT ignore, weaken, reinterpret, or overwrite this result.

The sealed ctrl_test outcomes remain unspent and must remain sealed until a new confirmatory hypothesis/policy is fully frozen.

## SCIENTIFIC STATE

The project has established:

1. QML fraud classifiers can remain discriminative under the registered noise while becoming substantially miscalibrated.
2. Noise primarily damages calibration and fixed-threshold decisions rather than AUPRC.
3. Readout mitigation repairs readout-induced calibration bias.
4. ZNE repairs part of gate-noise-induced calibration bias.
5. Combined mitigation is useful under combined noise.
6. Additional shots improve variance/ranking but do not remove systematic calibration bias.
7. Mitigation does not improve AUPRC beyond resource-matched additional sampling in the registered study.
8. Mitigation benefit magnitude varies substantially across models.
9. Under the Phase 5B pure/mostly categorical noise contexts, cheap observable probes reveal noise type so accurately that a simple fixed policy is sufficient.
10. Therefore a learned Q-TRACE controller is NOT justified under the existing Phase 5B environment.

The next research question is NOT:

"How can we make Q-TRACE win?"

It is:

"Does a genuinely non-trivial selective mitigation problem emerge under realistic continuous mixed-noise and resource-cost conditions, or is a simple probe-based policy sufficient?"

## PRIMARY GOAL

Determine the strongest scientifically defensible final contribution of this project.

There are two legitimate final outcomes.

### OUTCOME A — LEARNED Q-TRACE IS JUSTIFIED

Only if newly preregistered experiments demonstrate residual decision complexity that cannot be adequately captured by a simple deployable fixed rule, train and evaluate Q-TRACE.

### OUTCOME B — SIMPLE POLICY IS SUFFICIENT

If simple probe-based policies continue to explain the decision boundary, do NOT force a learned controller.

Finish the project around the stronger negative result:

"Selective quantum mitigation can be reduced to a simple observable probe-based policy under the studied QML setting; learned control adds unnecessary complexity."

Either outcome is acceptable.

Scientific validity matters more than preserving the original hypothesis.

## NEXT STUDY: PHASE 5C

Design and preregister a new experiment testing whether the Phase 5B failure was caused by the categorical nature of its noise environments.

The motivation is already documented:

Phase 5B used conditions that were largely separable into:

* none;
* readout;
* gate;
* combined.

The probes therefore almost directly revealed the correct action category.

Real devices can exhibit simultaneous readout and gate errors at continuously varying magnitudes.

Phase 5C should test whether action choice becomes genuinely non-trivial when noise components vary continuously and jointly.

Do NOT use stronger noise merely to manufacture mitigation benefit.

## PHASE 5C DESIGN

Construct a preregistered continuous mixed-noise study.

Vary at least:

* readout error magnitude;
* gate/depolarizing error magnitude;
* thermal contribution where technically justified;
* shot budget.

Use continuous or sufficiently fine discrete ranges based on the already validated Phase 3B/4 ranges.

Stay within scientifically defensible ranges.

Include:

* near-clean regions;
* readout-dominated regions;
* gate-dominated regions;
* genuinely mixed regions;
* transition/boundary regions where multiple actions may have similar utility.

Do not select points after observing preferred actions.

Use a preregistered grid, stratified sampling scheme, Latin-hypercube design, or similarly defensible design.

Keep true simulator noise parameters OFFLINE-ONLY.

The policy sees only observable probes and legitimate static descriptors.

## MODEL POPULATION

Use the frozen Phase 5A model pool.

Do not retrain models merely to improve the hypothesis.

Preserve structure-level independence.

Do not use the sealed test outcomes.

## CONTROLLER SPLITS

Continue using the registered structural split unless a methodological reason requires a new split.

Any change must be preregistered before outcomes.

Maintain separation between:

* controller train;
* controller validation;
* sealed controller test.

## TEST LOCKBOX

Do NOT open ctrl_test.

Do not inspect aggregate test metrics.

Do not use test outcomes for:

* choosing utility;
* choosing probes;
* selecting models;
* selecting policy;
* setting thresholds;
* choosing hyperparameters;
* deciding whether Q-TRACE exists.

The test set may be opened exactly once after the complete final policy and evaluation protocol are frozen.

## OBSERVABLE FEATURES

Continue enforcing the feature registry.

Allowed information may include:

* circuit descriptors;
* ansatz/encoding/readout descriptors;
* shot budget;
* frozen historical clean-model descriptors;
* readout calibration probe;
* gate-noise probe;
* legitimate uncertainty estimates from those probes.

Prohibited information includes:

* true simulator noise parameters;
* true noise-family labels;
* current evaluation labels;
* post-action outcomes;
* Oracle choice;
* current Brier/AUPRC/F1;
* hidden model/structure lookup IDs;
* anything derived from sealed test outcomes.

## PROBE COST

Every probe has a cost.

Always evaluate:

total deployment cost =
probe cost + selected action cost.

A policy that saves mitigation executions but spends equivalent or greater resources probing is not an improvement.

## ACTION SPACE

Maintain the scientifically supported action set unless preregistered evidence warrants modification:

* A0 — None
* A1 — Readout mitigation
* A2 — ZNE
* A3 — Combined readout mitigation + ZNE
* A4 — Additional shots

Do not add complex mitigation techniques simply to make the decision problem harder.

## UTILITY / DECISION FORMULATION

Brier remains the primary reliability endpoint unless a new endpoint change is scientifically justified and preregistered before Phase 5C outcomes.

Do not optimize primarily for AUPRC because Phases 4–5B showed that mitigation does not materially improve it.

Prefer a constrained or Pareto formulation rather than inventing one favorable λ.

For example:

minimize quantum resource cost

subject to reliability degradation relative to the best available action being ≤ ε

or evaluate several preregistered λ values:

U(a) = reliability benefit(a) − λ × normalized quantum cost(a)

If λ values are used, freeze them before policy evaluation and report sensitivity across them.

Do not choose λ after seeing which value makes Q-TRACE win.

## BASELINES

Every learned policy must be compared against:

* Never mitigate / A0
* Always A1
* Always A2
* Always A3
* Always A4 where appropriate
* best single global action
* Phase 5B category rule
* improved hand-written probe rule using legitimate observable model descriptors
* simple decision tree
* simple logistic/multinomial model where appropriate
* Oracle upper bound

A learned Q-TRACE model is scientifically useful only if it adds value beyond simple baselines.

## PHASE 5C GATE

Before training a sophisticated controller, quantify residual decision complexity.

PASS to learned-controller training only if all of the following are supported:

1. Multiple actions are meaningfully preferred across contexts.
2. Preferred actions cannot be reproduced almost perfectly by a simple preregistered probe rule.
3. Residual action choice depends on interactions between observable model/noise/resource features.
4. The residual effect is larger than replicate noise.
5. A meaningful performance/cost gap exists between the simple rule and Oracle.
6. There is enough sample size and independent model support to train and evaluate a controller.

If the fixed rule remains sufficient, STOP attempting to justify learned Q-TRACE.

Proceed directly toward the negative-result final project.

## IF PHASE 5C SUPPORTS LEARNING: PHASE 6

Only then train Q-TRACE.

Start simple.

Candidate models:

1. multinomial/logistic baseline;
2. shallow decision tree;
3. random forest;
4. XGBoost or equivalent gradient-boosted trees;
5. small MLP only if justified.

Do not use a quantum controller.

Do not introduce an LLM/agentic controller.

Do not select complexity for marketing value.

Primary controller should be the simplest model that performs competitively.

Hyperparameter selection uses controller train/validation only.

Respect structure/model grouping.

Do not access sealed test.

## CONTROLLER TARGET

Prefer predicting action-specific benefit/cost or constrained action utility rather than blindly classifying Oracle action labels if the continuous targets are scientifically more stable.

Possible formulation:

For each action a:

predict expected reliability outcome and/or improvement

then select the lowest-cost action satisfying the reliability constraint.

Compare this against direct action classification.

Pre-register the final formulation before final evaluation.

## PHASE 7: POLICY EVALUATION

After model and policy are frozen, compare on validation:

* Never
* Always policies
* extra shots
* fixed rule
* simple ML baselines
* Q-TRACE
* Oracle

Evaluate:

* Brier
* ECE
* threshold metrics
* AUPRC/AUROC as secondary diagnostics
* shots
* circuit executions
* CX-shot exposure
* probe overhead
* total resource cost
* regret to Oracle
* action accuracy where meaningful
* Pareto efficiency.

The central question is:

Does learned control provide a practically meaningful reliability/cost improvement beyond a simple deployable rule?

If no, accept the negative result.

## FINAL TEST PROTOCOL

Before opening ctrl_test:

1. Freeze the final scientific hypothesis.
2. Freeze policy implementation.
3. Freeze model weights.
4. Freeze probe design.
5. Freeze utility/cost definition.
6. Freeze all thresholds.
7. Freeze statistical tests.
8. Freeze figures/tables to be generated.
9. Commit and push this final test protocol.
10. Verify clean tree.
11. Verify no test access has occurred.

Only then unlock the sealed test once.

Never retune after seeing test results.

If test results contradict validation, report that honestly.

## ROBUSTNESS / ABLATIONS

Perform only scientifically useful robustness studies.

Potential analyses include:

* unseen model structures;
* model-family ablation;
* feature-group ablation;
* probe ablation;
* readout-probe-only vs gate-probe-only;
* probe-cost sensitivity;
* shot-budget sensitivity;
* noise-magnitude generalization;
* continuous interpolation/extrapolation within registered ranges;
* cost-weight sensitivity;
* model complexity comparison;
* finite-shot uncertainty.

Avoid endless experiments.

Stop when the primary conclusion is stable and adequately supported.

## REAL-HARDWARE CLAIMS

Do not claim real-hardware validation unless actual hardware experiments are performed.

Synthetic asymmetric readout remains synthetic.

If hardware access is unavailable or unnecessary, clearly state that simulation-to-hardware generalization is future work.

Do not block project completion solely because hardware is unavailable.

## STATISTICAL INTEGRITY

Use:

* paired comparisons where appropriate;
* hierarchical/group-aware analysis;
* confidence intervals;
* multiple-comparison correction where applicable;
* model/structure as the independent unit when appropriate.

Do not treat transactions, stochastic replicates, or action rows as independent model-level observations when they are not.

Report effect sizes, not only p-values.

## REPRODUCIBILITY

Maintain the existing project standard.

Every major experiment must have:

* preregistration;
* machine-readable config;
* deterministic seeds;
* hashes;
* frozen artifacts;
* runtime record;
* tests;
* lint;
* fresh-clone verification where practical.

Never commit raw transaction-level data.

Keep lockbox data gitignored.

Use caffeinate for long local runs where appropriate.

Use parallel workers safely with deterministic merging.

## GIT

Continue using incremental commits.

For each new scientific experiment:

1. preregistration commit and push;
2. implementation if not already included;
3. clean-tree reported run;
4. results/documentation commit and push.

Never force-push.

Never rewrite historical scientific commits.

Never silently modify earlier result artifacts.

## AUTONOMOUS EXECUTION

Continue automatically through ordinary successful steps.

Do not ask the user for routine engineering decisions that can be resolved from:

* prior decisions;
* scientific best practice;
* existing repository conventions;
* preregistered protocols.

When uncertain, choose the more conservative scientific option and document the decision.

You MAY stop and request user input only for a genuinely blocking external dependency such as:

* credentials/access that cannot be obtained locally;
* destructive operation requiring explicit approval;
* paid resource purchase;
* irreconcilable scientific choice with no defensible default.

A negative experimental result is NOT a reason to stop.

Instead follow the decision tree defined here.

## 48-HOUR SPRINT PRIORITY

Prioritize the scientific critical path.

Do not spend substantial time polishing presentation aesthetics before the final conclusion is known.

Priority order:

1. Phase 5C preregistration.
2. Phase 5C counterfactual generation.
3. residual-complexity gate.
4. controller training only if justified.
5. policy comparison.
6. frozen final test.
7. robustness/ablations.
8. final paper/report.
9. final presentation.

## FINAL PROJECT DELIVERABLES

Do not consider the project complete until the repository contains a coherent final set of artifacts.

At minimum produce:

### A. FINAL RESEARCH REPORT

A complete report covering:

* motivation;
* research question;
* related work;
* dataset;
* leakage-safe design;
* classical baselines;
* VQC development;
* encoding failure and repair;
* noise characterization;
* mitigation characterization;
* model pool;
* Phase 5B negative result;
* Phase 5C follow-up;
* final policy/controller;
* final held-out evaluation;
* ablations;
* limitations;
* conclusions;
* future work.

### B. PAPER-STYLE MANUSCRIPT

Create a publication-style manuscript suitable for later adaptation to an appropriate venue.

Include:

* abstract;
* introduction;
* related work;
* methods;
* experimental design;
* results;
* discussion;
* limitations;
* conclusion;
* references.

Do not claim novelty stronger than the evidence supports.

Do not claim "first" without verified literature evidence.

### C. FINAL FIGURES

Create publication-quality versions of the important plots.

Prefer a small number of information-dense figures over dozens of weak ones.

### D. FINAL TABLES

Include the principal quantitative comparisons needed to support the conclusion.

### E. REPRODUCIBILITY GUIDE

Document exactly how to reproduce:

* environment;
* datasets;
* models;
* experiments;
* final results.

### F. DECISION LOG

Update DECISIONS.md with all major scientific decisions and why they were made.

### G. LIMITATIONS

Explicitly document:

* simulation-only evidence if applicable;
* 4-qubit scale;
* fraud dataset limitations;
* model-pool limitations;
* synthetic noise assumptions;
* threshold optimism where relevant;
* absence of quantum advantage;
* any failed hypotheses.

### H. CAPSTONE PRESENTATION

Prepare the content/data needed for the final capstone presentation.

The presentation must tell the actual scientific story, including negative results.

Do not hide Phase 5B.

### I. NEXT WIP PRESENTATION

If the repository supports slide generation, prepare the next WIP presentation from measured results, emphasizing:

* Phase 4 findings;
* 64-model pool;
* Phase 5B;
* why the original learned-controller hypothesis failed;
* the Phase 5C research response.

### J. FINAL PROJECT STATUS

Create a concise final status document containing:

* final research question;
* final contribution;
* hypotheses supported/rejected;
* final test results;
* whether Q-TRACE learned controller survived;
* best deployable policy;
* resource savings;
* limitations;
* publication readiness;
* remaining optional future work.

## FINAL SUCCESS CONDITION

The project is complete when we can answer, with held-out evidence:

When should a noisy QML fraud model spend additional quantum resources on mitigation, and is learning that decision actually better than using a simple observable rule?

The answer is allowed to be:

"Use Q-TRACE."

or:

"Use the simple rule; Q-TRACE is unnecessary."

Both are successful research outcomes if supported rigorously.

When the final project is scientifically complete:

1. run the full relevant test suite;
2. run lint;
3. perform fresh-clone verification;
4. verify frozen artifact hashes;
5. verify repository hygiene;
6. commit all final documentation/results;
7. push to origin/main;
8. confirm HEAD equals origin/main;
9. produce one final completion report summarizing the entire project.

Do not continue generating new experiments after the final conclusion is adequately supported.

Stop only when the project is complete according to these criteria.

---

## Appendix: condensed `/goal` text (3,419 characters)

> Complete the Q-TRACE capstone end-to-end from the current repo (authoritative through Phase 5B, 018734c; G3B = FAIL, fixed_rule_sufficient: never weaken or overwrite it). Work autonomously through preregistration, experiments, analysis, docs, paper and presentation; stop only for blocking external needs (credentials, destructive ops, paid resources, irreconcilable scientific choices). Integrity over speed: no post-hoc hypothesis changes, no manufactured Q-TRACE wins, no test leakage.
>
> Path: (1) Preregister Phase 5C: continuous mixed noise on the frozen 64-model pool and existing structural split. Vary readout, gate/depolarizing and thermal (where justified) magnitudes within Phase 3B/4-validated ranges, plus shot budget, via a preregistered grid/LHS covering near-clean, readout-dominated, gate-dominated, mixed and boundary regions; no stronger noise to create benefit. Actions A0-A4; Brier primary; constrained/Pareto utility or a frozen lambda set with sensitivity; total cost = probe + action. Observables only (registry enforced). (2) Clean-tree reported generation. (3) Residual-complexity gate: PASS only if several actions are preferred, a preregistered simple probe rule cannot nearly reproduce them, the residual depends on feature interactions and exceeds replicate noise, the Oracle-rule gap is meaningful, and sample support suffices. (4) If PASS: Phase 6 controller, simplest competitive (multinomial, shallow tree, RF, GBT; MLP only if justified; no quantum/LLM controller); compare benefit/cost prediction with direct classification; group-aware tuning on train/val. If FAIL: no learned controller; finish around the negative result. (5) Validation comparison vs Never, Always A1-A4, best global action, 5B rule, improved hand rule, tree, logistic, Oracle: Brier, ECE, threshold metrics, AUPRC/AUROC secondary, shots, circuits, CX-shots, probe overhead, regret, Pareto. (6) Freeze, commit and push the final test protocol (hypothesis, policy, weights, probes, utility, thresholds, stats, outputs) on a clean tree with no prior test access; open ctrl_test once; never retune; report contradictions honestly. (7) Only useful ablations; stop when the conclusion is stable.
>
> Rules: ctrl_test sealed until (6); simulation only, no hardware claims; synthetic AR profiles stay labelled synthetic; model/structure is the independent unit; paired, hierarchical stats with CIs, effect sizes, multiplicity correction. Each experiment: prereg commit+push, config, seeds, hashes, frozen artifacts, runtime record, tests, lint, fresh-clone check. Never commit transaction data; keep the lockbox gitignored; caffeinate long runs; deterministic parallel merge. Incremental commits to origin/main; never force-push, rewrite history or silently change earlier results.
>
> Done when the repo has: final research report; paper-style manuscript (no unverified "first" claims); final figures and tables; reproducibility guide; updated DECISIONS.md; explicit limitations; capstone presentation content; WIP presentation (Phase 4, pool, 5B failure, 5C response); final status doc. Held-out evidence must answer: when should a noisy QML fraud model spend quantum resources on mitigation, and does learning that decision beat a simple observable rule? Either answer is success. Finish with full tests, lint, fresh clone, frozen-hash and hygiene checks, commit, push, HEAD == origin/main, and one final completion report.
