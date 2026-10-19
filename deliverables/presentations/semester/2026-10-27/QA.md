---
title: "Professor Q&A sheet — October 27, 2026 (Noise and mitigation)"
subtitle: "Phases 3B and 4, completed October 7, 2026"
---

**1. If noise does not hurt AUPRC, why mitigate at all?**
Because fraud alerts fire at a fixed threshold, and the decision depends on calibrated probabilities. Under combined-high noise the Brier score rose from 0.0093 to 0.121 and precision at the frozen threshold fell from 0.53 to 0.03, even though AUPRC changed by at most 0.003.

**2. Did noise leave the ranking completely unchanged?**
Not exactly. Scores among legitimate transactions reorder slightly (Kendall τ 0.96–0.99), but discrimination is preserved: AUPRC and AUROC stay within their intervals, and at least 46 of the 47 top-ranked frauds stay on top. We say "not discrimination", not "not ranking".

**3. Why compare ZNE with three times the shots?**
ZNE uses three circuits, hence three times the shots. The fair question is whether that budget is better spent on mitigation or on more samples of the unmitigated circuit. Extra shots left Brier unchanged (0.121 versus 0.122 under combined-high noise), because shots reduce variance, not bias.

**4. Why linear extrapolation rather than Richardson?**
Linear least squares over λ = 1, 3, 5 was registered in advance. Richardson recovered more of the exact Brier gap (43–97% versus 13–70%), but at about 5.2× the shot variance, so it was kept as a diagnostic (decision O09).

**5. What is the symmetric-readout negative control?**
Symmetric readout noise rescales parity scores exactly, so it cannot change their ranking. The simulation confirmed this: ranking metrics unchanged and affine residual $\le 4.4\times10^{-16}$. This checks the noise engine.

**6. Are the asymmetric readout profiles real device data?**
No. They are synthetic stress tests.

**7. Did mitigation help everywhere?**
It restored calibration where its noise type was present:

- readout mitigation: 0.053 → 0.011 under readout noise;
- ZNE: 0.055 → 0.038 under depolarizing noise;
- combined mitigation: 0.122 → 0.054 under combined noise.

No action improved AUPRC beyond its resource-matched comparator. The best action depended on the noise type.

**Sources:** `p3b_exact_metrics.csv`, `p3b_negative_control.csv`, `p4_summary.csv`, `p4_resource_matched.csv`, `docs/DECISIONS.md` (O09).
