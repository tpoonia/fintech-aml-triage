---
title: "Professor Q&A sheet — November 10, 2026 (Policy selection)"
subtitle: "Phases 5A–5C, completed October 7–8, 2026"
---

**1. Why was no learned controller trained?**
The protocol said to train one only if a residual-complexity gate passed. Both gates failed:

- **G3B (categorical noise):** the category rule was wrong in 0.33% of validation cases.
- **G3C (continuous noise):** the best rule's material failure was 2.0% [1.6, 2.7], below the 5% threshold.

Training anyway would have been an unregistered analysis.

**2. Was there no residual structure at all?**
There was some. It was statistically detectable (mutual information 0.08 nats in 5B, 0.04 nats in 5C validation), mostly from mean-Z readouts, but far below materiality. So: "no material residual".

**3. What is a material failure?**
A choice whose Brier score exceeds the best by more than 20%, or that costs at least one extra shot-set per inference. Raw failure, meaning any disagreement with the Oracle, also counts near-ties and near-free overspends.

**4. Doesn't the rule just read the true noise?**
No. Policies never see true noise parameters, labels or identifiers; a feature registry and tests enforce this. The probes are deployable measurements that estimate the noise by design. The readout probe tracks the true readout error with ρ = 0.999. The gate probe tracks depolarizing noise (ρ = −0.89) but barely tracks thermal noise (ρ = −0.12).

**5. Is "gate noise almost always present" a finding about devices?**
No. It is a property of our design: 16 of 17 gate settings carry gate noise.

**6. Why 64 models?**
To make models, nested in structures, the independent unit of analysis. That is 16 structures × 4 seeds, split 8/4/4, with the test structures sealed.

**7. Do the thresholds transfer to other devices?**
Not without refitting. The roughly 0.4% readout threshold and the 0.97–0.98 contraction threshold are specific to this simulated 4-qubit setting.

**Sources:** `p5a_pool_metrics.csv`, `p5b_metadata.json`, `p5c_metadata.json`, `p5c_probe_validity.csv`, `p5c_policy_eval.csv`.
