# Contribution Log

Record **actual** work as it happens, not intended work [RR §Team-contribution record].

- One dated section per working day.
- Each team member edits their own entries.
- AI-tool work is recorded in [`ai_tool_log.md`](ai_tool_log.md) and summarized here.

## 2026-10-06

### Mayank Kumar Pokhriyal
- Supplied the Q-TRACE research report (`docs/research/deep-research-report.md`) to the repository.
- GitHub repository `MayankKumarPokhriyal/q-trace` (private) created on this account and set as `origin`.
- Reviewed the Phase 0 planning documents.
- Decided blocking questions Q1–Q3 and amendments A01–A14 (see `DECISIONS.md`).
- Corrected the Oct 13 timeline and set the raw resource-cost requirement.

### Tushar Poonia
- *(no entries recorded yet — to be filled in by Tushar)*

### AI tools (summary; details in `ai_tool_log.md`)
- Claude Code: Phase 0 planning documents, then the Phase 0 scaffold, tests and smoke test, implemented under the PI's approval.

## 2026-10-07

### Mayank Kumar Pokhriyal
- Accepted Phase 0.
- Decided H3 condition 3, O22, the continuous-noise and finite-shot deferrals, O21 = option B, the duplicate-handling policy, and the Phase 1 scope.
- Provided Kaggle credentials locally, outside the repository.

### Tushar Poonia
- *(no entries recorded yet)*

### AI tools
- Claude Code: Phase 1 implementation (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 1 review)
- Accepted Phase 1.
- Decided O23 (group-aware split) and the Phase 2 scope: scikit-learn only, VQC partitions only, regimes, representations, metrics, outputs.

### AI tools (Phase 1 correction and Phase 2)
- Claude Code: O23 group-aware split and access guard; Phase 2 classical baselines (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 2 review)
- Approved Phase 2.
- Decided the provisional Phase 3A choices: O01 parity readout; O02 top-4; O03 robust symmetric clip ±3 encoding; O17 4:1 subset; COBYLA for the pilot.

### AI tools (Phase 3A)
- Claude Code: clean VQC implementation, diagnostics, figures, tests (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 3A review)
- Accepted Phase 3A as a pilot (preserved as P3A-original).
- Ordered the pre-registered Phase 3A-R repair and its constraints.
- Set the O07 pilot (1,024 × 20) and kept O20 open.

### AI tools (Phase 3A-R)
- Claude Code: pre-registration, folds, repair study, two-stage execution, figures, tests (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 3A-R review)
- Approved Phase 3A-R; P3A-R became the Phase 3B base model.
- Ordered the pre-registered Phase 3B controlled-noise characterization and its constraints: no mitigation or controller; `vqc_val` only; synthetic asymmetric readout labelling; G1 stop rule.

### AI tools (Phase 3B)
- Claude Code: pre-registration, noise engine, E08 validation, finite-shot pilot, A13/G1 diagnostics, figures, tests (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 3B review)
- Accepted Phase 3B as a CONDITIONAL PASS.
- Ordered the pre-registered Phase 4 mitigation characterization and its constraints. O07 resolved: 1,024 / 4,096 arms. O14 resolved: benefit vector. O15: no pool yet. Defined the resource-matched baseline requirement and G2.

### AI tools (Phase 4)
- Claude Code: pre-registration, readout/ZNE/cost implementation, validation, finite-shot study, two-stage bootstrap, G2, figures, tests (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 4 review)
- Accepted Phase 4 as G2 = CONDITIONAL PASS.
- Ordered the pre-registered Phase 5A independent VQC pool and its constraints: VQC partitions only; clean qualification only; ≥ 40 models; G3A; no mitigation or controller.

### AI tools (Phase 5A)
- Claude Code: pre-registration, pool code (representations, encoders, ansatze, readouts), training and qualification, freeze and manifest, diversity, power, runtime projection, figures, tests (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 5A review)
- Accepted Phase 5A (G3A PASS).
- Ordered Phase 5B with the structure-level split, A04 controller panels, A4 extra shots as a real action, Brier primary, observable probes only, leakage audit and the G3B gate.

### AI tools (Phase 5B)
- Claude Code: registry tightening (A15), pre-registration with code, probes, counterfactual generation, lockbox, registered analysis, figures, tests (see `ai_tool_log.md`).

### Mayank Kumar Pokhriyal (Phase 5B review and completion brief, 2026-10-08)
- Accepted the Phase 5B G3B FAIL.
- Issued the autonomous project-completion brief (`docs/AUTONOMOUS_PROJECT_COMPLETION_BRIEF.md`).
- Ordered Phase 5C: continuous mixed noise, residual-complexity gate, learned controller only if justified.

### AI tools (Phase 5C registration)
- Claude Code: Phase 5C design (split-plot LHS on the anchor-severity scale), registration, generation and analysis code, tests (see `ai_tool_log.md`).

### AI tools (Phase 5C execution, Phase 7, final evaluation, deliverables; 2026-10-08)
- **Claude Code:**
  - Phase 5C execution and analysis (G3C FAIL);
  - optional Colab infrastructure and benchmark;
  - Phase 7 and final-test protocol and code;
  - the single sealed-test evaluation (H1–H4 supported);
  - ablations;
  - final report, manuscript, status, reproducibility guide and presentations.
- **Background research agents** checked the literature and the Aer GPU / Colab facts.
- Everything awaits PI review (see `ai_tool_log.md`).
