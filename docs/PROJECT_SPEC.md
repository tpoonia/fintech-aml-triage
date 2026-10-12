# Q-TRACE — Project Specification

**Q-TRACE: cost-aware selective quantum error mitigation for noisy quantum machine-learning fraud detection** (working scope, frozen by the PI 2026-10-06; `F23`).

| | |
|---|---|
| **Status** | v0.15. **Research complete (2026-10-08): use the simple probe rule; a learned controller is unnecessary (H1–H4 supported on the sealed held-out test).** Deliverables: `FINAL_REPORT.md`, `MANUSCRIPT.md`, `FINAL_STATUS.md`, `REPRODUCIBILITY.md`, `presentations/`. |
| **Source of research intent** | [`docs/research/deep-research-report.md`](research/deep-research-report.md), cited as **[RR]**. **SHA-256 `e1a8d0714a73b96ce67ddd05b9bd3108b65e040f6c1fe8311a8e17d80b1274f1`**. Moved unchanged from the repository root (Q2). The checksum is enforced by `tests/test_repo_hygiene.py`. |
| **Companions** | [`EXPERIMENT_PROTOCOL.md`](EXPERIMENT_PROTOCOL.md): scientific procedure.<br>[`DECISIONS.md`](DECISIONS.md): decision register (`Q`/`F`/`E`/`O`/`A`).<br>[`LITERATURE.md`](LITERATURE.md): reference verification. |
| **Precedence** | [RR] < accepted entries in `DECISIONS.md`. When this spec and [RR] disagree without a recorded decision, [RR] wins. |

---

## 1. What Q-TRACE is

Q-TRACE is a **decision layer for quantum error mitigation (QEM)** on a *frozen* variational quantum classifier (VQC) used for credit-card fraud detection.

For each operational context — a frozen VQC, a noise environment, a shot budget and a transaction batch — it:

1. runs a cheap, **label-free probe**;
2. predicts the *counterfactual* change in downstream fraud-detection performance that each mitigation action would produce relative to no mitigation;
3. selects one action, accounting for the quantum resources that action, *and the probe*, consume.

Zero-noise extrapolation (ZNE) and readout mitigation are used as established techniques. Q-TRACE does not propose a new QEM method.

**Out of scope:**
- quantum-advantage claims for fraud detection;
- a new QEM algorithm;
- an LLM agent as the scientific contribution;
- a production fraud system.

## 2. Research question

Verbatim from [RR §Precise research question]:

> Can model-, circuit-, and noise-specific information predict the counterfactual downstream benefit of quantum error mitigation for a VQC-based fraud detector well enough to select a mitigation strategy under a resource constraint and achieve a better fraud-performance–cost trade-off than never mitigating, always mitigating, or using a fixed noise threshold?

Q1 confirmed that this fraud-specific, four-action formulation supersedes the earlier generic QML (Iris/QM9/WDBC) and binary-mitigation framing. Binary None-vs-ZNE survives only as an ablation.

## 3. Formal decision problem

| Symbol | Definition |
|---|---|
| Context $c=(m,\nu,s,b)$ | $m$: frozen VQC.<br>$\nu$: noise-parameter vector.<br>$s$: shots per circuit.<br>$b$: transaction batch. |
| Actions $\mathcal A$ | {None, Readout, ZNE, Combined}. PEC is exploratory only (`F03`). |
| Probe $P(c)$ | A cheap, **label-free** execution of the frozen VQC on the current context, run *before* the decision (`A01`). Its size is not frozen (`O19`). |
| Decision information $X$ | Registry-approved features from (i) model, circuit, noise and shot metadata and (ii) the probe output (`configs/features/registry.yaml`). |
| Outcome $M(c,a)$ | Fraud metric on batch $b$ under action $a$. AUPRC is the provisional principal metric (`F08`); further metrics per `A03`. |
| Benefit $\Delta_a(c)$ | $\mathbb E_{\text{shots}}[M(c,a)-M(c,\text{None})]$: the expectation is over shot noise (`O10`). |
| Resources $R_a(c)$ | Raw counts, never collapsed (`F25`): probe, task, mitigation and calibration **executions and shots**; simulator/QPU execution time; wall-clock time (separately). |
| Cost $C_a(c)$ | A cost *function* of $R_a(c)$, chosen later (`O08`). The probe's resources are charged to every policy that uses a probe. |
| Predictor | $f_a(X)\approx\Delta_a(c)$, with $f_\text{None}\equiv0$. |
| Policies | Utility form $\arg\max_a[f_a(X)-\lambda C_a]$, or the budget-constrained form [RR §Two decision formulations]. |
| Oracle | Chooses with realized outcomes from an **independent** replicate; evaluation only (`A08`). |

**The decision unit is a batch** (AUPRC is set-level; labels arrive late).

### 3.1 Probe-before-decision (`A01`)

```text
frozen VQC ──► probe execution (cheap, label-free) ──► decision-time features X
                                                          │
                                                          ▼
                                    Q-TRACE decision: None | Readout | ZNE | Combined
                                                          │
                                                          ▼
                                           task execution (+ mitigation work)
```

The probe never sees ground-truth labels, which the schema enforces with `ProbeConfig.uses_labels: false`.

Its executions and shots are recorded as `probe_*` resources and counted in Q-TRACE's total cost. Policies that do not probe (Never, Always, fixed threshold) are not charged for one.

Still open (`O19`):
- how many transactions and shots the probe uses;
- whether probe outputs may be reused in the task execution.

## 4. Hypotheses

Thresholds are provisional, **never chosen post hoc**, and frozen after the pilot and before the locked evaluation (`F22`, `O12`).

