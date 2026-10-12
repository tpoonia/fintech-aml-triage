# Q-TRACE — Final capstone defense: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | December 8, 2026 (meeting 7 of 7): Final capstone defense |
| **Deck** | `Q-TRACE_2026-12-08_Final-Defense.pptx` (18 slides + 6 backup) |
| **Speakers** | Mayank: slides 1–5, 10–11, 17–18 · Tushar: slides 6–9, 12–16 (proposed for roughly equal time; team to confirm) |
| **Length** | ≈ 13:15 of speech (≈ 1856 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 6:09, Tushar ≈ 7:07 |
| **Status** | Ready for review. Complete study (completed Oct 6–8, 2026). Confirm the allowed length with the instructor: the research plan records a 3–5-slide limit for the biweekly meetings. |

## Slide 1: When is quantum error mitigation worth paying for?

**Mayank** · 0:00–0:28

> Good afternoon. We are Mayank and Tushar, and this is our capstone defense.
>
> Our research problem: a noisy quantum classifier can spend extra quantum resources on error mitigation. When is that worth paying for, and does deciding it require a learned controller? Our answer, from a pre-registered study confirmed on a sealed held-out test, is that in the studied setting a simple probe rule was enough.

## Slide 2: A noisy quantum classifier faces a spending decision

**Mayank** · 0:28–1:11

> Mitigation options differ in cost by an order of magnitude. Readout mitigation needs about two calibration circuits per batch. Zero-noise extrapolation needs three times the shots and nine times the two-qubit-gate exposure. Buying extra shots only reduces variance, not bias.
>
> In fraud scoring this matters, because alerts fire at a fixed threshold: a model whose probabilities are biased raises the wrong alerts even if it ranks transactions well. So for every execution context there is a real choice: nothing, readout mitigation, ZNE, both, or more shots. Paying for the wrong one either wastes quantum resources or leaves the alerts unreliable.

## Slide 3: What the literature offers

**Mayank** · 1:11–1:57

> Four strands of work frame our study.
>
> The foundations of mitigation are established: zero-noise extrapolation, readout inversion, and probabilistic error cancellation, which removes bias at an exponential sampling cost.
>
> Whether mitigation pays is less settled. A resource-normalized evaluation found it beneficial on average but strongly platform-dependent, and at a matched shot budget ZNE can be worse than the raw estimate.
>
> Adaptive selection already exists: bandit and orchestration methods choose mitigation per context.
>
> And for fraud, quantum classifiers have been tested on the same dataset, with tuned classical baselines ahead; other studies report quantum or hybrid models matching classical ones on particular metrics. So the comparison results are mixed.

## Slide 4: Research gap

**Mayank** · 1:57–2:36

> This table compares the closest selectors with our work. The learned selectors condition on information that is label-dependent or unavailable at deployment, such as ideal-state fidelity, simulator noise parameters, loss or reward, and they report gains mainly over static choices.
>
> To our knowledge, none puts extra shots and combined mitigation in one action space, restricts itself to label-free probes, and tests learning against a simple rule on held-out models under pre-registration. That is our gap. We do not claim to be the first to adapt mitigation; we claim a stricter comparison.

## Slide 5: Original hypothesis and how we tested it

**Mayank** · 2:36–3:22

> Our original hypothesis was that a learned controller, Q-TRACE, using only label-free probes, would beat fixed policies and a fairly tuned threshold rule on the reliability-cost trade-off. From the start we committed to report it as a result if a simple threshold rule matched it.
>
> We tested this in three stages. Two gates asked whether any material structure was left for learning; a controller would be trained only if one passed. Then one sealed test checked four hypotheses: the rule is near-Oracle, learning adds no meaningful value, the rule beats fixed policies, and it transfers to categorical noise. Tushar will now walk through the model and data.

## Slide 6: QML fraud-classification architecture

**Tushar** · 3:22–4:08

> Our reference classifier uses four features encoded as angles on four qubits, a ZZ feature map, a two-layer RealAmplitudes ansatz with 12 trainable parameters, and a parity readout that maps to a fraud probability. It has 18 two-qubit gates after transpilation.
>
> A pre-registered encoding repair raised its validation AUPRC from 0.104 to 0.507. Classical models on the same inputs reach 0.59 to 0.62, so we make no quantum-advantage claim: the classifier is the noisy workload whose mitigation decisions we study. Its output is an expectation value, the very quantity noise distorts and mitigation repairs.

## Slide 7: Dataset and leakage-safe preprocessing

**Tushar** · 4:08–4:50

> We use the public European credit-card fraud dataset: 284,807 transactions. After removing exact duplicates, 283,726 rows remain, with 473 frauds, or 0.17 percent.
>
> Rows that differ only in their timestamp are kept together, and a group-aware split creates five disjoint partitions. Preprocessing is fitted on the training partition only. The controller test partition was sealed until the final evaluation. True noise parameters, labels and identifiers never enter a policy, as enforced by a feature registry and tests. The probes are deployable measurements that estimate the noise by design.

## Slide 8: Noise models

**Tushar** · 4:50–5:42

> We simulate noise exactly with density matrices: depolarizing errors after gates, thermal relaxation during gates, and readout confusion. Each has low, medium and high anchors; asymmetric readout is a synthetic stress test, not device data.
>
> We used two environments. Phase 5B used eight near-categorical conditions. Phase 5C varied all sources continuously and jointly: 17 gate settings, one of them gate-free, times four readout settings, giving 68 noise points, shown on the right. The first finding, on the right: across the twelve anchor conditions, noise changed AUPRC by at most 0.003 but raised the Brier score up to thirteen-fold. Noise pulls scores toward one half, so calibration and threshold alerts suffer, while the top-ranked frauds stay on top.

## Slide 9: Error-mitigation methods

**Tushar** · 5:42–6:28

> We compare five actions: none, readout mitigation, ZNE by global folding at noise scales one, three and five with linear extrapolation, both combined, and three times the shots as the resource-matched baseline.
>
> Mitigation restored calibration: under combined high noise, the Brier score fell from 0.122 to 0.054 with combined mitigation, while three times the shots left it at 0.121. No action improved AUPRC beyond its shot-matched comparator, and the best action depended on the noise type: readout mitigation for readout noise, ZNE for gate noise, both for combined noise. Mayank will explain how we tested the decision.

## Slide 10: Experimental design and integrity

**Mayank** · 6:28–7:12

> From Phase 3A-R on, every phase was pre-registered and committed before its own outcomes existed; for Phases 5B, 5C and the final test the code was pushed together with the registration. Gates decided whether to continue, and negative outcomes count as results.
>
> The controller test outcomes were written to a sealed store. A guard allowed exactly one unlock, after the protocol and frozen comparators were pushed, and logged every read. Learned comparators were frozen by fingerprints of their decisions. Sixteen slow tests re-run Phases 1 to 5C and the final test. Every reported run records its commit, configuration hash, package versions and seeds.

## Slide 11: Evaluation metrics

**Mayank** · 7:12–8:03

> Because noise acts on calibration, the primary endpoint is the Brier score. The Oracle picks the cheapest action within ten percent of the best Brier score. A policy fails when it disagrees with the Oracle; the failure is material when its Brier score is more than twenty percent above the best, or it spends at least one extra shot-set per inference.
>
> Costs are counted in shots, including the probes for probing policies. Models nested in structures are the independent units, so intervals come from a two-stage cluster bootstrap, resampling structures and then models. One subtlety: Brier regret can be slightly negative, because the Oracle may trade some reliability for a lower cost. Tushar will now present the results.

## Slide 12: The 64-model benchmark

**Tushar** · 8:03–8:50

> To make models, not transactions, the unit of analysis, we trained 64 classifiers: 16 structures times four seeds, varying features, encoding, ansatz and readout. All qualified, with a median AUPRC of 0.235. Structures were split eight, four and four, and the four test structures were sealed.
>
> Every model was run under every action, noise context, budget and replicate: about 1.4 million paired outcomes. A policy sees only static descriptors and two probes: the readout calibration circuits, and a gate probe of 32 fixed inputs at fold factors one and three. Together they cost 66 circuits per batch, charged to every probing policy.

## Slide 13: Policy comparison: the gates failed, a simple rule emerged

**Tushar** · 8:50–9:38

> Under categorical noise, the best action was a lookup on the noise type, and a four-cell probe rule was wrong in only 0.33 percent of validation cases. Under continuous joint noise, where 16 of 17 gate settings carry gate noise by design, combined mitigation or ZNE was almost always best, and the two-threshold rule on the left made material errors in only 2.0 percent of validation decisions.
>
> Both were below the five-percent gates. The remaining structure was detectable, mostly from mean-Z readouts, but not material, so, as registered, no learned controller was trained. Instead we froze four learned comparators with fixed settings for the sealed test.

## Slide 14: Final held-out results

**Tushar** · 9:38–10:36

> On the sealed test, all four hypotheses were supported. Under continuous joint noise the rule made material errors in 2.0 percent of decisions, with an interval of 1.4 to 2.6 percent, and its Brier score was within 0.03 percent of the Oracle's. Under categorical noise: 8.8 percent, inside the ten-percent bound.
>
> The best learned comparator, gradient boosting, tied the rule on material errors at 2.1 percent. To be precise: it disagreed with the Oracle less often, 6.5 against 21.9 percent, but most of the rule's extra choices came from the unseen mean-Z structure, cost only two calibration circuits and were not material. The learned models were also unstable: gradient boosting made 10.7 percent material errors on validation.

## Slide 15: Cost–reliability findings

**Tushar** · 10:36–11:23

> Against cost, the rule sits next to the Oracle: 0.6 percent more shots, and 3.4 percent fewer than always using combined mitigation, with about a third of its material errors. Never mitigating uses about a third of the shots, but makes material errors 96 percent of the time.
>
> One disclosure matters here: always-combined's 5.9 percent material errors are exactly the one gate-free setting out of 17 in our design. So this saving, and the case for probing, depend on how often batches are gate-free. Probing pays for itself only above about 645 to 685 transactions per batch, a validation estimate.

## Slide 16: Limitations and threats to validity

**Tushar** · 11:23–12:04

> Our evidence is simulation-only, at four qubits, on one dataset, with two mitigation techniques. The held-out test has only four structures, so its intervals are probably too narrow, and H2 is a non-superiority result on material errors, not proof that learning cannot help. On raw agreement with the Oracle, learned models did better. The gate probe barely sees thermal noise, and gate noise was present in 16 of 17 settings by design. Per-model alert thresholds were tuned on clean validation data, which is optimistic. We claim no quantum advantage and no general applicability.

## Slide 17: Research contribution

**Mayank** · 12:04–12:42

> Our contribution has three parts. A characterization: noise damaged calibration, not discrimination, and mitigation repaired calibration where extra shots could not. A leakage-safe counterfactual benchmark across 64 independently trained models. And a pre-registered, held-out test of learned selection against simple rules, which found that a two-threshold probe rule performed competitively.
>
> Every result is reproducible from the repository, and the manuscript and report are complete drafts for review; nothing has been submitted. The broader lesson is methodological: adaptive mitigation should be evaluated against simple probe rules and a cost-aware Oracle.

## Slide 18: Conclusions and future work

**Mayank** · 12:42–13:15

> So, our answer. Spend on mitigation when the probes detect noise that biases calibration, choose the technique by noise type with a simple rule, and in this setting do not learn that decision.
>
> Next steps: validate on hardware, where readout asymmetry, drift and crosstalk are real; add richer mitigation such as probabilistic error cancellation and a thermal-sensitive probe; and test larger circuits, where noise may also damage discrimination.
>
> Thank you. We are happy to take your questions.

## Slide 19: B1 · Per-structure held-out results

**either** · backup slide, for questions only

> If asked why the rule's raw disagreement is higher on the test: it comes from the unseen mean-Z structure, where the rule adds readout mitigation that mean-Z readouts barely need. That costs two calibration circuits per batch and is not material (1.4 percent). R_obs, which conditions on the readout type, absorbs it; learned comparators reached 5 to 30 percent material errors on that structure.

## Slide 20: B2 · Where ZNE versus combined mitigation wins

**either** · backup slide, for questions only

> If asked where ZNE alone beats combined mitigation: at low readout severity under gate noise, readout error below about 0.003. Readout mitigation or no mitigation wins only on the gate-free setting.

## Slide 21: B3 · Probe ablation and probing break-even

**either** · backup slide, for questions only

> If asked which probe matters: the gate probe alone keeps material failure at 1.8 percent under continuous noise and 9.4 percent under categorical noise, though raw disagreement rises from 10 to 25 percent. A readout-only rule reaches 6.2 and 50 percent. Probing pays for itself relative to always-combined only above about 645 to 685 transactions per batch, or about 80 under categorical noise, and that break-even depends on the gate-free share.

## Slide 22: B4 · Baselines and the encoding repair

**either** · backup slide, for questions only

> If asked about classical baselines and the first quantum model: random forest on all thirty features reaches 0.805; on the VQC's four inputs classical models reach 0.59 to 0.62, and only the logistic-regression gap has an interval excluding zero. The first encoding saturated and aliased, leaving 91 distinct fraud inputs; the pre-registered repair keeps 212 and raises AUPRC from 0.104 to 0.507.

## Slide 23: B5 · Statistical details

**either** · backup slide, for questions only

> If asked about the statistics: these are the paired differences behind slides 14 and 15. On material errors no learned comparator is meaningfully better. On raw disagreement, gradient boosting, the depth-3 tree, the benefit model and R_obs are significantly closer to the Oracle. Learned comparators shifted between validation and test, while the rule did not. Only four structures were held out, so a cluster bootstrap over four clusters has few distinct resamples and its intervals are likely too narrow.

## Slide 24: B6 · References

**either** · backup slide, for questions only

> Full references for the citations on the slides. The complete, verified bibliography is in the manuscript.

## Delivery notes

- Hand-offs: before slide 6 (to Tushar), before slide 10 (to Mayank), before slide 12 (to Tushar), before slide 17 (to Mayank).
- Keep the registered endpoint (material errors) and the raw-disagreement result together; do not let a question surface the second.
- Use 'in the studied setting', 'in simulation' and 'to our knowledge'. Never claim quantum advantage, hardware validation or general applicability.
- Backup slides B1–B6 are for questions only; see Technical_QA_Guide.md.
