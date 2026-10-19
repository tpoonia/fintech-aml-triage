# Figure provenance: semester decks

Every quantitative figure on a slide is drawn from committed tables in `results/tables/`. Schematics are labeled "illustrative" or "schematic" on the slide and contain no project data.

## Semester figures (`_system/figures/`, made by `_system/make_semester_figures.py`)

| File | Content | Source | Kind | Used in |
|---|---|---|---|---|
| `circuit_p3ar` | The frozen P3A-R circuit: ZZ map, RealAmplitudes with 2 layers, parity readout; 12 parameters, 18 CX | `configs/repair/p3ar_v1.yaml`, `configs/vqc/vqc3a_top4_ra1.yaml`, `p5a_pool_metrics.csv` (anchor: 18 CX, 12 parameters) | exact schematic | Oct 13 (3), Dec 8 (6) |
| `circuit_generic` | Generic variational-classifier template | literature (Havlíček 2019; Schuld 2020) | generic schematic | Sep 29 (3) |
| `noise_concept` | Expectation-value decay and probability contraction | illustrative global-depolarizing model | illustrative, no data | Sep 15 (2) |
| `zne_schematic` | Folding and linear extrapolation | illustrative values | illustrative, no data | Sep 15 (3), Sep 29 (4), Oct 27 (4) |
| `baselines_auprc` | Validation AUPRC with 95% CI: classical (30 features; VQC inputs) and VQC (first, repaired) | `phase2_classical_metrics.csv` (a-full, draw 0, full), `p3ar_validation_comparison.csv` | data | Oct 13 (2), Dec 8 (B4) |
| `encoding_repair` | Distinct fraud inputs, frauds clipped on all features, AUPRC: encodings e0 and e3 | `p3ar_encoding_diagnostics.csv`, `p3ar_validation_comparison.csv` | data | Oct 13 (4), Dec 8 (B4) |
| `pool_auprc` | 64 models by structure, colored by split | `p5a_pool_metrics.csv`, `p5b_split.csv` | data | Nov 10 (3), Dec 8 (12) |
| `workflow_slide` | Pre-registered workflow with gate outcomes; corrected note ("from Phase 3A-R on") | gate outcomes as recorded in `p3b_metadata.json`, `p5b_metadata.json`, `p5c_metadata.json`, `final_metadata.json` | schematic | Dec 8 (10) |
| `cost_reliability_slide` | Material failure vs shots ÷ Oracle, 5C sealed test, with off-scale policies listed | `final_policies_5c_test.csv` (arm `all`) | data | Nov 24 (4), Dec 8 (15) |

## Reused figures

| File | Made by | Used in |
|---|---|---|
| `deliverables/figures/fig3_noise_effects` | `deliverables/figures/make_figures.py` | Oct 13 (5), Oct 27 (3), Dec 8 (8) |
| `deliverables/figures/fig4_mitigation` | same | Oct 27 (5), Dec 8 (9) |
| `deliverables/figures/fig5_preferred_actions` | same | Nov 10 (4), Dec 8 (13) |
| `deliverables/figures/fig7_learned_vs_rule` | same | Nov 24 (3) |
| `deliverables/figures/fig8_final_heldout` | same | Nov 24 (2), Dec 8 (14) |
| `deliverables/figures/fig9_probe_ablation` | same | Dec 8 (B3) |
| `results/figures/final_b_structures.png` | `scripts/make_final_figures.py` | Dec 8 (B1) |
| `results/figures/p5c_b_preferred_map.png` | `scripts/make_p5c_figures.py` | Dec 8 (B2) |

The provenance of the publication figures is in `deliverables/figures/FIGURES.md`. Numbers quoted in slide text are listed per slide in each folder's `speaker_notes.md`, under "Sources".