| ID | Hypothesis (corrected where noted) |
|---|---|
| **H1** Heterogeneity (`A09`) | The expected benefit $\mathbb E[\Delta_a\mid c]$ varies across contexts beyond within-context shot-replicate variance, and the best action $a^*(c)$ is not constant. ([RR]'s $\operatorname{Var}(\Delta M_a\mid X)>0$ was the wrong quantity; see `DECISIONS.md` §A09.) |
| **H2** Predictability | On unseen models, $f_a$ beats the constant and noise-only predictors (provisional: ≥10% relative MAE reduction). |
| **H3** Selective mitigation (`A10`) | Q-TRACE (1) is non-inferior to the high-resource reference within a pre-registered ε, **and** (2) uses statistically and meaningfully fewer total resources *including its probe*, **and** (3) the reference materially beats Never. Otherwise H3 is **not applicable** for that condition and is reported as such. All three conditions confirmed by the PI. |
| **H4** Learned policy | $U_{QT}>U_{Threshold}$ with the paired 95% CI excluding 0, against a threshold rule tuned fairly on controller-training/validation data (`A11`). This is the most important hypothesis. |
| **H5** Oracle recovery | $R=\frac{U_{QT}-U_{Never}}{U_{Oracle}-U_{Never}}$ as a ratio of sums, with an independent-replicate oracle (`A08`). Aspirational target ≥ 0.8. |

**If a fixed threshold matches Q-TRACE, that is a result and will be reported.**

## 5. Scope

| Tier | Contents |
|---|---|
| **Oct 13 WIP** (`F24`) | ULB data → leakage-safe preprocessing → classical sanity baseline → **one** functioning, reproducible clean 4-qubit VQC result. No model pool, no noise sweep. |
| **Core (December)** | [RR] VQC families (2 ansätze × 2 depths) with a configurable seed pool (`A06`); 4 noise families × 3 severities, plus asymmetric readout (`A07`) and backend snapshots; 4 actions; probe; Q-TRACE-S; all baselines including resource-matched None (`A02`); oracle; ablations; held-out models and noise. |
| **Deferred** | Architecture diversity and continuous noise sampling (`A05`) are revisited after the runtime benchmark and first heterogeneity results. |
| **Extension** | 6 qubits, BankSim, IBM QPU validation, Q-TRACE-A, PEC, quantum controller, noise-aware training. Only after gates G1–G4. |

## 6. Claim boundary and literature

**Allowed contribution statement** [RR §Novelty boundary]: task-level QEM orchestration for severely imbalanced quantum fraud classification. Q-TRACE estimates the counterfactual downstream benefit and resource cost of candidate mitigation actions per model/noise context, then selects an intervention under an explicit execution budget. It is evaluated against static mitigation, threshold rules and an oracle on held-out models and noise.

**Prohibited claims:** any "first …" claim (adaptive QEM, cost-aware QEM, adaptive QEM for VQCs, multi-action QEM agent) [RR §Literature matrix].

**Literature: UNVERIFIED.** Every [RR] citation is an unresolved `citeturn…` token. Verification is handled by a separate research/project-guidance workflow (Q3). Tracking is in [`LITERATURE.md`](LITERATURE.md). Tokens are never repaired or inferred. **No reference is cited in slides or the paper until it is verified there.**

## 7. Separation of concerns and leakage rules

```text
OFFLINE label generation (labels allowed)                 DECISION TIME (no labels of the current batch)
data → split → preprocess → VQC train → freeze             probe(c) ──► X (registry features) ──► f_a(X) ──► policy ──► action
contexts × all actions × replicates  ──► outcomes, raw resources ──► Δ_a ──trains──► predictors
evaluation (policies, oracle, statistics) ◄── oracle lives only here
```

| Rule | Statement | Enforced by |
|---|---|---|
| R1 | `qtrace.features` and `qtrace.policies` must not import `qtrace.counterfactual` or `qtrace.evaluation`. The exception is `qtrace.policies.oracle`, which is evaluation-only. | `tests/test_import_boundaries.py` (AST check, absolute and relative imports) |
| R2 | Q-TRACE inputs must be declared `deployable` in `configs/features/registry.yaml` for the given controller. | `qtrace.features.assert_deployable`; `tests/test_feature_registry.py` (snapshot of the deployable set) |
| R3 | Never inputs (`A12`): model ID, seed IDs, noise-profile ID or family or severity, ground-truth labels, accuracy from ground truth, anything from post-mitigation outcomes. Clean validation performance measured **at freeze time** is allowed. | Registry `offline_only` status; schema forbids deployable identifiers, labels and outcomes |
| R4 | Controller training, validation and testing use disjoint *models* and disjoint *transaction partitions*: `ctrl_train`, `ctrl_val`, `ctrl_test` (`A04`, `F28`). No QEM observation is evaluated on `vqc_train`. | `DataRef.panel_partition` cannot be `vqc_train`; `ActionOutcome` maps meta-train/val/test to `ctrl_train`/`ctrl_val`/`ctrl_test`; the Phase 1 pipeline verifies zero overlap |
| R5 | The oracle selects and is scored on independent replicates (`A08`). Thresholds are never tuned on the test partition (`A11`). | `PolicyDecision` validators |
| R6 | Controller-test outcomes are lockboxed until the protocol is frozen. | `E14` (Phase 6) |

## 8. Repository architecture (as implemented in Phase 0)

```text
q-trace/
├── README.md                      # overview, reproduction commands, checksum, status
├── pyproject.toml / uv.lock       # uv-managed, locked environment (E01, E17)
├── .python-version                # 3.12
├── .gitignore                     # verified by tests/test_repo_hygiene.py (E20)
├── docs/
│   ├── PROJECT_SPEC.md  EXPERIMENT_PROTOCOL.md  DECISIONS.md  LITERATURE.md
│   ├── contribution_log.md        # actual dated work per team member
│   ├── ai_tool_log.md             # AI-tool usage record
│   └── research/deep-research-report.md   # [RR], unchanged
├── configs/
│   ├── datasets/ulb_v1.yaml       # dataset spec (no download yet)
│   ├── qml/pool_rr_v1.yaml        # [RR] 40-model pool definition (configurable, A06)
│   ├── noise/anchors_rr_v1.yaml   # [RR] 12 anchors; symmetric readout = negative controls (A07)
│   ├── noise/synthetic_asym_v1.yaml   # 3 synthetic asymmetric readout stress-test profiles (O20 open)
│   ├── noise_study/p3b_v1.yaml    # Phase 3B pre-registered study (PREREG_P3B.md)
│   ├── mitigation_study/p4_v1.yaml   # Phase 4 pre-registered study (PREREG_P4.md)
│   ├── model_pool/p5a_v1.yaml     # Phase 5A pre-registered pool (PREREG_P5A.md)
│   ├── counterfactual_study/p5b_v1.yaml   # Phase 5B pre-registered study (PREREG_P5B.md)
│   ├── noise/smoke.yaml           # smoke-test-only profile (asymmetric readout)
│   ├── mitigation/{none,readout,zne,combined}.yaml
│   ├── features/registry.yaml     # leakage registry (R2/R3)
│   ├── experiments/smoke_env.yaml # the only Phase 0 experiment
│   └── policies/                  # (Phase 8)
├── src/qtrace/
│   ├── config/      schemas.py (pydantic v2), loader.py (YAML, id resolution, duplicate-key guard)
│   ├── records/     manifest.py (RunManifest), observation.py (ActionOutcome), decision.py (PolicyDecision)
│   ├── features/    registry.py (FeatureRegistry, assert_deployable)
│   ├── utils/       hashing.py, seeds.py, provenance.py, smoke.py
│   ├── data/        ingest, duplicates, partition (group-aware), preprocess, subset, panels,
│   │                pipeline, access (phase-scoped partition guard), representation (Phase 1–2)
│   ├── classical/   models, runner, tables, pipeline (Phase 2; vqc_train/vqc_val only)
│   ├── evaluation/  metrics (fraud, calibration, ranking distortion), bootstrap (Phase 2)
│   ├── qml/         encoding, circuit, simulate (exact engine), model, phase3a, phase3a_outputs,
│   │                repair, repair_outputs (Phase 3A-R), pool, pool_study (Phase 5A)
│   ├── noise/       models, frozen, exact, shots, diagnostics, study (Phase 3B; vqc_val only)
│   ├── mitigation/  readout, zne, costs, study, outputs (Phase 4; vqc_val only)
│   ├── counterfactual/ pool_models, probes, generate, study, analysis, report, features (Phase 5B);
│   │                    mixed, mixed_generate, mixed_study, mixed_analysis, mixed_report (Phase 5C)
│   ├── controller/      learned (comparator policies), lockbox (one-time sealed-test unlock)
│   ├── remote/          optional Colab benchmark and guarded transfer (E62)
│   ├── execution/ policies/       # stubs: later phases
├── scripts/smoke_test.py          # Phase 0 environment/noise smoke test
├── scripts/prepare_data.py        # Phase 1 data preparation (reported mode needs a clean tree)
├── scripts/run_classical_baselines.py, make_phase2_figures.py   # Phase 2
├── scripts/train_vqc_3a.py, make_phase3a_figures.py             # Phase 3A
├── scripts/select_vqc_3ar.py, evaluate_vqc_3ar.py, make_p3ar_figures.py   # Phase 3A-R
├── scripts/run_noise_3b.py, make_p3b_figures.py                 # Phase 3B
├── scripts/run_mitigation_4.py, make_p4_figures.py              # Phase 4
├── scripts/build_pool_5a.py, make_p5a_figures.py                # Phase 5A
├── scripts/build_counterfactual_5b.py, analyze_counterfactual_5b.py, make_p5b_figures.py   # Phase 5B
├── tests/                         # 103 tests; markers: slow, qpu
├── notebooks/                     # exploration only; never the source of a reported number
├── results/tables/                # committed aggregates: ulb_v1_*, phase2_*, phase3a_*, p3ar_*, p3b_*, p4_*, p5a_*, p5b_*
├── results/figures/               # committed; raw/, processed/, lockbox/ are gitignored
├── artifacts/frozen_vqcs/         # committed frozen VQCs (parameters + provenance hashes); cache/ gitignored
├── artifacts/model_pool/          # Phase 5A frozen pool: one JSON per model + p5a_pool_manifest.json
└── data/                          # gitignored (created in Phase 1)
```

**Deviation from the v0.1 proposal.** Record schemas moved from `evaluation/` to a neutral `records/` package. Policies must be able to emit `PolicyDecision` records without importing `evaluation/`, which R1 forbids.

## 9. Environment (`E01`, `E15`–`E17`)

**Tooling**
- `uv` 0.10.3 with a committed `uv.lock`.
- Python **3.12.11**.
- Install with `uv sync --frozen`.
- Conda is not used.

**Locked core packages (Phase 0):**

| Package | Version |
|---|---|
| qiskit | 2.5.2 |
| qiskit-aer | 0.17.2 |
| numpy | 2.5.3 |
| scipy | 1.18.1 |
| pandas | 3.0.6 |
| pyarrow | 25.0.1 |
| scikit-learn | 1.9.1 |
| pydantic | 2.13.5 |
| pyyaml | 6.0.3 |
| matplotlib | 3.11.2 (added in Phase 2, `E27`) |

**Dev tools:** pytest 9.1.1, ruff 0.16.10.

**Phase-gated extras** are added only when their phase needs them, with a `DECISIONS.md` entry:
- xgboost (Phase 7; `libomp` is present on the development Mac);
- mitiq (optional, Phase 5);
- qiskit-ibm-runtime (Phase 10);
- qiskit-aer-gpu (Linux x86-64 only, and only after a benchmark).

**Development machine:** Apple M5 Pro, 15 cores, 24 GB, macOS (arm64). The CPU is used for simulation. Cloud use means `uv sync --frozen` on Linux.

**Secrets** (Kaggle and IBM tokens) live outside the repository and are covered by `.gitignore`.

## 10. Configuration system (`E03`, `E04`)

**Format and validation**
- YAML per component under `configs/<family>/`.
- Every family has a pydantic v2 schema: `extra="forbid"`, frozen.
- Duplicate YAML keys are rejected.

**References**
- Experiments reference components by id.
- The id inside a file must match its file name.
- `load_experiment(id)` returns a `ResolvedExperiment`.

**Hashing**
- `config_hash()` is the SHA-256 of canonical JSON (sorted keys; NaN rejected).
- `component_hashes()` gives per-component keys for stage caches.

**Encoded decisions:**
- `deduplicate_before_split: true` and `fit_on: train` are the only legal values (`A04`);
- `ProbeConfig.uses_labels: false` (`A01`);
- PEC requires `exploratory: true` (`F03`);
- ZNE factors must be odd, start at 1 and increase;
- noise profiles must be physical ($T_2\le2T_1$, invertible readout) and family-consistent;
- `ModelPoolConfig.seeds_per_architecture` has no upper bound (`A06`).

**Open decisions** are optional fields defaulting to `null`, with the decision ID in a comment.

**Seeds**
- Streams: `split`, `model`, `undersample`, `noise`, `shots`, `policy`, `bootstrap`.
- `derive_seed(master, stream, *key)` is SHA-256-based, type-tagged and length-prefixed. It is deterministic, stream-separated and order-independent.
- **Reported runs** must come from committed configs on a clean tree; `RunManifest` rejects anything else.

## 11. Experimental record schema (`qtrace.records`)

### 11.1 `RunManifest` (one JSON per run)

**Contents:**
- run id, experiment id, protocol version;
- `reporting` (dev or reported) and status;
- command;
- the full resolved config, its hash and the component hashes;
- git commit, branch and dirty flag;
- Python, platform and locked package versions;
- hardware;
- seeds;
- start and finish times;
- outputs, each with its SHA-256.

### 11.2 `ActionOutcome` (one experimental observation = context × action × replicate)

| Group | Fields |
|---|---|
| `provenance` | experiment and run ids, protocol version, commit, dirty flag, config hash, cache key, timestamp, Python/Qiskit/Aer/NumPy versions, platform |
| `data` | dataset SHA-256, split hash, panel id/hash, **panel partition** (`vqc_val`, `ctrl_train`, `ctrl_val` or `ctrl_test`; never `vqc_train`), panel size and fraud count, weighting scheme |
| `model` | model id, architecture, meta split, seed, parameter hash, observable, score link |
| `circuit` | qubits, depth, noisy 1-qubit and 2-qubit counts, basis, optimization level, transpile seed |
| `noise` | profile id, source (anchor / negative control / sampled / backend snapshot), p1, p2, `ro_p01`, `ro_p10`, T1, T2, gate times, seeds |
| `execution` | mode, shots, replicate, shot seed, probe enabled, simulator, backend |
| `action` | action, config hash, ZNE factors / extrapolator / allocation, readout method, clip policy |
| `resources` (`F25`) | probe, task, mitigation and calibration **executions and shots**; totals (validated to equal the sums); depth-weighted shots; simulator execution seconds; QPU execution seconds; **wall-clock seconds (separate)**. There is no single cost field. |
| `metrics` (`A03`, `A13`) | AUPRC, AUROC, recall, precision, F1, F2, precision@k, recall@precision, Brier, ECE, τ and its source; distortion versus clean: Spearman, Kendall, threshold-crossing fraction, mean absolute score shift; clip fraction; ties |
| pointers | predictions path and SHA-256 |

`to_flat_dict()` gives `group.field` columns for Parquet.

### 11.3 `PolicyDecision`

**Contents:**
- policy id and config hash;
- `is_oracle` and `deployable`;
- `tuned_on` (meta-train or meta-val only) and `evaluated_on`;
- context;
- chosen action and predicted benefits;
- λ or budget;
- selection and evaluation replicate ids (the oracle requires them to differ).

## 12. Reproducibility rules

1. Every reported number traces to a committed config, a clean commit and a run manifest.
2. Raw outputs are immutable. A re-run gets a new run id. Results are never deleted without approval.
3. Caches are keyed on config/upstream hashes plus a stage `CACHE_VERSION`, not on the git commit (`E06`).
4. The dataset is verified by SHA-256 before every pipeline run (Phase 1 onward).
5. Slides and figures are generated by scripts from `results/tables`, never from notebooks or by hand.
6. No datasets, raw outputs, caches, credentials, environments or machine files in git. Verified by tests.

## 13. Testing strategy

**Current suite:** `uv run pytest` runs 382 fast tests in about 2.5 min. `uv run pytest -m slow` runs 16 real-data tests, which skip when the gitignored data are absent. The slow tests cover:
- byte-for-byte reproduction of every committed Phase 1, 2, 3A, 3A-R, 3B, 4 and 5A deterministic output and frozen model;
- partial regeneration of the Phase 5B and 5C counterfactual datasets, row for row;
- reproduction of the 5B and 5C reports and cost tables;
- reproduction of the final one-time evaluation's tables (a logged sealed read after the single unlock).

| File | Covers |
|---|---|
| `test_config.py` | Shipped configs validate; unknown and duplicate keys rejected; id/file-name match; A04 constants; noise physics and family consistency; asymmetric readout; ZNE factor rules; action/block consistency; probe label ban; hash stability and sensitivity; pool scales to 200 models |
| `test_seeds.py` | Determinism, stream separation, collision resistance, order independence, invalid input |
| `test_records.py` | Synthetic observation validates and flattens; raw cost fields never collapsed; totals add up; exact/finite-shot rules; A04 partition rules; training-partition ban; probe/none consistency; metric ranges; oracle independence; tuned-on-test ban; reported-run clean-tree rule |
| `test_provenance.py` | Git state before first commit, clean and dirty; non-repository; environment and hardware capture; run ids; manifest round trip |
| `test_feature_registry.py` | Deployable snapshot; A12 inputs offline-only; no identifier-like deployable names; probe features label-free; `assert_deployable` accept and reject; Q-TRACE-A-only history; schema refusals |
| `test_import_boundaries.py` | R1 over `features/` and `policies/`, plus self-tests of the checker |
| `test_repo_hygiene.py` | [RR] checksum; 21 must-ignore and 10 must-track paths; no tracked file > 1 MB, secret or data path |
| `test_smoke_quantum.py` | 4-qubit density-matrix noise smoke test; closed-form readout-confusion check |
| `test_data_ingest_dedup.py` | Checksum mismatch; 7 schema violations; duplicate-audit counts on synthetic data with known structure; dedup policy (lowest row id, conflicting groups excluded); input-order independence; −0.0 normalization |
| `test_data_pipeline.py` | Largest-remainder allocation; all sanity checks; disjoint, exhaustive, exactly stratified partitions; dedup before split; determinism; six unrelated seed streams leave outputs unchanged; split seed changes them; changing non-training partitions cannot alter the preprocessing fit; scikit-learn `RobustScaler` parity; aggregate-only outputs |
| `test_data_subset_panels.py` | Subset drawn only from `vqc_train`; deterministic and seed-sensitive; limits; spec validation; panel validation, membership and hash; sampler is abstract |
| `test_data_real.py` (`slow`) | Real checksum; real sanity checks; rerun identity; committed tables reproduce byte for byte |
| `test_metrics_bootstrap.py` | Metrics equal scikit-learn (AP, AUROC, precision, recall, F1, F2, calibration bins for uniform and quantile); weights equal duplicated rows; max-F1 threshold with tie rule; hand-computed ECE; precision@k ties; recall@precision feasibility; ranking-distortion utilities; bootstrap keeps class counts, is seeded, and weights equal a materialized resample |
| `test_phase2_classical.py` | PCA equals scikit-learn; top-k follows `f_classif`; config validators; config cannot name controller partitions; runner coverage; injected signal detected; subsets within `vqc_train`; runner refuses other partitions; determinism; tables aggregate-only |
| `test_qml_3a.py` | Encoder formula, range, sign and train-only fit; circuit structure and transpiled statistics; exact engine equals `StatevectorEstimator` and Aer density-matrix; parity diagonal; readout orientation; BCE equals scikit-learn with clipping; training reduces loss and is deterministic; synthetic end-to-end run (selection reproduced, retrain/replay identical, non-constant scores); selection mismatch is fatal; controller rows refused; aggregate-only tables |
| `test_p3ar.py` | Group-aware stratified folds (deterministic, order-independent, groups intact); stored group keys equal recomputed ones; E0 equals the P3A-original encoder; first-qubit Z equals Qiskit; default observable unchanged; collision diagnostics; eligibility; selection and tie-break rules; 12-candidate cap; CV trains only on fold-train rows with identical restart seeds; selection code cannot read `vqc_val` (access + AST) |
| `test_p3ar_real.py` (`slow`) | Real-data 3A-R selection and one-time evaluation regenerate every committed output byte for byte |
| `test_noise_3b.py` | Registered matrix (15 conditions; synthetic AR labelling; negative controls); gate noise only on sx/x/cx; depolarizing-then-thermal composition equals the explicit channel; classical readout equals the Kronecker confusion, has the right p01/p10 orientation and matches Aer `ReadoutError` shots; frozen artifacts verified (wrong hash refused); Aer clean equals the exact engine; symmetric readout is an exact affine contraction and asymmetric is not; weighted ECE; paired bootstrap pairing and determinism; every A13 rule and the G1 PASS/CONDITIONAL/FAIL and trend rules; sampler counts, seeds and limits; χ² merging; E08 passes for two valid samplers and fails for a biased one; direct Aer shots agree and are reproducible |
| `test_p3b_real.py` (`slow`) | Real-data Phase 3B regenerates every committed table byte for byte; reads `vqc_val` only; frozen artifacts unchanged |
| `test_p4_config.py` | The Phase 4 study matches the Phase 3B profiles, frozen model and τ; actions match the mitigation configs; registered design choices; the schema rejects unregistered designs |
| `test_mitigation_4.py` | Per-qubit readout application equals the Kronecker product (bit order); calibration estimates and exact inversion; convergence with shots; simplex projection is valid, idempotent and optimal (vs SLSQP); stability flag; λ = 1 is the original circuit; folding preserves the ideal unitary and scales noisy gates exactly; noiseless folded distributions are equal; noise exposure increases with λ; an independent channel engine equals Aer on a noisy folded circuit; extrapolation weights and exactness; clean ZNE has no systematic gain; hand-checked resource accounting |
| `test_p4_study.py` | Paired and nested draws; determinism; the oracle never reaches A0–A3/RM; readout mitigation recovers clean scores; noiseless actions are the identity; exactly one τ in the code (AST); RRB rule; Table D cheapest-within-minimum-effect; G2 verdicts (PASS, CONDITIONAL, FAIL, universal dominance, negative controls never count, clean flag); `phase4` access and static guard |
| `test_p4_real.py` (`slow`) | Real-data Phase 4 regenerates every committed table byte for byte; reads `vqc_val` only; the frozen artifact is unchanged |
| `test_p5a_config.py` | The registered 16 × 4 grid; alias-safe encodings; protocol identical to P3A-R; `phase5a` access is VQC-only; the schema rejects alias-prone encodings, wrong IDs, unknown components and incomplete seed keys |
| `test_p5a_pool.py` | Registry and IDs; train-only feature sets (ranking reproduction enforced); alias-safe encoders; shared-fraud-vector metric; ansatz sizes; readout diagonals; Aer replay equals the exact engine (RA/ESU2, parity/mean-Z); deterministic training with retraining and Aer checks; every qualification criterion and duplicate detection; prediction-hash stability; power formula against the F distribution; the G3A rule (PASS, CONDITIONAL, FAIL paths); diversity summary; static guard |
| `test_p5b_config.py` | Registered Phase 5B design (Phase 4 conditions and budgets, A4, cost order, A04 partition map, lockbox location); features deployable and the prohibited list offline-only; `phase5b` access is controller-only; the schema rejects leaky features, an unsealed lockbox, overlapping splits and shared partitions |
| `test_p5b_counterfactual.py` | Structure split and partition isolation (all seeds together; 32/16/16); frozen pool verification; counterfactual completeness, no duplicate rows and determinism; probe behavior (clean, readout, gate) and sharing within a replicate; clean readout mitigation is the identity; action and probe costs by hand; order-independent merge with duplicate refusal; controller features deployable and leak-free; probes free of labels; synthetic end-to-end build (isolated files, lockbox split, records) and report (deterministic) |
| `test_p5b_analysis.py` | Oracle and failure definitions; train-fitted category rule and universal failures; random-effects heterogeneity detection; a priori probe categories; deterministic structure-association test; every G3B path; lockbox refusal |
| `test_p5b_real.py` (`slow`) | Partial regeneration (2 models × 3 conditions × 2 replicates) matches the stored dataset row for row; the registered report and the cost table reproduce byte for byte; the test split is never read |
| `test_p5c_design.py` | Registered design regenerates to its hash; split-plot and sliced-LHS structure; ranges within the validated anchors (T2 ≤ 2T1); inherits Phase 5B unchanged; schema guards |
| `test_p5c_generation.py` | Completeness, determinism and run-time validation on synthetic panels with the real frozen models; draws identical to Phase 4 `draw_context`; gate-free plot has no gate signal; leakage guard rejects 5C design truth; end-to-end build → lockbox → registered report |
| `test_p5c_analysis.py` | Oracle = cheapest within tolerance; failure ≡ disagreement; material failure; decision-list fitting recovers thresholds; noise-only ceiling; label instability; G3C verdict logic; lockbox refusal |
| `test_p5c_real.py` (`slow`) | Partial regeneration (2 models × 3 points × 2 replicates) matches the stored dataset row for row; the registered report and cost table reproduce byte for byte; test split never read |
| `test_controller_learned.py` | Learned-policy tooling: classification and benefit formulations recover a known structure; structure-grouped folds; unknown categories rejected |
| `test_controller_lockbox.py` | One-time sealed-test unlock refuses an uncommitted, unpushed or dirty state and a second unlock; every later read is logged |
| `test_remote_transfer.py`, `test_remote_notebook.py` | Remote-compute guards: sealed paths and `ctrl_test` never transferred; imports hash-, commit- and path-checked, never overwrite; the notebook is pinned, secret-free and cannot push |
| `test_p5a_real.py` (`slow`) | Real-data pool rebuild reproduces every deterministic output (tables, artifacts, manifest) byte for byte; reads `vqc_train`/`vqc_val` only; the anchor is unchanged |
| `test_phase3a_real.py` (`slow`) | Real-data Phase 3A regenerates every committed table and the frozen VQC byte for byte |
| `test_phase2_real.py` (`slow`) | Real-data Phase 2 regenerates every committed table byte for byte |
| `test_data_groups_access.py` | O23: zero exact overlap; zero exact-duplicate or near-duplicate groups crossing partitions (with independent recomputation); reproducible and order-independent group assignment; stratification within bound; preprocessing fitted on the corrected `vqc_train`; Phase 2 cannot read controller partitions (runtime refusal, read-time filter, static check); `phase3b` reads `vqc_val` only; the static `ctrl_*` guard covers Phases 2–3B |

**Markers:** `slow` (statistical and end-to-end) and `qpu` (never by default). Each phase adds its own tests before it is complete.

## 14. Roadmap (timeline corrected by the PI, 2026-10-06)

| Phase | Dates | Goal | Exit gate |
|---|---|---|---|
| **0** | Oct 6–7 | Specification, reproducible scaffold, smoke test | §15 |
| **1** | Oct 6–7 (done) | ULB pipeline: verified download, duplicate audit, dedup before split, option-B partitions, train-only preprocessing, subset utility, panel interface | **Done**: §15b |
| **2** | Oct 7 (done) | Classical fraud sanity baselines; metric implementation; evidence for O02 and O17 (not decisions) | **Done**: §15c |
| **3A** | Oct 7 (done) | First clean 4-qubit VQC: top-4 angles, parity readout, COBYLA; frozen and reproducible; equal-input classical comparison | **Done**: §15d; VQC weak (O24) |
| — | **Oct 12** | **Freeze results and figures for the Oct 13 presentation** | — |
| — | **Oct 13** | Capstone WIP presentation (`F24`) | — |
| **3A-R** | Oct 7 (done) | Pre-registered VQC repair: E3 encoding (±15, [−π/4, π/4]), RealAmplitudes reps 2, parity; selected on `vqc_train` CV only; one-time `vqc_val` AUPRC 0.507 | **Done**: §15e |
| **3B** | Oct 7 (done) | Pre-registered controlled-noise characterization of frozen P3A-R (+ P3A-original contrast): noise engine, 12 anchors + 3 synthetic asymmetric readout stress tests, A13 labels, negative control, E08, 1,024 × 20 finite-shot pilot, runtime benchmark | **G1 = CONDITIONAL PASS** (§15f) |
| **4** | Oct 7 (done) | Pre-registered mitigation characterization of frozen P3A-R: readout (calibration-based), ZNE (global folding), combined, vs None and shot-matched None; 8 conditions × 2 shot arms × 20 replicates; cost accounting | **G2 = CONDITIONAL PASS** (§15g) |
| **5A** | Oct 7 (done) | Pre-registered independent VQC pool: 16 structures × 4 seeds; clean qualification only; frozen manifest; diversity, power and runtime projection | **G3A = PASS** (§15h) |
| **5B** | Oct 7 (done) | Pre-registered cross-model counterfactual dataset (64 models × 8 conditions × 2 budgets × 20 replicates × A0–A4 + RM9) with observable probes; test sealed | **G3B = FAIL** (§15i): fixed probe rule sufficient |
| **5C** | Oct 8 (done) | Continuous mixed-noise counterfactual study (64 models × 68 split-plot noise points × 3 budgets × 20 replicates × A0–A4); simple-rule families; residual-complexity gate | **G3C = FAIL** (§15j): simple probe rule sufficient |
| **6** | Not triggered | Q-TRACE controller training (only on G3C = PASS); G3C failed | — |
| **7** | Oct 8 (done) | Validation comparison of frozen policies; one-time sealed-test evaluation (5C primary, 5B secondary) | **H1–H4 supported** (§15k) |
| **8** | Oct 8 (done) | Validation-only ablations; final report, manuscript, final status, reproducibility guide, capstone and WIP presentations (A16) | — |
| **5** | Oct 29–Nov 8 | Readout, ZNE, Combined; probe; raw resource accounting; resource-matched None | **G2** |
| **6** | Nov 5–15 | Counterfactual dataset; controller-test outcomes lockboxed | Schema-valid; replicate SEs |
| **7** | Nov 9–20 | Predictors | **G3** |
| **8** | Nov 16–29 | Policies; endpoint and threshold freeze; locked evaluation | **G4** (Nov 24 deck shows meta-val only) |
| **9** | Nov 23–Dec 6 | Ablations; out-of-distribution generalization | Dec 8 final |
| **10** | Dec 7 → | Extensions and manuscript | Only if G1–G4 justify them |

## 15. Phase 0 acceptance criteria

The PASS/FAIL evidence is in the Phase 0 completion report and the commit history.

**Review and literature**
- [x] Three specification documents reviewed; Q1–Q3 and A01–A14 decided and recorded in `DECISIONS.md`.
- [x] [RR] moved to `docs/research/` with its checksum unchanged and recorded (here, the README and a test).
- [x] `LITERATURE.md` created; every reference UNVERIFIED; no repaired tokens; no "first" claims.
- [x] `contribution_log.md` and `ai_tool_log.md` initialized.

**Environment**
- [x] Skeleton per §8; `import qtrace` works.
- [x] `pyproject.toml` and `uv.lock` committed; `.python-version` = 3.12; `uv sync --frozen` from a fresh clone works.
- [x] Smoke test: 4-qubit density-matrix circuit with depolarizing, thermal and asymmetric readout noise. All checks pass; versions in the manifest.

**Utilities and tests**
- [x] Config schemas validate, reject unknown keys and produce stable hashes.
- [x] Seed derivation is deterministic, stream-separated and order-independent.
- [x] The manifest writer records commit, dirty flag, config hash, versions, hardware, seeds and timestamps.
- [x] The `ActionOutcome` and `PolicyDecision` schemas are defined and tested.
- [x] Feature registry and R1–R3 leakage tests pass.

**Hygiene**
- [x] `.gitignore` is verified, and no tracked file is larger than 1 MB.
- [x] pytest passes in < 60 s; ruff lint and format are clean.
- [x] No dataset downloaded; no model trained; nothing run beyond the smoke test.
- [x] Two `phase-0:` commits.
- Push to `origin/main` happens only after all of the above pass (PI instruction; no force, no tags). The outcome is recorded in the Phase 0 completion report and in the remote history, not in this file, which is committed before the push.

## 15b. Phase 1 acceptance criteria (all PASS on 2026-10-07)

- [x] Dataset acquired with Kaggle CLI 2.2.4 via `uvx`. Credentials stayed in `~/.kaggle`, were never printed and never copied. Dataset and archive are gitignored.
- [x] SHA-256 verified and recorded (`configs/datasets/ulb_v1.yaml`): `76274b69…1a89`. Provenance recorded: Kaggle ref, dataset id 310, licence DbCL-1.0, archive hash, sizes, timestamp, commands.
- [x] Schema validated: 31 columns in order, float features, labels in {0, 1}, no NaN or infinite values, `Amount` ≥ 0, 284,807 rows, 492 frauds.
- [x] Duplicate audit produced **before** deduplication: exact groups, class mix, fraud duplicates, conflicting labels, near-duplicates ignoring `Time`.
- [x] Deterministic deduplication before splitting (`F27`).
- [x] Deterministic five-way stratified, **group-aware** split (`F28`, `O23`). Zero pairwise overlap; zero exact-duplicate leakage; zero `V1`–`V28` + `Amount` groups crossing partitions; deviation from the allocation is 0.
- [x] Preprocessing fitted on `vqc_train` only. Parameters, training-partition hash and artifact hash persisted. Tests prove other partitions cannot change the fit.
- [x] Configurable VQC-training-subset utility (`vqc_train` only, seeded, ids recorded); nothing frozen.
- [x] Evaluation-panel interface only; nothing frozen (O06).
- [x] Run manifests for every preparation run.
- [x] Synthetic-data unit tests; real-data `slow` tests.
- [x] Committed summary tables contain no transaction-level data (enforced by test). They are byte-identical across reruns and reproduced by a reported run at the commit.
- [x] Changing unrelated seed streams does not alter split or preprocessing artifacts.

## 15c. Phase 2 acceptance criteria (all PASS on 2026-10-07)

- [x] All tests pass (206 default, 5 slow); lint and format pass.
- [x] Corrected group-aware split used: the runner verifies `vqc_train`/`vqc_val` row hashes and the preprocessing artifact against the committed Phase 1 metadata.
- [x] Only `vqc_train` and `vqc_val` accessed: config literals, a phase-scoped loader with a read-time filter, and a static check.
- [x] Three classical baselines run: logistic regression, random forest, histogram gradient boosting (scikit-learn only).
- [x] Full-partition (A) and VQC-scale (B: 1, 4, 9 legitimate per fraud, 3 draws each) regimes compared; subset seeds and row hashes recorded.
- [x] PCA-4 (unstandardized and standardized) and supervised top-4 representations evaluated against all 30 features, with paired bootstrap differences.
- [x] All required metrics computed and tested against scikit-learn; ECE binning documented.
- [x] Threshold procedure documented (max F1 on `vqc_val`), with a cross-fitted honesty check.
- [x] Bootstrap intervals reproducible (seeded, fixed class counts, never empty of positives).
- [x] No transaction-level data committed (tables aggregate-only; per-row scores gitignored).
- [x] Tables and figures reproduce from configuration (byte-identical reruns; slow test).
- [x] Controller partitions untouched.
- [x] Results and limitations documented (`EXPERIMENT_PROTOCOL` §2.7, Phase 2 report).

## 15d. Phase 3A acceptance criteria (all PASS on 2026-10-07)

- [x] A 4-qubit VQC trains (COBYLA, 277 of 600 evaluations, BCE 0.733 → 0.604).
- [x] Only `vqc_train` and `vqc_val` accessed (phase guard, config literals, static check over `qml/` and the scripts).
- [x] Top-4 selection reproduced exactly (V17, V14, V12, V10).
- [x] Angle encoder fitted on `vqc_train` only; parameters persisted and hashed (`a03d3efc…`).
- [x] 1,065-row subset deterministic (hash `4e04298d…`; seed recorded; 213 fraud / 852 legitimate).
- [x] Optimizer configuration and full trace recorded.
- [x] Parameters frozen and hashed (`a30e2645…`; artifact `9c7fc390…`).
- [x] Retraining reproduces the parameters bitwise (max |Δθ| = 0 ≤ 1e-10); frozen replay is identical; Aer noiseless replay agrees.
- [x] Validation predictions non-constant (27,465 distinct scores).
- [x] Required metrics produced with bootstrap intervals; threshold metrics labelled exploratory.
- [x] Equal-input/equal-data LR, RF and HGB comparison produced; full-data context kept separate.
- [x] Runtime and circuit statistics recorded.
- [x] All tests and lint pass.
- [x] No transaction-level data committed.
- [x] Tables and figures reproduce from configuration (slow test).
- [x] Controller partitions untouched.

## 15e. Phase 3A-R acceptance (all PASS on 2026-10-07)

- [x] Candidate matrix pre-registered and committed before any run (`05b1435`); 10 candidates (cap 12); E3 addition disclosed.
- [x] 5-fold group-aware stratified CV inside `vqc_train`; fold hashes recorded; no `vqc_val` or controller access during selection (access phase, AST test).
- [x] Encoding collision diagnostics for E0–E3; the selected E3 cuts shared fraud vectors from 123 to 2 and removes single-qubit aliasing.
- [x] Identical restart seeds; all inits, final losses, statuses and CV metrics recorded; restart spread reported.
- [x] Deterministic selection (`e3-r2-par`, primary metric); frozen and hashed before evaluation.
- [x] One-time `vqc_val` evaluation reported, with comparisons to P3A-original and equal-input LR/RF/HGB.
- [x] Circuit, runtime and reproducibility recorded (bitwise retrain; byte-identical outputs).
- [x] P3A-original files untouched (verified); all tests and lint pass; no transaction-level data committed.

## 15f. Phase 3B acceptance (2026-10-07)

- [x] Pre-registration committed and pushed before the real experiment (`b5a14bb`); rules executed unchanged; implementation details and one wording erratum disclosed (`PREREG_P3B.md`, execution record).
- [x] Frozen P3A-R is the primary model and P3A-original the exploratory contrast; both artifacts are byte-identical before and after; no retraining, retuning, mitigation or controller.
- [x] `vqc_val` only (access phase `phase3b`); controller partitions untouched (runtime and static guards).
- [x] Stage 1 exact Aer density-matrix distributions for clean + 15 conditions × 2 models; clean equals the exact engine to 1.9e-15.
- [x] Negative control passes (affine residual ≤ 4.4e-16; |ΔAUPRC|, |ΔAUROC|, 1 − ρ ≤ 1.3e-13).
- [x] E08 passes all five tests on all four profiles before Stage 2.
- [x] Stage 2 pilot (1,024 × 20) compared with finite-shot clean of the same replicate; labelled as an O07 pilot only.
- [x] A13 labels, paired bootstrap CIs, G1 verdict under the registered rule (CONDITIONAL PASS); effect sizes reported, no post-hoc "meaningful".
- [x] Synthetic AR profiles labelled as synthetic asymmetric readout stress-test profiles everywhere (O20 open).
- [x] Figures A–E drawn from committed tables (palette validated); runtime benchmark recorded.
- [x] Outputs reproduce byte for byte (slow test); all tests and lint pass; no transaction-level data committed.

## 15g. Phase 4 acceptance (2026-10-07)

- [x] Pre-registration committed and pushed before the experiment (`9d377d0`); executed unchanged; implementation details and disclosures in the `PREREG_P4.md` execution record.
- [x] Frozen P3A-R, frozen τ and `vqc_val` only (access phase `phase4`); artifact byte-identical before and after; controller partitions unread (runtime and static guards); no retraining or threshold tuning (single τ, AST test).
- [x] Registered subset of 8 Phase 3B conditions (exact parameters); applicability matrix (applicable / partial / negative control; PEC not applicable).
- [x] Readout mitigation from calibration counts only (estimates recorded; projection documented; no oracle leak, tested); oracle diagnostic kept separate.
- [x] ZNE by global folding (1, 3, 5): ideal unitary preserved; noisy gates scale exactly λ×; noise exposure increases; independent channel engine agrees; linear primary, Richardson diagnostic.
- [x] Exact negative controls pass (symmetric readout: no AUPRC/AUROC change, clean scores restored); E08 on folded circuits and calibration checks pass.
- [x] 1,024 and 4,096 shot arms × 20 replicates; paired and nested draws; shot-matched resource baseline (RM3) and exposure-matched diagnostic (RM9).
- [x] Benefit vector (discrimination, calibration, threshold, ranking, cost); Tables A–D; two-stage intervals; H4.1–H4.5; G2 under the registered rule (CONDITIONAL PASS).
- [x] Raw cost accounting (shots, circuits, calibration, gate-shots, depth-weighted shots; runtime separate).
- [x] Figures A–E from committed tables (palette validated, rendered and inspected); outputs reproduce byte for byte (slow test); all tests and lint pass; no transaction-level data committed.

## 15h. Phase 5A acceptance (2026-10-07)

- [x] Pre-registration committed and pushed before training (`d542770`); executed unchanged; disclosures in the `PREREG_P5A.md` execution record.
- [x] `vqc_train`/`vqc_val` only (access phase `phase5a`; runtime and static guards); controller partitions unread; no noise, mitigation, counterfactuals or controller.
- [x] 64 candidates (3 feature sets, 3 encodings, 2 ansatz families × 2 depths, 2 readouts; 4 seeds); one frozen protocol (P3A-R optimizer, restarts, subset rule).
- [x] Qualification on clean validity only (Q1–Q9): 64/64 qualified; bitwise retraining and Aer replay pass for every model; duplicate and near-duplicate detection.
- [x] Stable IDs and hashes; one frozen artifact per model; manifest with status, hashes, configuration, τ_m and clean metrics; anchor untouched; controls labelled and excluded.
- [x] Diversity (structural, prediction, performance, circuit), power assessment (O15), runtime benchmark and Phase 5B projection; G3A = PASS under the registered rule.
- [x] Tables A–E and figures A–D from committed tables; deterministic outputs reproduce byte for byte (slow test); all tests and lint pass; no transaction-level data committed.

## 15i. Phase 5B acceptance (2026-10-07)

- [x] Pre-registration (with code) committed and pushed before any outcome (`0572c4c`); reported generation run on that tree; disclosures in the `PREREG_P5B.md` execution record.
- [x] Frozen pool (manifest hash verified; every artifact and circuit hash verified); no model change.
- [x] Structure-level split 8/4/4 (all seeds together); A04 panels (each model only its partition; access phase `phase5b`); full controller partitions; test outcomes sealed in the lockbox and never analysed.
- [x] A0–A4 (A4 extra shots) + RM9; Phase 4 implementations; paired, nested draws; raw costs; probe cost charged separately.
- [x] Observable features (static + label-free probes) registry-checked; true simulator parameters offline-only (A15); automated leakage tests.
- [x] Counterfactual completeness (122,880 rows; no duplicates); deterministic isolated-worker merge; content hashes.
- [x] Registered analysis: benefit distributions, preferred-action frequencies, random effects, variance decomposition, probe predictability, structure association, Q1–Q6, **G3B = FAIL**, so stopped.
- [x] Tables and figures A–F from committed tables; slow partial-regeneration and report-reproduction tests; lint; no transaction-level data committed.

## 15j. Phase 5C acceptance (2026-10-08)

- [x] Pre-registration with code committed and pushed before any outcome (`39b584a`); reported run on that tree; execution record with disclosures.
- [x] Frozen pool, 5B structure split, A04 panels, actions, probes and features inherited unchanged; registered design regenerated to its hash; all per-model checks passed.
- [x] 1,305,600 counterfactual rows; test sealed (count and hash committed only); deterministic merge.
- [x] Registered analysis: Oracle, failure and material failure, three simple-rule families fitted on train, noise-only ceiling, label instability, cluster-bootstrap CIs, sensitivity, **G3C = FAIL**, so no controller.
- [x] Figures A–E from committed tables; slow reproduction test; lint; no transaction-level data committed.

## 15k. Final evaluation acceptance (2026-10-08)

- [x] Protocol, config and code pushed before fitting comparators or reading the test (`b7df65f`); one disclosed pre-output correction (`919ecdc`).
- [x] Phase 7 validation comparison and comparator freeze (fingerprints) pushed before the unlock (`5e09c85`).
- [x] Single unlock via the guard; sealed contents hash-verified; comparators reproduced their fingerprints; two logged reads.
- [x] Pre-registered tables and figures; hypotheses H1–H4 evaluated as registered; slow reproduction test.

## 15l. Completion deliverables (A16 A–J; 2026-10-08)

- [x] A final report (`FINAL_REPORT.md`) · B manuscript (`MANUSCRIPT.md`) · C final figures (`results/figures/final_*`, `p5c_*`) · D final tables (`results/tables/final_*`, `p5c_*`, `p7_*`, `ablation_*`).
- [x] E reproducibility guide (`REPRODUCIBILITY.md`) · F decision log (`DECISIONS.md`) · G limitations (`FINAL_REPORT.md` §16) · H capstone presentation (`presentations/CAPSTONE_final.md`) · I WIP presentation (`presentations/WIP_phase4_to_5c.md`) · J final status (`FINAL_STATUS.md`).

## 16. Team, attribution and working rules

**Team:** Mayank Kumar Pokhriyal (PI for this repository) and Tushar Poonia.

**Logs**
- `docs/contribution_log.md` records **actual** dated work.
- `docs/ai_tool_log.md` records which AI tool did what.

**Commits and pushes**
- Commits are named `phase-N: <summary>`, one or two small commits per phase.
- Push to `origin` only after the phase's validation passes and when the PI instructs.
- Never force-push or rewrite published history.
- No tags or releases without instruction. `protocol-v1.0` is created only at the protocol freeze.

**Phase discipline**
- Never start a phase before approval.
- Never rewrite a completed phase without a `DECISIONS.md` entry.
- Never delete results or research documents without explicit approval.
