---
title: "Q-TRACE · September 29, 2026 · Research design"
subtitle: "One-page summary · meeting 2 of 7 · retrospective reconstruction, prepared October 2026"
---

**Status.** This is a retrospective reconstruction. The repository record begins on Oct 6, 2026. It preserves the pre-October design as a generic QML study (Iris, QM9, WDBC) with a mitigate-or-not decision (`docs/DECISIONS.md`, Q1). It also includes the early-October research plan's description of the deck of that time. The fraud-detection application was adopted on Oct 6, so it is described here as a later change. No results existed on this date.

**Purpose.** To lay out how the study would be built: the scope, the model template, the mitigation methods and the evaluation plan.

**Key messages.**

- **Scope as recorded.**
  - Benchmarks Iris and WDBC (classification) and QM9 (molecular properties), simulated with Qiskit Aer.
  - Decision: mitigate or not, with ZNE or readout mitigation.
  - Q-TRACE weighs expected benefit against cost.
- **Model template.** A variational quantum classifier: encoding U(x), a trainable ansatz V(θ), a measured expectation value, and a classical optimizer (Havlíček 2019; Schuld 2020).
- **Mitigation.** ZNE folds gates to amplify noise and extrapolates to zero noise (Temme 2017; Giurgica-Tiron 2020). Readout mitigation needs a few calibration circuits.
- **Evaluation (reconstructed).** Run each setting with and without mitigation, record the change in quality and the extra resources, and compare Q-TRACE with never, always and a fixed rule.
- **Example input then.** "Current accuracy". It needs labels, so it was removed on Oct 6 (A12).
- **Not recorded at this stage.** Exact metrics, noise models and thresholds.

| Slide | Content | Speaker (proposed) |
|---|---|---|
| 1 | Title | Tushar |
| 2 | Scope as recorded, and what came later | Tushar |
| 3 | Variational quantum classifier template | Tushar |
| 4 | Zero-noise extrapolation (and readout mitigation) | Mayank |
| 5 | Evaluation plan | Mayank |

**What happened next (added October 2026).**

- **Oct 6:** fraud detection was adopted, with several mitigation actions, label-free inputs and pre-registered, gated phases.
- **Oct 6–8:** the study was completed.

**Needs confirmation.**

- The presenter split.
- Whether any original September materials exist.
- The meeting date: it was supplied by the team and is not on a public course calendar.
