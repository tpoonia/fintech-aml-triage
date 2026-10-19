# Q-TRACE — Final experimental findings: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | November 24, 2026 (meeting 6 of 7): Final experimental findings |
| **Deck** | `Q-TRACE_2026-11-24_Final-Findings.pptx` (5 slides) |
| **Speakers** | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) |
| **Length** | ≈ 4:21 of speech (≈ 609 spoken words at 140 words per minute, numerals expanded); Tushar ≈ 2:27, Mayank ≈ 1:54 |
| **Status** | Ready for review. Reports the one-time sealed test of Oct 8, 2026. Before presenting, update slide 5 with any author decisions made since Oct 8 (venue, author order, references). |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | One sealed test: the simple rule held | Tushar | 0:00–0:28 | one-time sealed test, Oct 8; H1–H4 supported; only four held-out structures | How the test was protected. |
| 2 | The one-time sealed evaluation | Tushar | 0:28–1:21 | 16 unseen models, 4 structures (one mean-Z); frozen + fingerprinted + pushed, then one guarded unlock; material 2.0% [1.4, 2.6]; Brier −0.03%; +0.6% shots; 5B 8.8% ≤ 10% | How did the learned comparators compare? |
| 3 | The rule versus learned comparators | Tushar | 1:21–2:27 | material: GBT 2.1% vs 2.0%, diff +0.0005 [−0.016, +0.027] → H2 non-superiority; raw disagreement: GBT 6.5% vs rule 21.9% (mostly mean-Z; cheap, not material); learned unstable: GBT 10.7% on validation; 12–44% under categorical noise | Hand-off to Mayank: resources and limits. |
| 4 | Reliability, resources, and what the test cannot show | Mayank | 2:27–3:27 | rule: +0.6% shots vs Oracle, −3.4% vs always-combined; never-mitigate 0.35× shots, 96% material errors; always-A3 5.9% = 1/17 gate-free design share; 4 structures → CIs too narrow; H2 is non-superiority; simulation only; thermal blind spot | So what is the contribution, and where does it go next? |
| 5 | Contribution and the path to publication | Mayank | 3:27–4:21 | three contributions; no quantum-advantage claim; manuscript + report drafted; nothing submitted; plan: arXiv → TMLR; alternatives QCE27, QMI; author decisions pending | Questions; next meeting: the final defense. |

## Sources for the numbers on these slides

- **Slide 2:** final_metadata.json (unlock record, hypotheses); final_policies_5c_test.csv and final_policies_5b_test.csv (R_thr, arm all).
- **Slide 3:** final_paired_vs_rthr_5c_test.csv, final_paired_vs_rthr_5b_test.csv; final_policies_5c_test.csv (failure); p7_policies_5c_val.csv (L_gbt 0.107).
- **Slide 4:** final_policies_5c_test.csv (mean_total_shots_per_inference, material_failure; chart: semester cost_reliability_slide); p5c_design.csv (17 gate settings, one gate-free); p5c_probe_validity.csv.
- **Slide 5:** deliverables/README.md; deliverables/submission/VENUES.md and SUBMISSION_PLAN.md.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
