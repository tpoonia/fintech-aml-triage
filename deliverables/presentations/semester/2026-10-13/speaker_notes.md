# Q-TRACE — Implementation progress: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | October 13, 2026 (meeting 3 of 7): Implementation progress |
| **Deck** | `Q-TRACE_2026-10-13_Implementation-Progress.pptx` (5 slides) |
| **Speakers** | Mayank: slides 1–3 · Tushar: slides 4–5 (same first-half/second-half pattern as the committed Oct 13 script; team to confirm) |
| **Length** | ≈ 4:18 of speech (≈ 602 spoken words at 140 words per minute, numerals expanded); Mayank ≈ 2:14, Tushar ≈ 2:04 |
| **Status** | Ready for review. Reports work completed on Oct 6–7, 2026 (Phases 1–3B); the full study was completed on Oct 8, 2026. |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | From data to a working quantum classifier | Mayank | 0:00–0:33 | implementation milestones, Phases 1–3B; completed Oct 6–7; full study completed Oct 8; later meetings go deeper | Start with the data. |
| 2 | Leakage-safe data and strong classical baselines | Mayank | 0:33–1:26 | 284,807 → 283,726 rows, 473 frauds (0.17%); group-aware split, 0 groups cross partitions; classical AUPRC 0.805 (30 features); 0.59–0.62 on the VQC's inputs | Next, the quantum model we froze. |
| 3 | The frozen quantum classifier | Mayank | 1:26–2:14 | 4 qubits: ZZ feature map + RealAmplitudes (reps 2), parity readout; 12 parameters, 18 CX after transpilation; COBYLA on 1,065 balanced training rows; frozen and hashed | Hand-off to Tushar: why the first encoding failed. |
| 4 | Encoding repair: AUPRC 0.104 → 0.507 | Tushar | 2:14–3:16 | first encoding: saturation + aliasing; 91 of 213 fraud inputs distinct; pre-registered, training-only repair: 212 distinct; AUPRC 0.104 → 0.507 (AUROC 0.957); classical 0.59–0.62 on the same inputs | With a working model, we could study noise. |
| 5 | First noise result, and where the project stands | Tushar | 3:16–4:18 | AUPRC change ≤ 0.003, every CI contains 0; Brier 0.0093 → 0.121; precision 0.53 → 0.03 (combined-high); all phases complete by Oct 8; next meetings go deeper | Questions. |

## Sources for the numbers on these slides

- **Slide 2:** ulb_v1_dataset_summary.csv; ulb_v1_phase1_metadata.json; phase2_classical_metrics.csv (a-full, draw 0); p3ar_validation_comparison.csv.
- **Slide 3:** configs/vqc/vqc3a_top4_ra1.yaml; configs/repair/p3ar_v1.yaml; p5a_pool_metrics.csv (anchor p3a_r: 18 CX, 12 parameters).
- **Slide 4:** p3ar_encoding_diagnostics.csv (e0, e3); p3ar_validation_comparison.csv.
- **Slide 5:** p3b_exact_metrics.csv; p4_exact_diagnostics.csv (clean precision 0.532); git history for completion dates.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
