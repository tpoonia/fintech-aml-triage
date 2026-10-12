---
title: "Professor Q&A sheet — September 15, 2026 (Research proposal)"
subtitle: "Retrospective reconstruction, prepared October 2026"
---

**Short answers to likely questions.** "Later outcome" notes report what the completed study (Oct 6–8, 2026) found. Use them only if asked; they were not known on Sept 15.

**1. Is this the deck you presented on September 15?**
No. It is a reconstruction prepared in October 2026. The repository record begins on Oct 6, 2026. Two sources describe the pre-October project:

- the decision record: a generic QML study on Iris, QM9 and WDBC with a mitigate-or-not decision (`docs/DECISIONS.md`, Q1);
- the early-October research plan's description of the deck of that time: a benefit-minus-cost rule, a VQC, Qiskit Aer, ZNE and readout mitigation, a Never/Always/Fixed/Q-TRACE comparison, and "current accuracy" as an example input.

The record does not say which of these were shown on Sept 15. Original September materials, if they exist, take precedence.

**2. Why these benchmarks?**
The record names Iris and WDBC (classification) and QM9 (molecular properties) as the pre-October scope. *Later outcome:* on Oct 6 the scope was narrowed to credit-card fraud detection (decision Q1), a domain where calibrated, threshold-based decisions matter.

**3. Which mitigation techniques?**
Zero-noise extrapolation and readout mitigation, as the research plan describes the deck, with the decision framed as mitigate or not. *Later outcome:* combined mitigation and an extra-shots action were added from Oct 6 onward.

**4. Is mitigation always worth it?**
No. A resource-normalized study found mitigation beneficial on average but strongly platform-dependent (Russo et al., IEEE TQE 2023). That uncertainty motivates a per-context decision.

**5. How would Q-TRACE decide?**
By weighing expected benefit against extra cost, compared with never mitigating, always mitigating and a fixed rule. *Later outcome:* in the studied setting, a simple probe rule was enough, and no learned controller was justified.

**6. Will you use real quantum hardware?**
The record names Qiskit Aer simulation. *Later outcome:* all experiments were simulated, and hardware validation remains future work.

**References:** Preskill 2018 (Quantum 2:79); Temme et al. 2017 (PRL 119:180509); Kandala et al. 2019 (Nature 567:491); Giurgica-Tiron et al. 2020 (IEEE QCE); Bravyi et al. 2021 (PRA 103:042605); Russo et al. 2023 (IEEE TQE 4:1–18).
