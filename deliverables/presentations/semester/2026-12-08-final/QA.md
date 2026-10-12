---
title: "Professor Q&A sheet — December 8, 2026 (Final capstone defense)"
subtitle: "Short version; the full guide is Technical_QA_Guide.pdf"
---

**1. What is the answer in one sentence?**
In the studied setting, a simple observable probe rule performed competitively with learned comparators. Two pre-registered gates did not justify training a learned controller, and fixed learned comparators did not reduce material errors on a one-time sealed test.

**2. Is there a quantum advantage?**
No. Classical models on the same four inputs score higher (AUPRC 0.59–0.62 versus 0.507). The VQC is the noisy workload whose mitigation decisions we study.

**3. Why simulation instead of hardware?**
We needed exact paired counterfactuals: every action on the same model and noise context, with the true noise known for the offline Oracle. That gave about 1.4 million outcomes. Hardware validation is the main open gap.

**4. Why only four held-out structures, and does it matter?**
Structures are the independent units, and 16 were split 8/4/4. With four clusters, the bootstrap intervals are likely too narrow. We state this wherever an interval appears (backup B5).

**5. Did a learned model do better on anything?**
Yes, on raw agreement with the Oracle: gradient boosting 6.5% disagreement against the rule's 21.9%. Most of the rule's extra choices came from the unseen mean-Z structure, cost two calibration circuits each and were not material. Gradient boosting also made fewer material errors on the three parity structures, but more on the mean-Z one. Overall, on the registered endpoint (material errors), it was a tie: 2.1% versus 2.0%.

**6. Is the advantage over always-combined real?**
It depends on the design. Always-combined's 5.9% material errors are exactly the one gate-free setting out of 17, so the 3.4% shot saving scales with how often batches are gate-free (backup B3).

**7. Why not PEC, CDR or dynamical decoupling?**
PEC's sampling cost grows exponentially. CDR needs near-Clifford training circuits. Dynamical decoupling targets idle and coherent errors, which our gate-level noise model does not include. All three are future work.

**8. How was the sealed test protected?**
Outcomes were stored outside version control, with hashes committed. A guard allowed one unlock after the protocol and the frozen comparators were pushed, and every read is logged. The comparators reproduced their decision fingerprints.

**9. How was AI assistance used?**
An AI coding assistant (Claude Code) helped with engineering, analysis scripting and drafting, under the authors' direction. Its use is logged in `docs/ai_tool_log.md`. Team review of several entries and of the references is still pending and will be completed before any submission.
