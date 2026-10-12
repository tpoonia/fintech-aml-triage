# Q-TRACE — Policy selection: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | November 10, 2026 (meeting 5 of 7): Policy selection |
| **Deck** | `Q-TRACE_2026-11-10_Policy-Selection.pptx` (5 slides) |
| **Speakers** | Mayank: slides 1–3 · Tushar: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) |
| **Length** | ≈ 4:27 of speech (≈ 624 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 2:25, Tushar ≈ 2:03 |
| **Status** | Ready for review. Presents Phases 5A–5C (completed Oct 7–8, 2026); the sealed-test results (test run Oct 8) are presented on Nov 24. |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | Does choosing mitigation need a learned controller? | Mayank | 0:00–0:24 | Phases 5A–5C, completed Oct 7–8; two gates found no material residual; no controller trained; a two-threshold rule emerged | Start with the decision we set out to learn. |
| 2 | The decision we proposed to learn | Mayank | 0:24–1:28 | context → probes → policy → one of A0–A4; H-control vs the committed alternative (a simple rule suffices); Oracle: cheapest within 10% of best Brier; material failure defined in advance; train a controller only if the gate passes | To test that fairly we needed many models and cheap probes. |
| 3 | 64 independent models and two cheap probes | Mayank | 1:28–2:25 | 64 VQCs = 16 structures × 4 seeds; median AUPRC 0.235 (0.047–0.538); split 8/4/4 by structure; test sealed; readout probe ρ = 0.999; gate probe ρ = −0.89 (depolarizing), −0.12 (thermal); 66 circuits per batch | Hand-off to Tushar: what the experiments showed. |
| 4 | Categorical, then continuous joint noise | Tushar | 2:25–3:25 | 5B: best action = lookup on noise type; 4-cell rule wrong in 0.33% (best single action wrong in 62.5%); 5C: 68 points × 3 budgets; A3 67–71%, A2 23–27%; budget changes choice < 3%; A4 never preferred; 16 of 17 gate settings carry gate noise (design) | So what did the gates conclude? |
| 5 | Both gates failed, and a simple rule emerged | Tushar | 3:25–4:27 | G3B: 0.33% < 5% → fail; G3C: material 2.0% [1.6, 2.7] < 5% → fail; residual detectable (MI 0.08 / 0.04 nats) but not material; rule: gate probe → ZNE; readout probe ≥ ~0.4% → add readout mitigation; no controller trained; fixed comparators evaluated on the sealed test (run Oct 8; presented Nov 24) | Questions; next meeting: the sealed test. |

## Sources for the numbers on these slides

- **Slide 2:** docs/PREREG_P5B.md, docs/PREREG_P5C.md; configs/mixed_noise_study/p5c_v1.yaml (ε = 0.10, material multiple 2, overspend 1·S).
- **Slide 3:** p5a_pool_metrics.csv; p5b_split.csv; p5b_feature_definitions.csv; p5c_probe_validity.csv (train, all budgets).
- **Slide 4:** p5b_metadata.json (category rule val failure 0.00332, best single 0.625); p5c_metadata.json (preferred_shares); p5c_budget_effect.csv; p5c_design.csv.
- **Slide 5:** p5b_metadata.json (g3b); p5c_metadata.json (g3c, rules/R_thr, structure_association); p5c_policy_eval.csv.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
