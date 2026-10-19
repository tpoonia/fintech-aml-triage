# October 13, 2026 progress presentation: 5-minute script

| | |
|---|---|
| **Deck** | `deliverables/presentations/Q-TRACE_Oct13_Progress.pptx` (8 slides; the same notes are embedded in the deck) |
| **Speakers** | Mayank Kumar Pokhriyal: slides 1–4 (≈ 2 min 05 s). Tushar Poonia: slides 5–8 (≈ 2 min 40 s). |
| **Total** | ≈ 4 min 45 s of speech at about 140 words per minute, leaving a short buffer inside 5 minutes |
| **Numbers** | Every number traces to `results/tables/` (see `deliverables/figures/FIGURES.md`) |

---

## Slide 1: Title (Mayank, 0:00–0:23)

> Good afternoon. We are Mayank and Tushar.
>
> Our capstone asks a practical question about near-term quantum machine learning. Error mitigation makes noisy quantum results more reliable, but it costs extra quantum resources. So when is it actually worth paying for? And can a learned controller make that decision better than a simple rule?

## Slide 2: Mitigation is expensive, so use it selectively (Mayank, 0:23–0:58)

> Mitigation is not free.
>
> - **Readout mitigation** is nearly free once calibrated: about two calibration circuits per batch.
> - **Zero-noise extrapolation, or ZNE,** needs three times the shots and nine times the two-qubit-gate exposure.
> - **Buying more shots** only reduces variance.
>
> Our original hypothesis was that a learned controller, which we called Q-TRACE, could pick the right action for each context from cheap, label-free probes. From the start, we also pre-registered the alternative: a simple rule might be just as good.

## Slide 3: Setup: 64 noisy quantum fraud classifiers (Mayank, 0:58–1:27)

> We use the public European credit-card fraud dataset: about 284,000 transactions with 0.17 percent fraud, in five leakage-safe partitions.
>
> We trained 64 independent four-qubit variational quantum classifiers. Then we simulated every model under every noise context, shot budget and action, about 1.4 million counterfactual outcomes in all.
>
> Crucially, the policy only sees cheap label-free probes. The true noise parameters, the labels and our test set stay offline.

## Slide 4: Noise breaks calibration, and mitigation repairs it (Mayank, 1:27–2:06)

> Our first finding reframed the project.
>
> - **Discrimination:** noise barely changes it. AUPRC moves by at most 0.003, and the top-ranked frauds stay on top.
> - **Calibration:** it collapses. The Brier score gets up to 13 times worse.
> - **Mitigation fixes exactly that.** Under combined noise, readout mitigation plus ZNE cuts the Brier score from 0.122 to 0.054. Spending the same budget on extra shots does nothing.
>
> The best action also depends on the type of noise, so it looked like a genuine selective decision problem.
>
> Tushar will take it from here.

## Slide 5: Two pre-registered gates: nothing material left to learn (Tushar, 2:06–2:47)

> We tested the controller hypothesis with pre-registered gates.
>
> **Categorical noise first.** The best action was simply a lookup on the noise type, and a four-cell probe rule was right 99.7 percent of the time. That gate failed.
>
> **Then continuous, joint noise.** Readout, gate and thermal noise now varied continuously together. That removed most of the choice. In our design, 16 of 17 gate settings carry gate noise, and ZNE or combined mitigation wins in 94 percent of contexts. A two-threshold rule makes material mistakes only 2 percent of the time.
>
> The second gate failed too. As registered, we did not train a controller.

## Slide 6: Sealed held-out test: the rule matches the Oracle (Tushar, 2:47–3:29)

> Finally, we froze everything and opened our sealed test set exactly once: 16 models from four structures that the policies had never seen.
>
> - **Reliability:** the simple probe rule made material errors in 2 percent of decisions, with a confidence interval of 1.5 to 2.6 percent.
> - **Brier score:** within 0.03 percent of the cost-aware Oracle.
> - **Cost:** only 0.6 percent more shots.
>
> The best learned comparator, gradient boosting, tied it at 2.1 percent on material errors. It disagreed with the Oracle less often, but the rule's extra disagreements were cheap ones. All four pre-registered hypotheses held.

## Slide 7: Why the simpler policy prevailed (Tushar, 3:29–4:09)

> Why did the simple rule win? Three reasons.
>
> 1. **Bias, not variance.** Mitigation removes a calibration bias, and extra shots cannot, so the budget rarely matters.
> 2. **One question decides.** In our joint-noise design, where 16 of 17 gate settings carry gate noise, the decision collapses to "is gate noise present?", and the gate probe alone answers it.
> 3. **Magnitude, not the winner.** Models differ in how much mitigation helps, but rarely in which action wins. Where they do, on an unseen readout type, the learned models generalized worse than the rule.

## Slide 8: Contribution and remaining academic work (Tushar, 4:09–4:43)

> To summarize, we contribute three things:
>
> - mitigation fixes calibration, not discrimination;
> - a leakage-safe benchmark across 64 models;
> - a pre-registered test showing that a simple probe rule is enough in this setting; fixed learned comparators did not reduce material errors.
>
> Next, we polish the manuscript by October 20 and update this presentation by October 27. We revise after your feedback in November and deliver the final package in December.
>
> Thank you. We are happy to take questions.

---

## Delivery notes

- **Hand-off:** at the end of slide 4 ("Tushar will take it from here") to keep the flow.
- **If time is short:** compress slide 3 to one sentence about the data and the 64 models.
- **Do not claim:** quantum advantage, hardware validation, or that results generalize beyond simulated 4-qubit circuits. Do not call the simulated noise "realistic"; say "our joint-noise design".
- **Material error:** a choice whose Brier score is more than 20% above the best action's, or that costs at least one extra shot-set per inference. Have this definition ready.
- **Planning dates:** the milestones on slide 8 are planning targets. Confirm them against the course calendar before presenting (`deliverables/submission/SUBMISSION_PLAN.md`).
- **Likely questions:** see `Final_QA.md` (the same questions apply to this talk).
