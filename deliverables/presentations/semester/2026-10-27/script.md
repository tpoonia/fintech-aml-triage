# Q-TRACE — Noise and mitigation: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | October 27, 2026 (meeting 4 of 7): Noise and mitigation |
| **Deck** | `Q-TRACE_2026-10-27_Noise-and-Mitigation.pptx` (5 slides) |
| **Speakers** | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) |
| **Length** | ≈ 4:21 of speech (≈ 608 spoken words at 140 words per minute, numerals expanded); Tushar ≈ 2:25, Mayank ≈ 1:56 |
| **Status** | Ready for review. Presents Phases 3B and 4, completed on Oct 7, 2026, in more depth than the Oct 13 overview. |

## Slide 1: Noise breaks calibration; mitigation repairs it

**Tushar** · 0:00–0:24

> Good afternoon. Today we go deeper into two completed phases of Q-TRACE: how simulated noise affects our quantum fraud classifier, and what error mitigation does about it.
>
> Both phases were completed on October 7. In short: noise damaged calibration and threshold decisions, not discrimination. Mitigation repaired calibration, and simply buying three times the shots did not.

## Slide 2: How we simulated noise

**Tushar** · 0:24–1:21

> We simulate the frozen classifier exactly, with Qiskit Aer density matrices, so every effect we see comes from the noise model and not from sampling.
>
> There are three noise sources. Depolarizing errors follow one- and two-qubit gates. Thermal relaxation acts during 35-nanosecond and 300-nanosecond gates. Readout confusion flips measured bits. Each source has low, medium and high anchors, and a combined profile uses all three, which gives twelve conditions. Finite-shot experiments then use 1,024 shots and 20 replicates per condition.
>
> Symmetric readout noise also serves as a negative control: in theory it is an exact rescaling of parity scores, so it cannot change their ranking, and in simulation the ranking metrics did not change at all. Three asymmetric readout profiles are synthetic stress tests, not device data.

## Slide 3: Noise damages calibration, not discrimination

**Tushar** · 1:21–2:25

> Here is the main characterization result. On the left, AUPRC barely moves under any anchor condition: at most 0.003, and every interval contains zero. At least 46 of the 47 top-ranked frauds stay on top.
>
> On the right, calibration collapses. Under combined high noise the Brier score rises from 0.0093 to 0.121, about thirteen times worse, and expected calibration error rises from 0.083 to 0.346. Noise pulls the scores toward one half. Because fraud alerts fire at a fixed threshold, precision falls from 0.53 to 0.03.
>
> So the problem mitigation must solve is calibration, not discrimination. Noise does reorder some legitimate transactions, with Kendall tau between 0.96 and 0.99, but the frauds at the top survive. Mayank will now explain the two mitigation tools.

## Slide 4: Two mitigation tools, very different costs

**Mayank** · 2:25–3:19

> We compare two standard mitigation techniques, and their combination.
>
> Readout mitigation runs two calibration circuits per batch, all zeros and all ones. From their counts it estimates each qubit's confusion matrix, inverts it, and projects the result back onto valid probabilities. Once calibrated, it is almost free.
>
> Zero-noise extrapolation, or ZNE, deliberately amplifies gate noise by folding the circuit, running it at noise scales one, three and five, and extrapolating linearly back to zero noise. That costs three times the shots and nine times the two-qubit-gate exposure. The combined action applies readout mitigation at every noise scale before extrapolating.
>
> The fair comparison for ZNE is therefore not "no mitigation" but the same three-times shot budget spent on the unmitigated circuit. We call that the extra-shots action.

## Slide 5: Mitigation repairs calibration; extra shots do not

**Mayank** · 3:19–4:21

> Here is the resource-matched comparison at 1,024 shots.
>
> Mitigation restores calibration where its noise type is present. Readout mitigation cuts the Brier score from 0.053 to 0.011 under high readout noise. ZNE cuts it from 0.055 to 0.038 under high depolarizing noise. Combined mitigation cuts it from 0.122 to 0.054 under combined high noise. Three times the shots leaves it at 0.121, because shots reduce variance, not bias.
>
> Mitigation never improved AUPRC beyond its shot-matched comparator, which fits the previous slide.
>
> And the best action depended on the noise type: none, readout mitigation, ZNE or both. That made selective mitigation look like a real decision. Whether that decision needs to be learned is the topic of our next meeting. Thank you.

## Delivery notes

- Say 'discrimination' (AUPRC, AUROC, the top-ranked frauds), not 'ranking': noise did slightly reorder scores among legitimate transactions.
- The asymmetric readout profiles are synthetic stress tests, not device data.
- These results were completed on Oct 7; present them as completed findings.
