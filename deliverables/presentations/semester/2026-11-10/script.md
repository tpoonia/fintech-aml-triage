# Q-TRACE — Policy selection: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | November 10, 2026 (meeting 5 of 7): Policy selection |
| **Deck** | `Q-TRACE_2026-11-10_Policy-Selection.pptx` (5 slides) |
| **Speakers** | Mayank: slides 1–3 · Tushar: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) |
| **Length** | ≈ 4:27 of speech (≈ 624 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 2:25, Tushar ≈ 2:03 |
| **Status** | Ready for review. Presents Phases 5A–5C (completed Oct 7–8, 2026); the sealed-test results (test run Oct 8) are presented on Nov 24. |

## Slide 1: Does choosing mitigation need a learned controller?

**Mayank** · 0:00–0:24

> Good afternoon. Today's question is the heart of our original proposal: does deciding when and how to mitigate need a learned controller?
>
> This covers Phases 5A to 5C, completed on October 7 and 8. Two pre-registered gates found no material structure left for a learned controller, so none was trained. A simple two-threshold probe rule emerged instead.

## Slide 2: The decision we proposed to learn

**Mayank** · 0:24–1:28

> For every context, meaning a model, a noise environment and a shot budget, the system must pick one of five actions: nothing, readout mitigation, ZNE, both, or three times the shots.
>
> Our original hypothesis was that a learned controller, Q-TRACE, could make this choice from cheap label-free probes better than fixed policies and a fairly tuned threshold rule. From the start we committed to report it as a result if a simple threshold rule matched the learned controller.
>
> The Oracle is evaluation-only. It picks the cheapest action whose Brier score is within ten percent of the best. A failure is any disagreement with it. A failure is material when the Brier score is more than twenty percent above the best, or when it costs at least one extra shot-set. And we committed to train a controller only if a gate found material structure that a simple rule missed.

## Slide 3: 64 independent models and two cheap probes

**Mayank** · 1:28–2:25

> To make models, not transactions, the unit of analysis, we trained 64 quantum classifiers: 16 structures times four seeds. Structures vary the features, the encoding, the ansatz and the readout. All 64 qualified on clean data, with a median AUPRC of 0.235. Structures were split eight, four and four into training, validation and sealed test models.
>
> A policy sees only static model descriptors and two label-free probes. The readout probe is the pair of calibration circuits that readout mitigation needs anyway. The gate probe runs 32 fixed synthetic inputs at fold factors one and three. Together they cost 66 circuits per batch. The readout probe tracks the true readout error almost perfectly, and the gate probe tracks depolarizing noise, but it barely sees thermal noise.

## Slide 4: Categorical, then continuous joint noise

**Tushar** · 2:25–3:25

> We ran every model under every action in two noise environments.
>
> In Phase 5B, with eight near-categorical noise conditions, the best action was simply a lookup on the noise type, and a four-cell probe rule was wrong in only 0.33 percent of validation cases.
>
> We then asked whether that was too easy, and in Phase 5C varied readout, depolarizing and thermal noise continuously and jointly, across 68 noise points and three shot budgets. That removed most of the choice. In our design, 16 of 17 gate settings carry gate noise, and combined mitigation was the Oracle's choice in 67 to 71 percent of contexts and ZNE in 23 to 27 percent. The shot budget changed the choice in fewer than three percent of cases, and three times the shots was never chosen.

## Slide 5: Both gates failed, and a simple rule emerged

**Tushar** · 3:25–4:27

> Both gates failed, as defined in advance.
>
> Under categorical noise the category rule was nearly perfect. Under continuous noise the best rule, shown here, disagreed with the Oracle in 9.6 percent of validation decisions, but only 2.0 percent were material, well below the five percent gate. The remaining structure, mostly from mean-Z readouts, was statistically detectable but small.
>
> The rule is two thresholds per shot budget. If the gate probe detects gate noise, use ZNE, and add readout mitigation when the readout probe exceeds about 0.4 percent error. Otherwise use readout mitigation alone. It works because mitigation removes a bias that shots cannot, and because in our design the material question is simply whether gate noise is present.
>
> As registered, we trained no controller. Next time: the sealed-test results, from the test we ran on October 8. Thank you.

## Delivery notes

- Be exact about the gates: the residual structure was statistically detectable but far below materiality, so 'no material residual', not 'no residual'.
- No Q-TRACE controller was ever trained. The learned models on Nov 24 are fixed comparators, specified in advance.
- Gate noise is present in 16 of 17 gate settings by design. Say 'in our design', not 'on real devices'.
