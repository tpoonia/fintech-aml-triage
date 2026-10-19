---
title: "Professor Q&A sheet — November 24, 2026 (Final experimental findings)"
subtitle: "One-time sealed test, October 8, 2026"
---

**1. Can you trust intervals from four test structures?**
Only partly. A cluster bootstrap over four top-level clusters has few distinct resamples, so the intervals are likely too narrow; always-combined's interval is degenerate. The pre-registered detectable effect (about 0.70 SD) assumed 16 independent models, so power at the structure level is lower. The conclusion also rests on four separate validation structures (material failure 2.0% there as well) and on the mechanism (the gate probe alone carries the decision).

**2. Didn't gradient boosting beat the rule?**
Not on the registered endpoint: material errors were 2.1% versus 2.0% (difference +0.0005 [−0.016, +0.027]).

On any disagreement with the Oracle, yes: 6.5% versus 21.9%. Most of the rule's extra disagreements came from the unseen mean-Z structure and cost two calibration circuits per batch, so they were not material there (1.4%). Structure by structure, gradient boosting made fewer material errors on the three parity structures and more on the mean-Z one. Gradient boosting was also unstable, with 10.7% material errors on validation.

**3. What exactly does H2 show?**
Non-superiority on material errors. No learned comparator was better by the registered margin of 0.02 with an interval excluding zero, or cheaper by 5% at no more than 0.005 extra material failure. It does not prove that learning cannot help.

**4. Is the 3.4% saving over always-combined a design artifact?**
Largely, yes. Always-combined's 5.9% material errors are exactly the one gate-free setting out of 17 in our design. On a device where gate noise is always present, the saving shrinks to the ZNE-versus-combined choice (two calibration circuits).

**5. Under categorical noise, why did the old category rule win?**
The thresholds are environment-specific. The continuous-noise rule transferred within the registered bound (8.8% ≤ 10%), but the rule fitted on categorical data did better (6.4%; paired difference 0.024 [0.011, 0.037]). All learned comparators did worse (11.8–43.9%).

**6. Is the paper ready to publish?**
It is a complete draft for review; nothing has been submitted or accepted. Open items: author confirmation of references, author order, venue choice (recommended: arXiv, then TMLR) and an arXiv endorser.

**Sources:** `final_policies_5c_test.csv`, `final_policies_5b_test.csv`, `final_paired_vs_rthr_5c_test.csv`, `final_paired_vs_rthr_5b_test.csv`, `p7_policies_5c_val.csv`, `p5c_design.csv`.
