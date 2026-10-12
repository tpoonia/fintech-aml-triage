# Anticipated questions and accurate answers

For the October 13 progress talk and the final capstone presentation. Each answer gives the short spoken version first, then the supporting numbers. Every number comes from `results/tables/` or the decision log (`docs/DECISIONS.md`). If a question goes beyond what we measured, say so.

**Defaults when unsure:** "in the studied setting", "in simulation", "to our knowledge". Never claim quantum advantage, hardware validation or general applicability.

---

## A. Framing and novelty

**1. Why use a quantum classifier at all, if classical models are better?**
We are not proposing the VQC as a fraud model. It is a noisy workload whose mitigation decisions we can study end to end. On the same four inputs, classical models reach AUPRC 0.59–0.62 against the repaired VQC's 0.507. Only the logistic-regression gap has an interval excluding zero (+0.113 [0.021, 0.214]). We make no quantum-advantage claim.

**2. Isn't adaptive mitigation selection already published?**
Yes, and we say so. Bandit and orchestration selectors exist (GSC-QEMit, Rahman & Nguyen, Majid et al.), as do a fuzzy-rule selector (Rao et al.) and a decision-aware analysis (Scavino). The learned selectors use context that is label-dependent or unavailable at deployment (ideal-state fidelity, simulator noise parameters, loss, accuracy or reward). They report gains mainly over static choices; Rahman & Nguyen also compare against grid-search ZNE and other published methods. Our addition, to our knowledge, has three parts:
- extra shots and combined mitigation in one action space;
- a context restricted to label-free probes;
- a pre-registered, held-out comparison of learning against simple rules.

We do not claim to be first to adapt mitigation.

**3. Your original hypothesis failed. Is this still a contribution?**
Yes. We registered the alternative ("a simple rule suffices") before any outcome existed, and we report negative results as results. The finding is useful to practitioners and to the selector literature: evaluate selectors against simple probe rules and a cost-aware Oracle, on held-out models.

## B. Design choices

**4. Why simulation and not IBM hardware?**
The study needs exact counterfactuals: every action on the same model and noise context, with paired random draws, plus the true noise parameters to build Oracle labels offline. That produced about 1.4 million outcomes (102,400 in Phase 5B and 1,305,600 in Phase 5C). Hardware drift would confound the paired comparison, and the plan always reserved a real QPU for validation only (decision F17). Hardware validation is the main open external-validity gap.

**5. Why only readout mitigation and ZNE? Why not PEC, CDR or dynamical decoupling?**
- **PEC:** removes bias at a sampling cost that grows exponentially with circuit noise. It was scoped as exploratory from the start (decision F03).
- **CDR:** needs near-Clifford training circuits per workload.
- **Dynamical decoupling:** acts on idle-period and coherent errors, which our gate-level noise model does not represent.

All three could create a richer decision and are listed as future work. Our conclusion covers only the actions we studied.

**6. Why linear extrapolation instead of Richardson?**
- **Registered choice:** linear least squares over λ = 1, 3, 5 was registered in advance (decisions F07 and O09).
- **Variance:** in Phase 4, Richardson recovered more of the exact Brier gap (43–97% versus 13–70%), but at about 5.2× the shot variance, and it needed clipping more often (up to 4.6% of rows).
- **Diagnostic only:** we kept Richardson as a diagnostic.

**7. Why is the Brier score the primary endpoint, not AUPRC?**
Noise in our setting damaged calibration, not discrimination:
- AUPRC moved by at most 0.003, with every interval containing zero, and at least 46 of the 47 top-ranked frauds were preserved.
- The Brier score rose from 0.0093 to 0.121.
- Fraud alerts fire at a fixed threshold, so calibration drives decisions (precision fell from 0.53 to 0.03).

No mitigation action improved AUPRC over its resource-matched baseline, so an AUPRC endpoint would have no decision to make.

**8. Did noise really leave the ranking unchanged?**
Not exactly, so phrase it carefully. Noise reordered scores within the legitimate bulk (Kendall τ 0.96–0.99), but it did not degrade discrimination: AUPRC and AUROC were unchanged within their intervals, and the top-ranked frauds stayed on top. Say "not discrimination", not "not ranking".

