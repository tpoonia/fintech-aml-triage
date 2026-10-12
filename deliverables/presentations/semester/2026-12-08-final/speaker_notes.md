# Q-TRACE — Final capstone defense: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | December 8, 2026 (meeting 7 of 7): Final capstone defense |
| **Deck** | `Q-TRACE_2026-12-08_Final-Defense.pptx` (18 slides + 6 backup) |
| **Speakers** | Mayank: slides 1–5, 10–11, 17–18 · Tushar: slides 6–9, 12–16 (proposed for roughly equal time; team to confirm) |
| **Length** | ≈ 13:15 of speech (≈ 1856 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 6:09, Tushar ≈ 7:07 |
| **Status** | Ready for review. Complete study (completed Oct 6–8, 2026). Confirm the allowed length with the instructor: the research plan records a 3–5-slide limit for the biweekly meetings. |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | When is quantum error mitigation worth paying for? | Mayank | 0:00–0:28 | the research problem; answer preview: a simple probe rule was enough in the studied setting | Why this is a real decision. |
| 2 | A noisy quantum classifier faces a spending decision | Mayank | 0:28–1:11 | readout ≈ 2 calibration circuits per batch; ZNE 3× shots, 9× CX; extra shots fix variance, not bias; fraud alerts need calibrated probabilities; per-context choice among five actions | What the literature already offers. |
| 3 | What the literature offers | Mayank | 1:11–1:57 | foundations: ZNE, readout inversion, PEC; does it pay? platform-dependent; can be worse at matched budget; adaptive selectors exist; QML fraud: classical baselines ahead on this dataset | So what is missing? |
| 4 | Research gap | Mayank | 1:57–2:36 | learned selectors use label-dependent or simulator-only context; gains reported mainly over static choices; gap: extra shots + combined actions, label-free probes, pre-registered held-out test vs simple rules | Our original hypothesis. |
| 5 | Original hypothesis and how we tested it | Mayank | 2:36–3:22 | H-control vs the committed alternative (a simple rule suffices); two gates decide whether to train a controller; sealed test: H1 near-Oracle, H2 learning adds nothing meaningful, H3 beats fixed policies, H4 transfers | Hand-off to Tushar: the architecture. |
| 6 | QML fraud-classification architecture | Tushar | 3:22–4:08 | ZZ map + RealAmplitudes (reps 2) + parity; 12 parameters, 18 CX; repair: AUPRC 0.104 → 0.507; classical 0.59–0.62 on the same inputs: no quantum advantage | The data behind it. |
| 7 | Dataset and leakage-safe preprocessing | Tushar | 4:08–4:50 | 284,807 → 283,726 rows, 473 frauds (0.17%); group-aware split into 5 partitions; preprocessing fitted on training only; controller test sealed; registry + tests prevent leakage | How we simulated noise. |
| 8 | Noise models | Tushar | 4:50–5:42 | depolarizing, thermal relaxation, readout; low/medium/high anchors; 5B: 8 conditions; 5C: 68 continuous joint points (17 gate × 4 readout, one gate-free); AUPRC ≤ 0.003 change; Brier up to 13× worse | What mitigation does about it. |
| 9 | Error-mitigation methods | Tushar | 5:42–6:28 | A0–A4 with explicit shot and CX costs; Brier 0.122 → 0.054 (combined); 3× shots 0.121; no AUPRC gain; best action depends on noise type | Hand-off to Mayank: the experimental design. |
| 10 | Experimental design and integrity | Mayank | 6:28–7:12 | from Phase 3A-R: registered before each phase's outcomes; sealed test: one guarded unlock, reads logged; comparators fingerprinted; 16 slow reproduction tests | How we scored decisions. |
| 11 | Evaluation metrics | Mayank | 7:12–8:03 | Brier primary; Oracle = cheapest within 10%; failure vs material failure (Brier > 1.2× best, or ≥ 1 extra shot-set); shots incl. probes (66·S per batch); two-stage cluster bootstrap | Hand-off to Tushar: the 64-model benchmark. |
| 12 | The 64-model benchmark | Tushar | 8:03–8:50 | 64 VQCs; median AUPRC 0.235 (0.047–0.538); split 8/4/4; ≈ 1.4 M paired outcomes (102,400 + 1,305,600); probes: readout calibration + 32-binding gate probe, 66 circuits per batch | What the policies made of it. |
| 13 | Policy comparison: the gates failed, a simple rule emerged | Tushar | 8:50–9:38 | G3B: category rule wrong in 0.33% → fail; G3C: R_thr material 2.0% [1.6, 2.7] → fail; residual detectable, not material → no controller trained | The sealed test. |
| 14 | Final held-out results | Tushar | 9:38–10:36 | R_thr material 2.0% [1.4, 2.6]; Brier −0.03%; 5B 8.8%; H1–H4 supported; GBT 2.1% material; better raw agreement (6.5% vs 21.9%) but not material | What it costs. |
| 15 | Cost–reliability findings | Tushar | 10:36–11:23 | rule: +0.6% vs Oracle, −3.4% vs always-combined; never mitigate: 0.35× shots, 96% material errors; always-A3 5.9% = 1/17 gate-free design share | The limits of these findings. |
| 16 | Limitations and threats to validity | Tushar | 11:23–12:04 | simulation only; 4 qubits; one dataset; two techniques; 4 held-out structures; H2 non-superiority; raw-endpoint caveat; thermal blind spot; design dependence; no quantum advantage | Hand-off to Mayank: the contribution. |
| 17 | Research contribution | Mayank | 12:04–12:42 | characterization: calibration, not discrimination; leakage-safe benchmark: 64 models, ≈ 1.4 M outcomes; pre-registered learning-vs-rule test; reproducible; manuscript drafted, nothing submitted | Our answer and what comes next. |
| 18 | Conclusions and future work | Mayank | 12:42–13:15 | answer: rule-based selective mitigation sufficed in the studied setting; future: hardware, richer mitigation + thermal probe, larger circuits | Questions (backup slides B1–B6). |
| 19 | B1 · Per-structure held-out results | either | backup | mean-Z structure drives raw disagreement; rule material 1.4% there; learned 5–30% | — |
| 20 | B2 · Where ZNE versus combined mitigation wins | either | backup | ZNE alone where readout error < ~0.003; A0/A1 only on the gate-free setting | — |
| 21 | B3 · Probe ablation and probing break-even | either | backup | gate probe alone: 1.8% / 9.4% material; break-even ≈ 645–685 transactions (≈ 80 categorical) | — |
| 22 | B4 · Baselines and the encoding repair | either | backup | RF 0.805 (30 features); 0.59–0.62 on VQC inputs; repair: 91 → 212 distinct fraud inputs; 0.104 → 0.507 | — |
| 23 | B5 · Statistical details | either | backup | material: no comparator meaningfully better; raw: several comparators significantly closer to Oracle; validation → test shifts; 4-cluster bootstrap caveat | — |
| 24 | B6 · References | either | backup | references for slides 3–4 and the methods | — |

## Sources for the numbers on these slides

- **Slide 2:** p5c_costs.csv; configs/mitigation/*.yaml.
- **Slide 3:** deliverables/paper/references.bib; deliverables/paper/REFERENCES_VERIFICATION.md.
- **Slide 4:** deliverables/paper/REFERENCES_VERIFICATION.md (claim checks a–m).
- **Slide 5:** docs/PREREG_P5B.md, docs/PREREG_P5C.md, docs/PREREG_FINAL.md; configs/final_test/final_v1.yaml.
- **Slide 6:** configs/repair/p3ar_v1.yaml; p5a_pool_metrics.csv (anchor); p3ar_validation_comparison.csv.
- **Slide 7:** ulb_v1_dataset_summary.csv; ulb_v1_phase1_metadata.json.
- **Slide 8:** configs/noise/anchors_rr_v1.yaml; p5c_design.csv; p3b_exact_metrics.csv (figure: deliverables/figures/fig3_noise_effects).
- **Slide 9:** p4_summary.csv (s1024); p5c_costs.csv.
- **Slide 10:** docs/PREREG_*.md; final_metadata.json (unlock record); tests/ (16 slow tests).
- **Slide 11:** configs/mixed_noise_study/p5c_v1.yaml; configs/final_test/final_v1.yaml.
- **Slide 12:** p5a_pool_metrics.csv; p5b_split.csv; Phase 5B/5C row counts (EXPERIMENT_PROTOCOL §3.12–3.13); p5b_feature_definitions.csv.
- **Slide 13:** p5b_metadata.json; p5c_metadata.json (R_thr cells/thresholds, g3c); fig5 source tables.
- **Slide 14:** final_policies_5c_test.csv; final_policies_5b_test.csv; final_paired_vs_rthr_5c_test.csv; final_metadata.json.
- **Slide 15:** final_policies_5c_test.csv; p5c_design.csv.
- **Slide 16:** final_policies_5c_test.csv; final_paired_vs_rthr_5c_test.csv; p5c_probe_validity.csv; p3ar_validation_comparison.csv.
- **Slide 17:** deliverables/paper/main.tex; deliverables/README.md.
- **Slide 19:** final_by_structure_5c_test.csv.
- **Slide 20:** p5c_preferred_by_point_train.csv, p5c_preferred_by_point_val.csv.
- **Slide 21:** ablation_probes.csv; ablation_probe_cost.csv.
- **Slide 22:** phase2_classical_metrics.csv; p3ar_validation_comparison.csv; p3ar_encoding_diagnostics.csv.
- **Slide 23:** final_paired_vs_rthr_5c_test.csv; final_paired_vs_rthr_5b_test.csv; p7_policies_5c_val.csv.
- **Slide 24:** deliverables/paper/references.bib.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
