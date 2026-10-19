# Q-TRACE — Noise and mitigation: speaker notes

| | |
|-----------|-------------------------------------------------------------|
| **Meeting** | October 27, 2026 (meeting 4 of 7): Noise and mitigation |
| **Deck** | `Q-TRACE_2026-10-27_Noise-and-Mitigation.pptx` (5 slides) |
| **Speakers** | Tushar: slides 1–3 · Mayank: slides 4–5 (proposed, alternating the opener across meetings; team to confirm) |
| **Length** | ≈ 4:21 of speech (≈ 608 spoken words at 140 words per minute, numerals expanded); Tushar ≈ 2:25, Mayank ≈ 1:56 |
| **Status** | Ready for review. Presents Phases 3B and 4, completed on Oct 7, 2026, in more depth than the Oct 13 overview. |

| # | Slide | Speaker | Time | Key points | Transition |
|--|----------------|-------|---------|----------------------------------|--------------|
| 1 | Noise breaks calibration; mitigation repairs it | Tushar | 0:00–0:24 | Phases 3B and 4, completed Oct 7; noise damaged calibration, not discrimination; mitigation repaired calibration; extra shots did not | First, how we simulated noise. |
| 2 | How we simulated noise | Tushar | 0:24–1:21 | Qiskit Aer density matrices: exact; depolarizing, thermal relaxation, readout; low/medium/high + combined = 12 anchors; symmetric readout negative control passed (ranking change 0; affine residual ≤ 4.4e-16); asymmetric profiles are synthetic | So what did noise actually change? |
| 3 | Noise damages calibration, not discrimination | Tushar | 1:21–2:25 | ΔAUPRC ≤ 0.003, all CIs contain 0; ≥ 46 of 47 top frauds kept; Brier 0.0093 → 0.121; ECE 0.083 → 0.346; precision 0.53 → 0.03; some bulk reordering (Kendall τ 0.96–0.99) | Hand-off to Mayank: the mitigation tools. |
| 4 | Two mitigation tools, very different costs | Mayank | 2:25–3:19 | readout: 2 calibration circuits per batch, tensored inverse + simplex projection; ZNE: global folding λ = 1, 3, 5, linear extrapolation: 3× shots, 9× CX exposure; fair baseline: same 3× shots, unmitigated | So which one is worth paying for? |
| 5 | Mitigation repairs calibration; extra shots do not | Mayank | 3:19–4:21 | Brier 0.053 → 0.011 (readout), 0.055 → 0.038 (ZNE), 0.122 → 0.054 (both); 3× shots 0.121; no AUPRC gain over the resource-matched comparator; best action depends on the noise type → selection question (Nov 10) | Questions. |

## Sources for the numbers on these slides

- **Slide 2:** configs/noise/anchors_rr_v1.yaml; p3b_noise_matrix.csv; p3b_negative_control.csv.
- **Slide 3:** p3b_exact_metrics.csv (model p3a_r); p4_exact_diagnostics.csv (clean precision 0.532).
- **Slide 4:** configs/mitigation/*.yaml; p4_costs.csv; zne_schematic is illustrative (labelled).
- **Slide 5:** p4_summary.csv (s1024); p4_resource_matched.csv; p4_best_action.csv.

Every number traces to `results/tables/`; see `../FIGURES.md` and `deliverables/figures/FIGURES.md`.