**9. How is the Oracle defined? Why a 10% tolerance?**
The Oracle picks the cheapest action whose context-mean Brier score is within 10% of the best action's, using the cost order A0 < A1 < A4 < A2 < A3.
- **Why 10%:** the tolerance was registered before the outcomes.
- **Sensitivity:** across ε = 0.05 to 0.20, the rule's material failure stays between 2.0% and 7.5%.

**10. What is a "material" error, and why not just count disagreements with the Oracle?**
A material error is a choice whose Brier score exceeds the best by more than 2ε (20%), or that costs at least one extra shot-set (S shots) per inference.
- **Why not raw disagreement:** it counts near-ties and near-free overspends as failures. One example is choosing combined mitigation instead of ZNE, which costs only two calibration circuits per batch.
- **Registration:** material failure was the registered endpoint for the final test.

**11. How can the rule have negative Brier regret? Does it beat the Oracle?**
The Oracle is allowed to be up to 10% worse than the best action in exchange for being cheaper. A policy that sometimes overspends can therefore be slightly more reliable than the Oracle while costing more. Always-combined shows this most clearly: −1.4% regret at 4% more shots.

## C. Results and statistics

**12. What exactly did the sealed test show?**
The test set contained 16 models from 4 never-used structures and was opened once (2026-10-08T21:28:24Z). Results under continuous joint noise:
- **Rule R_thr:** material errors in 2.0% of decisions [1.5, 2.6]; Brier regret −0.03%; 0.6% more shots than the Oracle; 3.4% fewer than always-combined.
- **Categorical noise:** 8.8%, inside the pre-registered 10% bound.
- **Hypotheses:** H1–H4 were all supported.

**13. Your confidence intervals come from 4 test structures. Can you trust them?**
Only partly, and we say so in the paper. A percentile cluster bootstrap over 4 top-level clusters has only 35 distinct structure resamples, so the intervals are likely too narrow; always-combined's interval is degenerate. The pre-registered detectable effect of about 0.70 SD assumed 16 independent models, so power at the structure level is lower. The conclusion also rests on three other sources of evidence:
- the same result on 4 separate validation structures (material failure 2.0% on validation as well);
- the mechanism (the gate probe alone recovers the rule);
- the logic of the action space.

It does not rest on the test intervals alone.

**14. Didn't gradient boosting actually do better than your rule?**
On the registered endpoint, no:
- **Material errors:** 2.1% versus 2.0%, a paired difference of +0.0005 [−0.016, +0.027].
- **Raw disagreement:** yes. Gradient boosting disagreed with the Oracle in 6.5% of decisions against the rule's 21.9%, and that difference is significant. The depth-3 tree and R_obs were also closer to the Oracle.
- **Why the rule's extra disagreements are not material:** they come from one unseen mean-Z structure, where the rule adds readout mitigation that mean-Z readouts barely need. That costs two calibration circuits per batch.
- **Instability:** gradient boosting was unstable between validation and test (10.7% → 2.1% material). The rule was stable at 2.0% on both.

A different endpoint could favour the learned models; we disclose that.

**15. Couldn't a better-tuned learner win?**
Possibly on raw agreement, but there is little room on the registered endpoint: the rule's material failure is only 2.0%, which caps any learner's possible gain at 2 percentage points. The comparators used fixed hyperparameters, chosen in advance, to avoid a forking-paths search on the test set. We claim only that these pre-specified comparators did not beat the rule, not that learning can never help.

**16. Why didn't you train the Q-TRACE controller?**
The protocol said to train it only if a residual-complexity gate passed. Both gates failed:
- **G3B (categorical noise):** the category rule was wrong in only 0.33% of validation cases.
- **G3C (continuous noise):** the best rule's material failure was 2.0%, below the 5% threshold.

The residual structure was statistically detectable but small: mutual information 0.08 nats (p = 0.001) in 5B and 0.04 nats (p < 0.001) in 5C validation. Training a controller anyway would have been an unregistered analysis. We tested fixed learned comparators instead.

**17. Always-combined has 5.9% material errors and your rule 2.0%. Isn't that difference built into your design?**
Yes, largely. Always-combined's 5.9% is exactly the share of contexts on our single gate-free design setting (1 of 17 gate settings), where it pays 2S more than readout mitigation. Three results scale with the share of gate-free batches:
- H3's margin;
- the 3.4% shot saving;
- the probing break-even.

