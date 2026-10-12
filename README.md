# Q-TRACE

**Cost-aware selective quantum error mitigation for noisy quantum machine-learning fraud detection.**

Q-TRACE was designed as a decision layer on top of a *frozen* 4-qubit variational quantum classifier (VQC) trained for credit-card fraud detection (ULB dataset). The design that was tested: for each batch, a learned controller would

1. run cheap, label-free probes;
2. predict the counterfactual change in fraud-detection performance that each action would produce (None, Readout, ZNE, Combined, or extra shots);
3. choose an action while accounting for the extra quantum resources it would spend.

The project tested this design against Never, Always, simple probe-threshold rules, unmitigated execution at an equal total shot budget, and an evaluation-only oracle. A finding that a simple rule matches the learned controller was registered in advance as a reportable result, and that is what was found: two pre-registered gates found no material residual for a learned controller, so none was trained, and fixed learned comparators did not beat the rule on the sealed test.

> **Status: research complete (2026-10-08).** The final held-out evaluation was pre-registered, and the sealed test was opened once. Its conclusion: **use a simple probe rule; a learned controller is unnecessary.**
> - **The rule:** one readout-probe and one gate-probe threshold per shot budget.
> - **On unseen model structures:** it matches the cost-aware Oracle's reliability (Brier within 0.03%) at 0.6% more shots. Only 2% of its choices are material mistakes, under continuous joint noise; 8.8% under categorical noise.
> - **Fixed learned comparators** (logistic regression, decision tree, gradient boosting) at best tie it on material mistakes, and generalize worse to an unseen readout type. Some agree with the Oracle more often, but the rule's extra disagreements are not material; the test spans only 4 structures.
> - **Mitigation itself** repairs calibration and threshold decisions, not discrimination (AUPRC). Extra shots never substitute for it.
>
> **No quantum-advantage claim.**

## Documents

| Document | Purpose |
|---|---|
| [`docs/PROJECT_SPEC.md`](docs/PROJECT_SPEC.md) | Scope, formal decision problem, hypotheses, architecture, schema, roadmap |
| [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) | Scientific procedure; frozen as `protocol-v1.0` before the locked evaluation |
| [`docs/DECISIONS.md`](docs/DECISIONS.md) | Every fixed, accepted, deferred and open decision, with evidence |
| [`docs/LITERATURE.md`](docs/LITERATURE.md) | Reference register: all [RR] references located and checked against their abstracts (AGENT-CHECKED; team confirmation pending), plus the novelty boundary |
| [`docs/research/deep-research-report.md`](docs/research/deep-research-report.md) | Original research report, unmodified. SHA-256 `e1a8d0714a73b96ce67ddd05b9bd3108b65e040f6c1fe8311a8e17d80b1274f1` |
| [`docs/FINAL_STATUS.md`](docs/FINAL_STATUS.md) | **Start here:** final answer, hypotheses, final test results, limitations, readiness |
| [`deliverables/`](deliverables/) | **Academic submission package:** manuscript (PDF + LaTeX), capstone report (PDF + DOCX), Oct 13 and final decks, speaker notes and Q&A, figures with provenance, submission plan and venue options |
| [`docs/FINAL_REPORT.md`](docs/FINAL_REPORT.md), [`docs/MANUSCRIPT.md`](docs/MANUSCRIPT.md) | Final research report; paper-style manuscript |
| [`docs/REPRODUCIBILITY.md`](docs/REPRODUCIBILITY.md) | How to reproduce every result |
| [`docs/presentations/`](docs/presentations/) | Capstone and WIP presentation content |
| [`docs/REMOTE_COMPUTE.md`](docs/REMOTE_COMPUTE.md) | Optional Colab remote-compute workflow: audit, setup, guarded transfer, benchmark, recommendation |
| [`docs/contribution_log.md`](docs/contribution_log.md), [`docs/ai_tool_log.md`](docs/ai_tool_log.md) | Who did what |

## Reproduce

