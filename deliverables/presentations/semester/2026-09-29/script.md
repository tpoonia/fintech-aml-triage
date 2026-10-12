# Q-TRACE — Research design: word-for-word script

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | September 29, 2026 (meeting 2 of 7): Research design |
| **Deck** | `Q-TRACE_2026-09-29_Research-Design.pptx` (5 slides) |
| **Speakers** | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed; no presenter record exists for this date; team to confirm) |
| **Length** | ≈ 4:10 of speech (≈ 584 spoken words at 140 words per minute, numerals expanded); Tushar ≈ 2:14, Mayank ≈ 1:56 |
| **Status** | Retrospective reconstruction prepared in October 2026; see the note below |

> Retrospective reconstruction, prepared in October 2026. The repository record begins on Oct 6, 2026. It preserves the pre-October design as a generic QML study (Iris, QM9, WDBC) with a binary mitigate-or-not decision (docs/DECISIONS.md, Q1). The early-October research plan (docs/research/deep-research-report.md) describes the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and 'current accuracy' as an example input. The fraud-detection application was adopted on Oct 6, so this deck describes it as a later change, not as the Sept 29 design. Technical background cites published literature. If the team has the original September materials, they take precedence.

## Slide 1: Designing the study: model, mitigation and evaluation

**Tushar** · 0:00–0:30

> Good afternoon. This is the research-design stage of Q-TRACE: how we intended to build the study before any experiment ran. As with our proposal deck, this version was reconstructed in October from the project record, so it contains no results.
>
> We cover the scope as it was recorded at this stage, the general shape of a variational quantum classifier, how zero-noise extrapolation works, and how the decision would be evaluated.

## Slide 2: Scope as recorded before October 6

**Tushar** · 0:30–1:20

> At this stage, as the record shows, the design was generic. The models were quantum machine-learning models on standard benchmarks: Iris and the Wisconsin breast-cancer data for classification, and QM9 for molecular properties, simulated with Qiskit Aer. The decision was whether to mitigate, with zero-noise extrapolation or readout mitigation. Q-TRACE would make that decision by weighing expected benefit against cost, and be compared with never mitigating, always mitigating and a fixed rule.
>
> We want to be transparent about one point. The application to credit-card fraud detection, and a design with several mitigation actions, were adopted later, on October 6. They are not part of this stage, and we do not present them as if they were.

## Slide 3: The variational quantum classifier template

**Tushar** · 1:20–2:14

> The classification models in the design are variational quantum classifiers, a well-established template.
>
> Input data are first encoded into qubit rotations by an encoding circuit, U of x. A trainable circuit, V of theta, follows, repeated in layers. Measuring the qubits gives an expectation value that becomes the class score. A classical optimizer then adjusts theta to reduce the training loss. Because the output is estimated from repeated measurements, called shots, it always carries sampling noise as well as hardware noise.
>
> The specific circuit, with its encoding, depth and readout, was chosen later, on the fraud data. What matters for our question is that the output is a measured expectation value, exactly the quantity noise distorts and mitigation tries to repair. Mayank will explain the mitigation side.

## Slide 4: Mitigation strategy: zero-noise extrapolation

**Mayank** · 2:14–3:15

> The mitigation in this design is zero-noise extrapolation.
>
> It works in two steps. First, amplify the noise on purpose, for example by folding the circuit: running a gate, its inverse and the gate again leaves the ideal result unchanged but multiplies the noise. Second, measure at several noise levels and extrapolate the trend back to zero noise. Folding adds a gate and its inverse in pairs, so common choices use odd scale factors, such as one, three and five.
>
> The cost is the reason for our project. Each extra noise level is another circuit to run, so ZNE multiplies shots and gate exposure. The record also lists readout mitigation, which corrects measurement errors with a few calibration circuits and costs far less. The decision the design asks for is therefore whether the expected improvement is worth those extra resources in a given setting.

## Slide 5: How the decision would be evaluated

**Mayank** · 3:15–4:10

> Finally, the evaluation design.
>
> For each benchmark and noise setting, we would run the model with and without mitigation, and record both the change in task quality and the extra resources used. Q-TRACE's benefit-minus-cost decision would then be compared with three simple policies: never mitigate, always mitigate, and a fixed rule. It is only worth building if it beats all three.
>
> One detail from the record is instructive. The deck at the time used "current accuracy" as an example input. That needs labels a deployed system would not have, and it was removed on October 6.
>
> The specific metrics and noise models were not recorded at this stage. They were fixed when the study was narrowed on October 6, and the following meetings report that study. Thank you.

## Delivery notes

- If shown, introduce it as a reconstruction of the design stage prepared in October.
- Do not present the fraud application, the five-action design or any metric values as decided on Sept 29: the record dates them to Oct 6 or later.
