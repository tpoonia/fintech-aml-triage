# Q-TRACE — Implementation progress: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | October 13, 2026 (meeting 3 of 7): Implementation progress |
| **Deck** | `Q-TRACE_2026-10-13_Implementation-Progress.pptx` (5 slides) |
| **Speakers** | Mayank: slides 1–3 · Tushar: slides 4–5 (same first-half/second-half pattern as the committed Oct 13 script; team to confirm) |
| **Length** | ≈ 4:18 of speech (≈ 602 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 2:14, Tushar ≈ 2:04 |
| **Status** | Ready for review. Reports work completed on Oct 6–7, 2026 (Phases 1–3B); the full study was completed on Oct 8, 2026. |

## Slide 1: From data to a working quantum classifier

**Mayank** · 0:00–0:33

> Good afternoon. We are Mayank and Tushar, and this is our implementation progress update for Q-TRACE.
>
> Today we cover the implementation milestones: the data pipeline, the classical baselines, the frozen quantum classifier, a repair to its encoding, and our first noise characterization. All of this was completed on October 6 and 7. The full study, including the sealed held-out test, was completed on October 8, and we will present those results in depth at the next meetings.

## Slide 2: Leakage-safe data and strong classical baselines

**Mayank** · 0:33–1:26

> We use the public European credit-card fraud dataset: 284,807 transactions, of which 492 are frauds.
>
> We removed exact duplicates, which leaves 283,726 rows and 473 frauds, or 0.17 percent. Rows that differ only in their timestamp are kept together, so they can never straddle partitions. That gives five disjoint partitions. All preprocessing is fitted on the training partition only, and the controller test partition is sealed from the start.
>
> Classical models then set the bar. On all thirty features, random forest reaches an AUPRC of 0.805. On the same four inputs and training rows the quantum model uses, classical models reach about 0.59 to 0.62.

## Slide 3: The frozen quantum classifier

**Mayank** · 1:26–2:14

> This is the frozen classifier, which every later experiment uses as its reference model.
>
> Four features, chosen on the training data, are encoded as angles on four qubits. A ZZ feature map entangles every pair of qubits, a two-layer RealAmplitudes ansatz carries the 12 trainable parameters, and we read out the four-qubit parity, which maps to a fraud probability. After transpilation the circuit has 18 two-qubit gates.
>
> We train it with COBYLA on a balanced subset: all 213 training frauds plus four legitimate transactions for each fraud. Its parameters and circuit are hashed, and retraining reproduces it exactly. Tushar will now explain the repair that made it work.

## Slide 4: Encoding repair: AUPRC 0.104 → 0.507

**Tushar** · 2:14–3:16

> Our first quantum model learned almost nothing: its validation AUPRC was only 0.104.
>
> Diagnostics on the training data showed why. The original encoding clipped values at three interquartile ranges and mapped them to the full minus pi to pi range. Most fraud values were clipped, 123 frauds were clipped on all four features, and only 91 of the 213 training frauds remained distinct inputs. The wide angle range also caused phase aliasing.
>
> A pre-registered repair, selected by cross-validation on training data only, clips at fifteen interquartile ranges and uses a quarter of the angle range. Now 212 frauds stay distinct, and validation AUPRC rises to 0.507, with an AUROC of 0.957. Classical models on the same inputs still reach 0.59 to 0.62, so we make no quantum-advantage claim.

## Slide 5: First noise result, and where the project stands

**Tushar** · 3:16–4:18

> Our first noise characterization used exact density-matrix simulation of the frozen model, under depolarizing, thermal and readout noise.
>
> Discrimination barely moved: across the twelve anchor conditions, AUPRC changed by at most 0.003, and every interval contains zero. Calibration did not survive. Under combined high noise the Brier score rose from 0.0093 to 0.121, and precision at the frozen threshold fell from 0.53 to 0.03. So noise mainly damages calibrated probabilities and threshold decisions. That reframed the whole project.
>
> On the right is where the project stands. Every experimental phase was completed by October 8, including the one-time sealed test, so nothing is still running. What remains is analysis, review and writing. The coming meetings present the noise and mitigation results, the policy study and the final findings in depth. Thank you.

## Delivery notes

- Say the completion dates out loud: these milestones were finished on Oct 6–7, and the whole study, including the sealed test, was finished on Oct 8. Nothing is still running.
- If asked about later results, give the one-line answer (a simple probe rule was enough) and point to the Nov 10 and Nov 24 meetings.
- Do not claim quantum advantage: classical models on the same four inputs score higher.
