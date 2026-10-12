# Reproducibility guide

Everything in `results/tables/` and `results/figures/` can be regenerated from:
- the pinned environment;
- the public dataset;
- the commands below.

Every reported run records the following in `results/raw/<experiment>/<run_id>/manifest.json`: git commit, config hash, package versions, hardware, seeds and output hashes. The large replicate-level datasets are gitignored, but their content hashes are committed.

## 1. Environment

| Item | Value |
|---|---|
| Tooling | [`uv`](https://docs.astral.sh/uv/); Python 3.12 (`.python-version`); every dependency locked in `uv.lock` (Qiskit 2.5.2, Qiskit Aer 0.17.2, numpy, scipy, pandas, scikit-learn, pydantic) |
| Hardware used | Apple M5 Pro: 15 cores (5 performance + 10 efficiency), 24 GB RAM. CPU only. |

```bash
uv sync --frozen
uv run ruff check . && uv run ruff format --check .
uv run pytest                 # fast suite (~2.5 min)
uv run pytest -m slow         # real-data reproduction tests (~30 min; need the data below)
```

## 2. Data

ULB / Kaggle credit-card fraud. Never committed. Use your own Kaggle credentials.

```bash
uvx kaggle datasets download -d mlg-ulb/creditcardfraud -p data/raw && unzip -o data/raw/creditcardfraud.zip -d data/raw
uv run python scripts/prepare_data.py     # verifies SHA-256 76274b69…, deduplicates, group-aware partitions, preprocessing
```

Partition row-id hashes and the preprocessing artifact hash are committed in `results/tables/ulb_v1_phase1_metadata.json`. Every later phase verifies them.

## 3. Phases in order

Each phase is pre-registered in `docs/PREREG_*.md`. Its results are summarized in `docs/EXPERIMENT_PROTOCOL.md` §2.7–3.14.

| Phase | Command(s) | Approx. time | Key outputs |
|---|---|---|---|
| 2 classical baselines | `scripts/run_classical_baselines.py`, `scripts/make_phase2_figures.py` | 1.5 min | `phase2_*` |
| 3A first VQC | `scripts/train_vqc_3a.py`, `scripts/make_phase3a_figures.py` | 1 min | `phase3a_*`, frozen VQC |
| 3A-R repair | `scripts/select_vqc_3ar.py`, `scripts/evaluate_vqc_3ar.py`, `scripts/make_p3ar_figures.py` | 3 min | `p3ar_*`, frozen P3A-R |
| 3B noise | `scripts/run_noise_3b.py`, `scripts/make_p3b_figures.py` | 3 min | `p3b_*` (G1) |
| 4 mitigation | `scripts/run_mitigation_4.py`, `scripts/make_p4_figures.py` | 6 min | `p4_*` (G2) |
| 5A model pool | `scripts/build_pool_5a.py`, `scripts/make_p5a_figures.py` | 4 min | `artifacts/model_pool/` (manifest SHA-256 `90f09562…`) |
| 5B categorical counterfactuals | `caffeinate -i uv run python scripts/build_counterfactual_5b.py`, then `scripts/analyze_counterfactual_5b.py`, `scripts/make_p5b_figures.py` | 1.8 h + 1 min | `p5b_*` (G3B); test split sealed |
| 5C continuous counterfactuals | `caffeinate -i uv run python scripts/build_mixed_5c.py`, then `scripts/analyze_mixed_5c.py`, `scripts/make_p5c_figures.py` | 6.8 h + 2 min | `p5c_*` (G3C); test split sealed |
| 7 validation comparison | `scripts/phase7_validate.py` | 15 s | `p7_*`, frozen comparator fingerprints |
| Final one-time test | `scripts/final_test.py` (refuses unless the protocol and freeze are committed and pushed; unlocks once) | 20 s | `final_*` (H1–H4) |
| Ablations (validation only) | `scripts/ablations.py` | 1 min | `ablation_*` |
| Final figures | `scripts/make_final_figures.py` | seconds | `final_a_policies.png`, `final_b_structures.png` |

**How to run the scripts:** prefix each command with `uv run python`.
- *Reported* runs refuse a dirty git tree. Use `--dev` for exploratory reruns.
- Builds write isolated per-model files and merge them deterministically.

## 4. Verifying instead of rerunning

| Check | Command | What it proves |
|---|---|---|
| Byte-for-byte reproduction | `uv run pytest -m slow` | Phases 1, 2, 3A, 3A-R, 3B, 4 and 5A regenerate every committed deterministic output and frozen model byte for byte. 5B and 5C partially regenerate their stored datasets row for row and reproduce their reports and cost tables. The final evaluation reproduces its tables (`--reproduce`, a logged sealed read). |
| Frozen pool | (part of the slow suite) | `load_pool` verifies the manifest hash, every artifact hash and every rebuilt circuit hash |
| Sealed tests | `results/tables/p5b_lockbox_manifest.json`, `p5c_lockbox_manifest.json` | Content hashes (`c9ecc091…`, `91b0a5b9…`), verified at the single unlock |
| Unlock audit | `results/lockbox/UNLOCK_RECORD.json`, `ACCESS_LOG.jsonl` (gitignored; copied into `final_metadata.json`) | One unlock at 2026-10-08T21:28:24Z on `5e09c85`; every later read logged |
| Figures | `make_*_figures.py` | Regenerate from committed tables only; output is byte-identical on the reference machine |

## 5. Rules that keep results valid

- **The sealed test cannot be re-spent.** Never delete `results/lockbox/UNLOCK_RECORD.json` and rerun the final evaluation as a "new" test. The guard refuses a second unlock, and reproduction reads are logged.
- **Registered datasets stay on one platform.** Floating-point libraries differ slightly across machines, so a registered dataset is never mixed across platforms. Cross-machine reruns are reproduction checks, judged against documented tolerances (`docs/REMOTE_COMPUTE.md` §4).
- **What is never committed:** credentials, raw or processed transaction data, replicate-level datasets and lockbox files. This is enforced by `.gitignore` and `tests/test_repo_hygiene.py`.

## 6. Optional remote compute

See `docs/REMOTE_COMPUTE.md`: a Colab notebook, guarded transfer, a benchmark, and the recommendation to stay local.
