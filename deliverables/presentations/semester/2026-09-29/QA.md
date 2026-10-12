---
title: "Professor Q&A sheet — September 29, 2026 (Research design)"
subtitle: "Retrospective reconstruction, prepared October 2026"
---

**Short answers to likely questions.** "Later outcome" notes report what the completed study (Oct 6–8, 2026) did; they were not known on Sept 29.

**1. Where is the fraud-detection application?**
It is not part of this stage. The record dates the fraud-specific design to the research plan of early October, adopted on Oct 6, 2026 (`docs/DECISIONS.md`, Q1). It "supersedes the earlier generic QML (Iris/QM9/WDBC) and binary-mitigation framing". Presenting fraud as the Sept 29 design would misstate the record.

**2. What exactly is the model?**
For the classification benchmarks, a variational quantum classifier: a data-encoding circuit, a trainable layered ansatz and a measurement, trained by a classical optimizer (Havlíček et al. 2019; Schuld et al. 2020) and simulated with Qiskit Aer. *Later outcome:* the frozen fraud model used a ZZ feature map, a two-layer RealAmplitudes ansatz with 12 parameters, and a four-qubit parity readout.

**3. How does zero-noise extrapolation work, and what does it cost?**
Gates are folded (G → G G† G) to amplify noise without changing the ideal result. The circuit is measured at several noise levels and the trend is extrapolated to zero noise (Temme et al. 2017; Giurgica-Tiron et al. 2020). Every extra level is another circuit, so shots and two-qubit-gate exposure grow. Readout mitigation, also named in the record, needs only a few calibration circuits.

**4. What are the baselines?**
Never mitigate, always mitigate and a fixed rule, compared with Q-TRACE's benefit-versus-cost decision, as the research plan describes the deck of that time.

**5. What inputs would Q-TRACE use?**
The deck of that time showed "current accuracy" as an example input. That needs labels a deployed system does not have. *Later outcome:* on Oct 6 the inputs were restricted to label-free probes and static descriptors (decisions A01, A12).

**6. Which metrics will you use?**
They were not recorded at this stage, and we do not invent them. *Later outcome:* the Brier score became the primary endpoint, because noise mainly damaged calibration.

**References:** Havlíček et al. 2019 (Nature 567:209); Schuld et al. 2020 (PRA 101:032308); Temme et al. 2017 (PRL 119:180509); Giurgica-Tiron et al. 2020 (IEEE QCE).
