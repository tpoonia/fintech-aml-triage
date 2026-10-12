# Q-TRACE — Research proposal: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | September 15, 2026 (meeting 1 of 7): Research proposal |
| **Deck** | `Q-TRACE_2026-09-15_Research-Proposal.pptx` (5 slides) |
| **Speakers** | Mayank: slides 1–3 · Tushar: slides 4–5 (proposed; no presenter record exists for this date; team to confirm) |
| **Length** | ≈ 3:45 of speech (≈ 526 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 2:17, Tushar ≈ 1:28 |
| **Status** | Retrospective reconstruction prepared in October 2026; see the note below |

> Retrospective reconstruction, prepared in October 2026. The repository record begins on Oct 6, 2026. It preserves the pre-October project as a generic QML study (Iris, QM9, WDBC) with a binary mitigate-or-not decision (docs/DECISIONS.md, Q1). The early-October research plan (docs/research/deep-research-report.md) describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and 'current accuracy' as an example input. The record does not say which of these were shown on Sept 15. Background slides use published literature, and no results existed on this date. If the team has the original September slides, they take precedence.

## Slide 1: When is quantum error mitigation worth its cost?

**Mayank** · 0:00–0:33

> Good afternoon. We are Mayank and Tushar, and this is our research proposal. One note first: this version of the deck was reconstructed in October from our project record, so it shows the proposal stage and nothing later.
>
> Quantum machine-learning models run on noisy hardware, and error mitigation can correct some of that noise, at a price. Our question is simple to state: when is that price worth paying, and can a decision layer tell the difference?

## Slide 2: Why quantum noise matters

**Mayank** · 0:33–1:30

> Today's quantum processors are noisy, the so-called NISQ era described by Preskill.
>
> A quantum machine-learning model produces its output from measured expectation values. Gate errors, decoherence and imperfect measurement pull those values toward zero, and the effect grows with circuit depth. The left panel shows this for a simple illustrative noise model.
>
> For a classifier, the result is that its probabilities drift toward one half. A decision that depends on those probabilities, such as an alert above a threshold, can then change even if the underlying model is good. So noise is not only a hardware problem; it changes what the model tells us. And the damage is not the same everywhere: it depends on the circuit, the type of noise and its strength. That variation is what makes a context-dependent decision worth studying.

## Slide 3: Why error mitigation is expensive

**Mayank** · 1:30–2:17

> Error mitigation reduces the bias that noise introduces, without full error correction. Two widely used techniques matter here.
>
> Zero-noise extrapolation, or ZNE, runs the same circuit at several deliberately amplified noise levels, for example by folding gates, and extrapolates the results back to zero noise, as shown on the right. That means extra circuits: more shots, and more exposure to two-qubit gates. Readout mitigation is cheaper: it corrects measurement errors using a few calibration circuits.
>
> And the benefit is not guaranteed. A resource-normalized evaluation across hardware platforms found mitigation beneficial on average but strongly platform-dependent. Applying it everywhere, every time, can waste resources. Tushar will describe what we propose.

## Slide 4: Proposed approach: Q-TRACE

**Tushar** · 2:17–2:57

> We propose Q-TRACE, a decision layer that sits on top of a quantum machine-learning model.
>
> For each run, Q-TRACE decides whether mitigation is worth applying, using a simple principle: mitigate only when the expected benefit outweighs the extra cost. The mitigation techniques are zero-noise extrapolation and readout mitigation, and the models are simulated with Qiskit Aer.
>
> As recorded, the benchmarks were standard tasks: Iris and the Wisconsin breast-cancer data for classification, and QM9 for molecular properties. And Q-TRACE would be compared with three simple policies: never mitigate, always mitigate, and a fixed rule.

## Slide 5: Research questions and planned method

**Tushar** · 2:57–3:45

> We have two research questions. First, when does error mitigation improve a quantum model's output enough to justify its extra cost? Second, can Q-TRACE's benefit-versus-cost decision do better than never mitigating, always mitigating, or a fixed rule?
>
> Our plan has four steps. We simulate noisy quantum models on the benchmark tasks. For each setting we measure what mitigation changes and what it costs. Q-TRACE then decides by weighing benefit against cost. And we compare it with the three simple policies.
>
> For the record: this deck was reconstructed in October. The project was narrowed on October 6 to credit-card fraud detection with several mitigation actions, which is what the following meetings report. Thank you.

## Delivery notes

- This deck is a record of the proposal stage, not a recording of what was said on Sept 15. If shown, say so.
- Do not add any result: none existed on this date.
