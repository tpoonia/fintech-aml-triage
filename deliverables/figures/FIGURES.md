# Figure provenance

Every quantitative figure in the manuscript, the capstone report and the two decks is drawn from committed result tables in `results/tables/`. No number is typed in by hand. Figures 1 and 2 are schematics and contain no data.

**Regenerate:** `uv run python deliverables/figures/make_figures.py`. This writes a PDF (vector, used in LaTeX) and a PNG (220 dpi, used in the decks and the DOCX) for each figure.

**Palette:** Okabe–Ito, colour-blind safe. Each action keeps one fixed colour in every figure: A0 grey, A1 blue, A2 vermillion, A3 reddish purple, A4 orange.

## Figures made by `make_figures.py`

| File | Content | Source tables | Phase | Used in |
|---|---|---|---|---|
| `fig1_architecture` | Decision layer: what the policy sees and may choose; offline-only quantities | none (schematic) | — | paper Fig. 1; report; Oct 13 slide 3 |
| `fig2_workflow` | Pre-registered workflow with gate outcomes | none (schematic; gate outcomes as recorded in `p3b_metadata.json`, `p5b_metadata.json`, `p5c_metadata.json`, `final_metadata.json`) | — | paper Fig. 2; report; final slide 9 |
| `fig3_noise_effects` | ΔAUPRC with 95% paired bootstrap CIs and Brier score per noise condition | `p3b_exact_metrics.csv` | 3B | paper Fig. 3; report; final slide 7 |
| `fig4_mitigation` | Brier score by condition × action (1,024 shots, 20 replicates) | `p4_summary.csv` | 4 | paper Fig. 4; report; Oct 13 slide 4; final slide 8 |
| `fig5_preferred_actions` | Share of contexts in which each action is the cost-aware Oracle choice (5B and 5C, validation and test) | `p5b_metadata.json`, `p5c_metadata.json`, `final_metadata.json` (`preferred_shares`) | 5B, 5C, final | paper Fig. 5; report; Oct 13 slide 5 |
| `fig6_cost_reliability` | Material failure vs. total shots per inference ÷ Oracle, for each policy (5C and 5B test) | `final_policies_5c_test.csv`, `final_policies_5b_test.csv` (arm `all`) | final | paper Fig. 7; report; final slide 13 |
| `fig7_learned_vs_rule` | Paired material-failure difference, comparator − R_thr, with 95% two-stage cluster CIs | `final_paired_vs_rthr_5c_test.csv`, `final_paired_vs_rthr_5b_test.csv` (sign flipped from the stored R_thr − comparator) | final | paper Fig. 8; report; final slide 12 |
| `fig8_final_heldout` | Any disagreement and material failure for each policy, 5C test, with CIs | `final_policies_5c_test.csv` (arm `all`) | final | paper Fig. 6; report; Oct 13 slide 6; final slide 11 |
| `fig9_probe_ablation` | Material failure of probe variants on validation data | `ablation_probes.csv` | ablation (validation only) | paper Fig. 9; report; final slide 14 |

## Figures reused from the phase scripts (decks only)

These figures are made by the committed phase scripts from their own committed tables. They appear only in the final deck.

| File | Made by | Source tables | Used in |
|---|---|---|---|
| `results/figures/p3ar_pr_comparison.png` | `scripts/make_p3ar_figures.py` | `p3ar_pr_curves.csv`, `p3ar_validation_comparison.csv` | final slide 6 |
| `results/figures/p5c_a_design.png` | `scripts/make_p5c_figures.py` | `p5c_design.csv` | final slide 7 |
| `results/figures/final_b_structures.png` | `scripts/make_final_figures.py` | `final_by_structure_5c_test.csv` | final backup slide B1 |
| `results/figures/p5c_b_preferred_map.png` | `scripts/make_p5c_figures.py` | `p5c_preferred_by_point_train.csv`, `p5c_preferred_by_point_val.csv` | final backup slide B2 |

## Numbers quoted in text and on slides

| Quantity | Value | Source |
|---|---|---|
| R_thr material failure, 5C test | 0.020 [0.0145, 0.0260] | `final_policies_5c_test.csv`, `R_thr`, arm `all` |
| R_thr relative Brier regret, 5C test | −0.03% [−1.7%, +1.2%] | same row |
| R_thr shots vs Oracle | 5,195.17 / 5,165.22 = +0.58% | same file, `mean_total_shots_per_inference` |
| R_thr vs always-A3 shots | (5,376.06 − 5,195.17) / 5,376.06 = 3.36% | same file |
| L_gbt material failure / paired difference | 0.0206; R_thr − L_gbt = −0.0005 [−0.0273, +0.0159] | `final_policies_5c_test.csv`; `final_paired_vs_rthr_5c_test.csv` |
| Raw disagreement, R_thr vs L_gbt | 0.219 vs 0.065; paired 0.154 [0.028, 0.391] | same files, `failure`, `diff_fail` |
| R_thr material failure, 5B test | 0.0877 | `final_policies_5b_test.csv` |
| R_cat vs R_thr, 5B test | paired (R_thr − R_cat) 0.024 [0.011, 0.037] | `final_paired_vs_rthr_5b_test.csv` |
| Always-A3 material failure | 0.0588 = 1/17 (gate-free design share) | `final_policies_5c_test.csv`; `p5c_design.csv` |
| Validation material failure, R_thr / L_gbt / L_tree3 | 0.0204 / 0.1071 / 0.1753 | `p7_policies_5c_val.csv` |
| Gate-probe-only ablation | material 0.0178 (5C val), 0.0943 (5B val); raw 0.252 | `ablation_probes.csv` |
| Probe break-even | 644.5–685.1 transactions (5C), 79.6–83.1 (5B) | `ablation_probe_cost.csv` |
| Residual association (G3B / G3C val) | MI 0.078 nats, p = 0.001 / MI 0.038 nats, p = 0.0005 | `p5b_metadata.json`; `p5c_metadata.json` |
| Readout-probe validity | Spearman 0.999 vs true mean readout error; gate contraction vs thermal severity −0.12 | `p5c_probe_validity.csv` |
| AUPRC change under gate noise | ≤ 0.003 (every CI contains 0) | `p3b_exact_metrics.csv` |
| Brier, clean → combined-high | 0.0093 → 0.121 | `p3b_exact_metrics.csv` |
| Phase 4 Brier restorations (1,024 shots) | 0.053 → 0.011; 0.055 → 0.038; 0.122 → 0.054; 3× shots 0.121 | `p4_summary.csv` |

The full claims audit behind these numbers checked 186 claims across the repository documents.