On a device where gate noise is always present, the rule's advantage over always-combined shrinks to the ZNE-versus-combined choice, which costs two calibration circuits per batch.

**18. Under categorical noise, the old category rule beat R_thr. Doesn't that undermine your result?**
It shows that the thresholds are environment-specific. R_thr was fitted on continuous noise and transferred to the categorical test within the pre-registered 10% bound (8.8%). The rule fitted for that environment did better (6.4%; paired difference 0.024 [0.011, 0.037]), and all learned comparators did worse (11.8–43.9%). The conclusion "a simple rule suffices" holds for both rules.

**19. Why does the shot budget barely matter, and why are extra shots never chosen?**
Mitigation removes a calibration bias, and extra shots only reduce variance. Three times the shots left the Brier score unchanged (for example, 0.121 versus 0.122 under combined-high noise). The budget changed the Oracle action in under 3% of cases. Extra shots were never the Oracle action at ε = 0.10, and in at most 0.03% of contexts at ε = 0.20.

**20. How expensive are the probes, and when are they worth it?**
The probes cost 66·S shots per batch: 2 readout-calibration circuits plus 32 gate-probe bindings at fold factors 1 and 3.
- **Continuous noise:** probing beats always-combined only above about 645–685 transactions per batch, depending on the budget.
- **Categorical noise:** the break-even is about 80 transactions.
- **Our panels:** 28,372–56,746 transactions.

The break-even is conservative, because always-combined already pays for the two calibration circuits, and it depends on the gate-free share (see question 17).

## D. Validity and integrity

**21. How do you know the policy never saw the true noise or the labels?**
A feature registry separates deployable inputs from offline-only quantities, and automated tests fail if an offline-only name enters a policy input table. The offline-only quantities are:
- true noise parameters and noise labels;
- design-point and model identifiers;
- labels and post-action outcomes.

The probes estimate the noise by design. For example, the readout probe tracks the true mean readout error with Spearman ρ ≈ 0.999. They are legitimate measurements a deployed system could make, not leaked parameters.

**22. How was the sealed test protected?**
The test outcomes were written to a version-control-ignored store; only row counts and content hashes were committed. A guard allowed exactly one unlock, after the final protocol, the code and the frozen comparators had been pushed. Every read is logged. The stored outcomes matched their hashes, and the refitted learned comparators reproduced their frozen decision fingerprints.

**23. What is synthetic in your noise model?**
- **Synthetic:** the asymmetric readout component (p10 > p01) is a stress-test assumption, not device calibration data.
- **Not modelled:** crosstalk, drift, leakage and coherent errors.
- **Severities:** these stay within the validated "high" anchors (p2 up to 0.02, T1 down to 50 µs, mean readout error up to 0.05).

Do not call the noise "realistic".

**24. What is the weakest part of the study?**
Be direct:
1. simulation only;
2. four held-out structures;
3. a gate probe that is nearly blind to thermal relaxation (Spearman −0.12);
4. a design in which 16 of 17 gate settings carry gate noise, which shapes the cost comparison with always-combined.

**25. What would change your conclusion?**
- hardware with genuinely gate-free periods or drifting noise;
- richer actions (PEC, CDR, DD) whose costs and benefits overlap more;
- larger circuits, where noise may also damage discrimination;
- an endpoint that weights fraud-operations costs.

Any of these could create a decision that a two-threshold rule cannot capture.

**26. Can someone reproduce this?**
Yes:
- every reported run records its commit, configuration hash, package versions, hardware and seeds;
- 16 slow tests re-run Phases 1–5C and the final evaluation and compare the outputs;
- the dataset is public (Kaggle `mlg-ulb/creditcardfraud`).

Transaction-level data and the sealed store are not redistributed.

**27. How did you use AI tools?**
An AI coding assistant (Claude Code) helped with engineering, analysis scripting and drafting, under our direction. We reviewed every scientific decision, pre-registration and conclusion. The literature identifiers were checked against publisher, arXiv and Crossref records, and we confirm the references ourselves before any submission.