You need [`uv`](https://docs.astral.sh/uv/). Python 3.12 is pinned in `.python-version`, and all dependency versions are locked in `uv.lock`.

```bash
uv sync --frozen                         # create .venv from the lockfile
uv run pytest                            # fast suite (~15 s); slow/qpu tests are opt-in
uv run ruff check . && uv run ruff format --check .
uv run python scripts/smoke_test.py      # 4-qubit density-matrix noise smoke test
```

The smoke test writes `results/raw/smoke_env/<run_id>/{summary.json,manifest.json}`. That directory is gitignored. The manifest records the git commit, the config hash, the package versions, the hardware and the seeds.

### Data (Phase 1)

The ULB dataset is **never committed**. Obtain it once into `data/raw/`, which is gitignored. You need your own Kaggle credentials in `~/.kaggle`; never put them in this repository.

```bash
uvx kaggle datasets download -d mlg-ulb/creditcardfraud -p data/raw
unzip -o data/raw/creditcardfraud.zip -d data/raw
# or place creditcard.csv manually at data/raw/creditcard.csv
```

The file must have SHA-256 `76274b691b16a6c49d3f159c883398e03ccd6d1ee12d9d8ee38f4b4b98551a89`, recorded in `configs/datasets/ulb_v1.yaml`. The pipeline refuses any other file.

```bash
uv run python scripts/prepare_data.py   # reported run: needs a clean git tree (use --dev otherwise)
uv run pytest -m slow                   # real-data checks: checksum, sanity, rerun identity, table reproduction
```

**Outputs:**
- `data/processed/ulb_v1/` (gitignored): partitions, preprocessed features, fitted parameters, audit;
- `results/tables/ulb_v1_*` (committed): aggregate counts only, deterministic.

### Classical baselines (Phase 2)

```bash
uv run python scripts/run_classical_baselines.py   # ~1.5 min; reported mode needs a clean tree (--dev otherwise)
uv run python scripts/make_phase2_figures.py       # figures from the committed tables
```

This reads only `vqc_train` and `vqc_val`. It writes aggregate tables to `results/tables/phase2_*` (committed) and per-row scores to `results/raw/` (gitignored).

### Clean VQC (Phase 3A)

```bash
uv run python scripts/train_vqc_3a.py      # ~1 min; trains, retrains (reproducibility), freezes, evaluates
uv run python scripts/make_phase3a_figures.py
```

The frozen model is committed at `artifacts/frozen_vqcs/vqc3a_top4_ra1.json`.

### Pre-registered VQC repair (Phase 3A-R)

The registration is [`docs/PREREG_P3AR.md`](docs/PREREG_P3AR.md).

```bash
uv run python scripts/select_vqc_3ar.py     # ~3 min; vqc_train ONLY: CV, selection, final training, freezing
uv run python scripts/evaluate_vqc_3ar.py   # one-time vqc_val evaluation of the frozen selection
uv run python scripts/make_p3ar_figures.py
```

The frozen repaired model is committed at `artifacts/frozen_vqcs/vqc3ar_e3-r2-par.json`.

### Controlled-noise characterization (Phase 3B)

The registration is [`docs/PREREG_P3B.md`](docs/PREREG_P3B.md); results are in [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) §3.9.

```bash
uv run python scripts/run_noise_3b.py       # ~3 min; vqc_val ONLY: exact noise, negative control, E08, finite-shot pilot, G1
uv run python scripts/make_p3b_figures.py   # figures A-E from the committed p3b_* tables
```

### Mitigation characterization (Phase 4)

The registration is [`docs/PREREG_P4.md`](docs/PREREG_P4.md); results are in [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) §3.10.

```bash
uv run python scripts/run_mitigation_4.py   # ~6 min; vqc_val ONLY: exact stage, checks, finite-shot study, G2
uv run python scripts/make_p4_figures.py    # figures A-E from the committed p4_* tables
```

### Independent VQC pool (Phase 5A)

The registration is [`docs/PREREG_P5A.md`](docs/PREREG_P5A.md); results are in [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) §3.11.

```bash
uv run python scripts/build_pool_5a.py      # ~4 min compute; vqc_train fit + vqc_val qualification; freezes the pool
uv run python scripts/make_p5a_figures.py   # figures A-D from the committed p5a_* tables
```

The frozen pool is `artifacts/model_pool/` (one JSON per model + `p5a_pool_manifest.json`).

### Final evaluation (Phase 7, one-time sealed test) and ablations

The protocol is [`docs/PREREG_FINAL.md`](docs/PREREG_FINAL.md).

```bash
uv run python scripts/phase7_validate.py   # learned comparators on 5C train; validation comparison; freeze
uv run python scripts/final_test.py        # ONE-TIME sealed test (refuses unless protocol + freeze are pushed)
uv run python scripts/ablations.py         # validation-only ablations
uv run python scripts/make_final_figures.py
```

### Continuous mixed-noise study (Phase 5C)

The registration is [`docs/PREREG_P5C.md`](docs/PREREG_P5C.md).

```bash
caffeinate -i uv run python scripts/build_mixed_5c.py   # ~7 h on 15 cores; 68 noise points x 3 budgets x 20 reps
uv run python scripts/analyze_mixed_5c.py                # registered analysis + G3C (train/val only)
```

The replicate-level dataset is gitignored (`results/processed/phase5c/`); the test split is sealed in `results/lockbox/phase5c/`.

### Cross-model counterfactual dataset (Phase 5B)

The registration is [`docs/PREREG_P5B.md`](docs/PREREG_P5B.md); results are in [`docs/EXPERIMENT_PROTOCOL.md`](docs/EXPERIMENT_PROTOCOL.md) §3.12.

```bash
caffeinate -i uv run python scripts/build_counterfactual_5b.py   # ~2 h on 15 cores; ctrl_* panels per A04
uv run python scripts/analyze_counterfactual_5b.py                # registered analysis (train/val only)
uv run python scripts/make_p5b_figures.py                         # figures A-F
```

The replicate-level dataset is gitignored (`results/processed/phase5b/`); the test split is sealed in `results/lockbox/phase5b/`.

## Repository rules

**Never committed.** These are enforced by `.gitignore` and `tests/test_repo_hygiene.py`:
- datasets;
- raw or processed results;
- caches;
- virtual environments;
- credentials, tokens and `.env` files.

**Reported numbers** come only from committed configs on a clean git tree, with a run manifest.

**Commits and pushes**
- Each development phase ends in small `phase-N:` commits.
- Pushes happen only after that phase's validation passes.
- No force-pushes.
