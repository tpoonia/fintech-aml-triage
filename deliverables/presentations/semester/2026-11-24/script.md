# Q-TRACE — Final experimental findings: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | November 24, 2026 (meeting 6 of 7): Final experimental findings |
| **Deck** | `Q-TRACE_2026-11-24_Final-Findings.pptx` (5 slides) |
| **Speakers** | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) |
| **Length** | ≈ 4:21 of speech (≈ 609 spoken words at 140 words per minute, numerals expanded); Tushar ≈ 2:27, Mayank ≈ 1:54 |
| **Status** | Ready for review. Reports the one-time sealed test of Oct 8, 2026. Before presenting, update slide 5 with any author decisions made since Oct 8 (venue, author order, references). |

## Slide 1: One sealed test: the simple rule held

**Tushar** · 0:00–0:28

> Good afternoon. Today we report the final experimental findings of Q-TRACE: the one-time sealed held-out test, which we ran on October 8.
>
> All four pre-registered hypotheses were supported. The two-threshold probe rule was near the Oracle on unseen models, and fixed learned comparators did not reduce material errors. Only four structures were held out, so we will also be careful about what these results cannot show.

## Slide 2: The one-time sealed evaluation

**Tushar** · 0:28–1:21

> The test used 16 models from four structures that no policy had ever seen, including one with a mean-Z readout.
>
> Before opening it, we froze the rule and four learned comparators, recorded fingerprints of their decisions, and pushed the full protocol. A guard then allowed exactly one unlock and logged every read. The stored outcomes matched their committed hashes.
>
> Under continuous joint noise, the rule made material errors in 2.0 percent of decisions, with a confidence interval of 1.4 to 2.6 percent. Its Brier score was within 0.03 percent of the Oracle's, at 0.6 percent more shots. Under categorical noise its material errors were 8.8 percent, inside the pre-registered ten-percent bound.

## Slide 3: The rule versus learned comparators

**Tushar** · 1:21–2:27

> Here are paired differences between each comparator and the rule. Positive values favour the rule; the shaded band is the pre-registered margin.
>
> On the registered endpoint, material errors, the best learned comparator, gradient boosting, tied the rule: 2.1 versus 2.0 percent. Its interval excludes an advantage as large as the margin.
>
> But we want to be precise. On any disagreement with the Oracle, gradient boosting was better: 6.5 percent against 21.9 percent. Most of the rule's extra disagreements came from the unseen mean-Z structure and cost only two calibration circuits per batch, so they were not material. Structure by structure, gradient boosting made fewer material errors on the three parity structures and more on the mean-Z one. The learned models were also unstable: gradient boosting made 10.7 percent material errors on validation. Under categorical noise, learned models reached 12 to 44 percent.

## Slide 4: Reliability, resources, and what the test cannot show

**Mayank** · 2:27–3:27

> This chart puts reliability against cost. Never mitigating uses about a third of the shots but makes material errors almost everywhere. Always using combined mitigation is reliable but overspends. The rule sits next to the Oracle: 0.6 percent more shots and 3.4 percent fewer than always-combined.
>
> Now the limits. Always-combined's 5.9 percent material errors equal exactly the one gate-free setting in our seventeen, so the saving depends on how often batches are gate-free. Only four structures were held out, so the intervals are probably too narrow. H2 is a non-superiority result on material errors, not proof that learning cannot help. And everything is simulated, at four qubits, with a gate probe that barely sees thermal noise. We state these limits next to every headline number, in the paper and in the report.

## Slide 5: Contribution and the path to publication

**Mayank** · 3:27–4:21

> Our contribution has three parts. First, a characterization showing that noise damaged calibration, not discrimination, and that mitigation repaired it while extra shots could not. Second, a leakage-safe counterfactual benchmark across 64 models. Third, a pre-registered test of learning against simple rules, which found that, in this setting, a simple probe rule performed competitively with learned comparators.
>
> The manuscript and capstone report are complete drafts for review, built from the same verified numbers as these slides; nothing has been submitted. Our recommended route is an arXiv preprint and then TMLR, which judges whether claims match the evidence and charges no fees. IEEE Quantum Week and Quantum Machine Intelligence are alternatives. Remaining decisions are ours: confirm the references, author order, venue and an arXiv endorser. Thank you.

## Delivery notes

- Lead with the registered endpoint (material failure) and immediately disclose the raw-disagreement result; do not let a question surface it first.
- Say 'only four held-out structures' whenever an interval is quoted.
- Nothing has been submitted; the manuscript is a draft for review, not accepted or under review.
