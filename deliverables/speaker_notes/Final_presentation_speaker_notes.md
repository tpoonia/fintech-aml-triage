# Final capstone presentation: speaker notes

| | |
|---|---|
| **Deck** | `deliverables/presentations/Q-TRACE_Final_Capstone.pptx`: 16 core slides plus 2 backup slides. Shorter versions of these notes are embedded in the deck. |
| **Target** | About 14 minutes, leaving 1–2 minutes of buffer within a 15-minute slot |
| **Speakers** | Alternating by section. **Mayank:** 1–4, 9, 10, 13, 14, 16. **Tushar:** 5–8, 11, 12, 15. |
| **Rule** | Every number on the slides traces to `results/tables/` (see `deliverables/figures/FIGURES.md`). Do not improvise numbers. |
| **Q&A** | Anticipated professor questions with accurate answers: `Final_QA.md`. |

| # | Slide | Speaker | Time | Key points to say |
|---|---|---|---|---|
| 1 | Title | Mayank | 0:40 | The question, and a preview of the answer: a simple probe rule was enough, confirmed on a sealed held-out test. |
| 2 | Spending decision | Mayank | 1:00 | Readout mitigation is about 2 calibration circuits per batch. ZNE costs 3× shots and 9× two-qubit-gate exposure. Extra shots remove variance, not bias. Fraud alerts fire at a fixed threshold, so calibration matters. |
| 3 | Research question and hypotheses | Mayank | 0:45 | The original learned-controller hypothesis. The registered alternative: a simple rule suffices. Characterization hypotheses. Negative outcomes count as results. |
| 4 | Literature and novelty | Mayank | 1:00 | Adaptive mitigation selection exists: bandits and orchestration. The learned selectors use label-dependent or simulator-only context and report gains mainly over static choices (one also over grid-search ZNE). Rao et al. use label-free features but hand-designed fuzzy rules. Our addition, *to our knowledge*: extra shots and combined mitigation in one action space; label-free probe context; held-out, pre-registered tests against simple rules. We do not claim to be first to adapt mitigation. |
| 5 | Dataset and leakage-safe design | Tushar | 0:50 | 283,726 transactions after deduplication, 0.17% fraud. Five disjoint, group-aware partitions. The controller test was sealed. Offline-only quantities are enforced by a registry and tests. |
| 6 | QML methodology | Tushar | 1:00 | A 4-qubit ZZ map with RealAmplitudes or EfficientSU2. Encoding repair: AUPRC 0.104 → 0.507. Classical models reach 0.59–0.62 (clearly ahead for logistic regression), so there is **no quantum advantage**. 64 models; structures split 8/4/4. |
| 7 | Noise breaks calibration, not discrimination | Tushar | 1:00 | Aer density matrices. AUPRC moves ≤ 0.003 and the top-ranked frauds stay on top (scores do reorder slightly in the legitimate bulk); Brier rises up to 13×. 5B used 8 categorical conditions; 5C used 68 continuous points within validated ranges. Asymmetric readout is synthetic. |
| 8 | Mitigation methods | Tushar | 1:00 | The cost table. No AUPRC gain beyond the shot-matched baseline. Brier restored: 0.053 → 0.011, 0.055 → 0.038, 0.122 → 0.054. Three times the shots leaves Brier unchanged. |
| 9 | Design and integrity | Mayank | 1:00 | Pre-registered with code. The sealed test was opened once by a guard, with reads logged. Comparators were frozen by decision fingerprints. 16 slow tests re-run Phases 1–5C and the final test. |
| 10 | Controllers, baselines, gates | Mayank | 1:00 | The policy families. G3B: the rule is right 99.7% of the time. G3C: the best rule's material errors are 2.0% [1.6, 2.7]. Both found only a small, statistically detectable but non-material residual, so both failed and no Q-TRACE was trained. Extra shots were never best (0%). |
| 11 | Held-out statistics | Tushar | 1:00 | Define a material error. R_thr: material errors 2.0% [1.5, 2.6]; Brier regret −0.03% (negative is possible because the Oracle may be up to 10% worse in exchange for being cheaper). Categorical test: 8.8%, inside the pre-registered 10% bound. H1–H4 all supported. Two-stage cluster bootstrap over only 4 structures, so CIs are likely too narrow. |
| 12 | No learned comparator reduces material errors | Tushar | 0:55 | Best learned on the 5C test (gradient boosting): 2.1% vs 2.0%, paired difference (comparator − rule) +0.0005 [−0.016, +0.027]. Say it plainly: it disagrees with the Oracle less often (6.5% vs 21.9%), but the rule's extra disagreements are cheap, not material. Learned models were unstable from validation to test, made 12–44% material errors under categorical noise (where R_cat, 6.4%, beats R_thr, 8.8%), and 5–30% on the unseen mean-Z structure versus the rule's 1.4%. |
| 13 | Cost–reliability | Mayank | 0:50 | R_thr uses 0.6% more shots than the Oracle and 3.4% fewer than always-combined, with a third of its material errors. Disclose: always-combined's 5.9% is exactly the gate-free share of our design (1 of 17 gate settings), so this saving shrinks where gate noise is always present. Never mitigating costs 0.35× the shots but gives 96% material errors. |
| 14 | Ablations | Mayank | 0:55 | The gate probe alone reaches 1.8% material errors. Probing breaks even at about 645–685 transactions per batch (about 80 under categorical noise); this depends on the gate-free share. Budget affects the choice in < 3% of cases. Tolerance 0.05–0.20 gives 2.0–7.5%. Validation only. |
| 15 | Limitations | Tushar | 0:50 | Simulation only, 4 qubits, one dataset, two mitigation techniques. The gate probe is blind to thermal noise; 16 of 17 gate settings carry gate noise. Four held-out structures, so CIs are likely too narrow. Thresholds are optimistic. No advantage claim. |
| 16 | Conclusions and future | Mayank | 1:00 | The answer: in the studied setting, a simple probe rule performed competitively with learned controllers. Then next steps: hardware, PEC/CDR/DD with a thermal-sensitive probe, larger circuits. Thank the committee; invite questions. |
| B1 | Per-structure results | either | (Q&A) | Explains R_thr's 21.9% raw disagreement on the test: the unseen mean-Z structure. These are non-material overspends; R_obs absorbs them. |
| B2 | 5C preferred-action map | either | (Q&A) | Where ZNE beats combined mitigation in the continuous noise space: low readout severity under gate noise. |

**Total:** about 14 min 05 s.

## Transitions

- **2 → 3:** "So the decision is real. What exactly did we test?"
- **4 → 5:** "To test it fairly, we first needed leakage-safe data." Hand off to Tushar.
- **8 → 9:** "Before results: how we kept ourselves honest." Hand off to Mayank.
- **10 → 11:** "Then we opened the sealed test, once." Hand off to Tushar.
- **12 → 13:** "What does that mean in resources?" Hand off to Mayank.
- **14 → 15:** "Now the limits of what we can claim." Hand off to Tushar.
- **15 → 16:** "So, our answer." Hand off to Mayank.

## Phrases to use precisely

| Say | Avoid |
|---|---|
| "material errors" (Brier above twice the tolerance, or at least one extra shot-set per inference) | plain "errors" |
| "in the studied setting", "simulation evidence" | "universally", "in general" |
| "to our knowledge" about novelty | "first" |
| "the learned comparators did not beat the rule on material errors" | "learning cannot work", "learning adds nothing" |
| "noise did not degrade discrimination" | "noise did not change the ranking" |
| "in our joint-noise design" | "under realistic noise" |
| "no material residual" | "no learnable residual" |
