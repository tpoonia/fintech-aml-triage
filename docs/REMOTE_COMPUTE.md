# Optional remote compute (Google Colab): audit, setup, workflow and recommendation

| | |
|---|---|
| **Status** | Tooling ready and tested (pushed `1abe5bd`). **Local benchmark done (§5). Colab benchmark: pending, run by the PI** (needs a Google account; costs well under 1 compute unit). Recommendation (§6): local MacBook. |
| **Scope** | Optional infrastructure. **No registered experiment uses it.** The authoritative repository, git history, frozen artifacts and the sealed lockbox stay on the MacBook and GitHub. |
| **Files** | Package `src/qtrace/remote/`:<br>• `bench.py` (benchmark)<br>• `transfer.py` (guards, export, pack, import)<br>`scripts/remote/`:<br>• `bench_aer.py`, `export_inputs.py`, `pack_results.py`, `import_results.py`, `compare_bench.py`<br>Notebook `notebooks/colab_qtrace_benchmark.ipynb`.<br>Tests `tests/test_remote_transfer.py`, `tests/test_remote_notebook.py`. |
| **Decision** | DECISIONS E62 |

## 1. Where the time goes (audit of the current backend)

**Per model in Phase 5C,** measured single-process on the idle MacBook before the run (42,559-row panel):

| Stage | What runs | Cost | Share |
|---|---|---|---|
| **Exact stage** | Aer `density_matrix` on the transpiled circuit, folded at λ = 1/3/5, **one Aer experiment per transaction row** (`parameter_binds`, 4,096-row chunks), for each of 16 noisy gate plots | λ = 1/3/5 = 10.8 / 32.5 / 55.1 s per plot, ≈ 1,570 s | ≈ 60% |
| **Finite-shot stage** | numpy multinomial draws, readout inversion, ZNE extrapolation, Brier/ECE/AUPRC/AUROC/threshold metrics, for 68 points × 3 budgets × 20 replicates | ≈ 0.25 s per replicate-context, ≈ 1,000 s | ≈ 40% |

- **Exact-stage scaling:** cost scales linearly with folded circuit length (1 : 3 : 5) and with rows. Each row is a tiny 16 × 16 density-matrix simulation of about 70–350 noisy gates.
- **How parallelism is currently obtained:** by 15 isolated worker processes (one per model). Inside a process, Aer's default `max_parallel_experiments = 1` runs bindings serially.

**Local bottlenecks observed during Phase 5C:**
- **Memory, not just CPU.** 15 workers each oscillate between 0.5 and 2.4 GB (Aer result objects for 4,096-binding chunks). On a 24 GB machine this costs about 25% of CPU time in memory compression.
- **Asymmetric cores.** 5 performance + 10 efficiency cores. The measured throughput is about 6.8 performance-core equivalents.

**What a GPU can and cannot touch:**
- It can only accelerate the exact stage (≈ 60%).
- The finite-shot stage is numpy on the CPU, plus Python-side extraction of `result.data(i)` per row.
- **Amdahl bound:** even an infinitely fast GPU leaves the finite-shot stage running on Colab's 2–12 vCPUs, which are 1–6 physical cores (one vCPU = one hyper-thread).

## 2. Can Aer use a Colab GPU? (web-verified 2026-10-08; sources in Appendix A)

| Question | Answer |
|---|---|
| GPU build matching our pinned Aer 0.17.2 | **Only `qiskit-aer-gpu-cu11==0.17.2`** (CUDA 11, manylinux x86_64, cp39–cp313). `qiskit-aer-gpu` (CUDA 12) stops at 0.15.1, which does not import under Qiskit 2.x. No CUDA 12/13 wheel exists for 0.16–0.17. |
| Install | **Replaces** `qiskit-aer` (same `qiskit_aer` import); uninstall the CPU package first. Its CUDA 11 user-space libraries come from pip and are found by RPATH. |
| GPU types | Compiled for sm 7.0–8.7:<br>• T4 (7.5) and A100 (8.0) native<br>• L4 (8.9) should run<br>• **H100 (9.0) and G4 (12.0) are not covered** |
| Density matrix on GPU | Supported |
| Small circuits | The Aer authors report that GPUs lose to CPUs at small qubit counts (launch and transfer overheads). Nothing is published at 4 qubits. |
| Batched bindings on GPU | `runtime_parameter_bind_enable=True` + `batched_shots_gpu=True` (Aer ≥ 0.13) runs many bindings of one circuit in shared kernels. Density matrix qualifies up to 8 qubits. |
| Our circuits | Runtime binding **fails** as built: the ZZ feature map uses multi-parameter angle expressions. The benchmark's *flattened* circuits fix this: one fresh parameter per angle expression, values computed in numpy. They are **bit-identical** to production (max \|Δp\| = 0). |
| Colab image (Oct 2026) | Ubuntu 24.04, **Python 3.13**, CUDA 13.0 by default. Our lock needs Python 3.12, so the notebook uses a uv-managed CPython 3.12. Fallback: pin runtime version **2026.07** (Python 3.12, CUDA 12.8). Colab also sets `UV_*` variables that break `uv sync`; the notebook clears them. |
| Cost | Compute-unit rates are not published by Google. Third-party measurements (March 2026): T4 ≈ 1.2, L4 ≈ 1.7, A100-40 ≈ 5.4 CU/h; CPU runtimes ≈ 0.07–0.14 CU/h (2024 figures). Read the live rate under *View resources*. |
| Hardware | 2024 figures: CPU and T4 runtimes have 2 vCPU / 13 GB; High-RAM variants 8 vCPU / 51 GB; L4 and A100 12 vCPU / 53–84 GB. |
| Session limits | At most 12 h (24 h on Pro+). Idle timeouts vary. |
| Maintenance | Aer is in reduced maintenance; open issue #2393 reports GPU batched/runtime-bound results differing in some noisy statevector tests. **Any GPU result must pass an equivalence check against CPU production.** The benchmark does this for every variant. |

## 3. Setup guide

### 3.1 One-time

1. **GitHub token.** Create a fine-grained token with **read-only "Contents"** permission on this repository only.
2. **Colab secret.** In Colab, open *Secrets* and add `GITHUB_TOKEN` with notebook access.
   - The token is read via `google.colab.userdata`, handed to git through a temporary `GIT_ASKPASS` script, then deleted.
   - It is never printed and never written into `.git/config`.
3. **Pinned commit.** The notebook clones a *pinned, pushed* commit, verifies `HEAD` equals it and the tree is clean, and then **removes the git remote** so the runtime cannot push.

### 3.2 Benchmark run (≈ 10–40 min)

1. Open `notebooks/colab_qtrace_benchmark.ipynb` in Colab and choose a **T4** GPU runtime.
   - Optionally repeat on a CPU runtime for the Colab CPU numbers.
2. Set `PINNED_COMMIT` to the commit printed by `git rev-parse origin/main`. It must contain `scripts/remote/`.
3. Run all cells. The notebook:
   - installs from `uv.lock` (Python 3.12);
   - on GPU, swaps `qiskit-aer` for `qiskit-aer-gpu-cu11` of the same version;
   - runs `scripts/remote/bench_aer.py`;
   - downloads `bench-colab-<gpu>.zip`.
4. **No data is uploaded.** The benchmark uses deterministic synthetic bindings and the frozen pool artifacts from the commit.

### 3.3 Back on the MacBook

```bash
uv run python scripts/remote/import_results.py ~/Downloads/bench-colab-t4.zip   # verified; never overwrites
uv run python scripts/remote/compare_bench.py                                   # table, projections, agreement
```

The importer refuses the bundle if any of these hold:
- any file hash differs from its manifest;
- the commit is not in local history;
- a path escapes the job directory or touches sealed material (`results/lockbox/`, `*_test.parquet`, `data/raw/`);
- `results/remote/<job_id>/` already exists.

Commit the imported JSON. Reference `.npz` arrays stay gitignored.

## 4. Workflow for a future remote experiment (if ever justified)

| Step | Where | Guard |
|---|---|---|
| 1. Pre-register, commit and **push** the experiment with its code | MacBook | Existing pre-registration rules |
| 2. Export only the needed partitions: `scripts/remote/export_inputs.py --partitions ctrl_train,ctrl_val` | MacBook | **`ctrl_test` is refused.** Per-partition row-id hashes must match the committed Phase 1 metadata; output goes to gitignored `remote_staging/` |
| 3. Clone the pinned commit and place the exported data at the same relative paths | Colab | `HEAD` = pinned commit; git remote removed. The unchanged Phase 1 verification passes for the exported partitions only |
| 4. Run the registered script as a *reported* run (clean tree at the pinned commit) | Colab | Run manifest records commit, platform and hashes. Jobs touching test-split models are **not** run remotely: sealed outcomes are generated and read only on the MacBook |
| 5. `scripts/remote/pack_results.py` → zip with a SHA-256 manifest | Colab | Refuses sealed material |
| 6. `scripts/remote/import_results.py` → `results/remote/<job_id>/` | MacBook | Hash, commit and path checks; **never overwrites**. Frozen artifacts and committed tables change only through a local, reviewed commit that renders them from the imported raw outputs |

**Scientific equivalence across machines.**
- Exact probabilities agree to floating-point tolerance, not bit for bit: different BLAS, CPU or GPU kernels. The benchmark fingerprints the production reference (rounded to 1e-10) per platform and reports max |Δp|.
- Finite-shot draws use platform-independent seeds (numpy PCG64). However, a last-bit difference in a probability can, rarely, flip a multinomial draw.
- **Rule:** a registered experiment runs entirely on one platform, recorded in its manifest. Results from different platforms are never mixed within one registered dataset. A cross-platform rerun is a reproduction check judged against the documented tolerance, not a byte-for-byte replacement.

## 5. Benchmark results

### 5.1 Local MacBook, idle (2026-10-08, after Phase 5C)

**Setup.** `results/remote/bench/bench_mac-m5pro.json`: Apple M5 Pro, 5 performance + 10 efficiency cores, 24 GB RAM, Aer 0.17.2 CPU. Model `p5a-top4-e3-ra2-parity-s0`, registered gate plots g04 / g14 / g06 (low / medium / high), synthetic bindings.

**Exact stage, per transaction row, all three folds** (mean of the 3 plots):

| Variant | 2,048 rows | 8,192 rows | vs production | max \|Δp\| vs production |
|---|---|---|---|---|
| **production** (1 process; Aer serial over bindings) | 3.86 ms | 3.92 ms | 1× | 0 |
| flattened parameters, 1 thread | 3.44 ms | 3.49 ms | 1.12× | 0 |
| `max_parallel_experiments=0` (15 threads, 1 process) | 1.08 ms | 1.07 ms | 3.6× | 0 |
| flattened + `max_parallel_experiments=0` | 0.76 ms | 0.77 ms | **5.1×** | 0 |
| runtime parameter binding (CPU) | fails on the unflattened circuit | | | |

All results are **bit-identical** to production.

**Finite-shot stage** (numpy): 0.033 s per replicate-context at 2,048 rows and 0.067 s at 8,192. That is about 0.35 s at a 42,559-row panel.

**Phase 5C-scale single-process work:** about 47 h exact plus about 25 h finite-shot.

**What production actually achieved.** The registered Phase 5C run used 15 single-threaded worker processes. It took **6.8 h wall**, an effective **≈ 10.7×** over one process. It was limited by memory compression, not cores.

### 5.2 Colab (pending)

Run `notebooks/colab_qtrace_benchmark.ipynb` on a T4 (and optionally a CPU runtime), import the zip, and run `compare_bench.py`.

The rows that decide the question are `gpu_flat_batched_chunk4096` / `gpu_flat_batched_chunk32768`. Their `aer_metadata` must show batching engaged.

## 6. Recommendation

**Use the local MacBook for the rest of Q-TRACE.** This is a firm recommendation, and the Colab numbers can only refine it. There are three reasons:
- the remaining workload is light;
- the sealed evaluation must be local;
- the end-to-end arithmetic already rules Colab out for simulation campaigns like Phase 5C, even with an infinitely fast GPU.

1. **The remaining workload is not simulation-bound.** Phase 5C was the last large simulation. G3C = FAIL, so no controller training campaign follows. What remains:
   - the Phase 7 comparison of small scikit-learn models on tabular context features;
   - the one-time sealed-test evaluation, which **must** run locally (lockbox isolation);
   - figures and documents.

   Each takes minutes on the MacBook.
2. **Colab CPU: no.**
   - Hardware: 2 vCPUs ≈ 1 physical core on standard and T4 runtimes; 8–12 vCPUs ≈ 4–6 cores on High-RAM, L4 and A100.
   - On a 5C-scale job, the numpy finite-shot stage alone would take **≈ 17–25 h on a T4 runtime** and about 4–6 h on 12 vCPUs. The MacBook did the whole job in 6.8 h.
3. **Colab GPU: not worth compute units for this project.**
   - It can only accelerate the exact stage (about 65% of single-process work).
   - **Amdahl bound:** with an *infinitely* fast GPU, a T4 runtime would still need about 17–25 h for the finite-shot stage on its 2 vCPUs.
   - An A100 runtime (12 vCPU, ≈ 5.4 CU/h) might roughly match the MacBook's 6.8 h for about 25–35 CU, with no time saved.
   - Colab GPU becomes interesting only if a *future* campaign also moves the finite-shot stage to the GPU (CuPy/JAX). That would be new engineering and would need its own equivalence validation.
4. **The cheapest real speed-up is local and exact.**
   - Flattened parameters are bit-identical and 1.12× faster per thread.
   - Combined with Aer's `max_parallel_experiments` within fewer processes, they could also ease the memory pressure that limited Phase 5C.
   - **Not adopted** for any registered experiment. It would need its own validation and decision entry first.

**Rule for the 300 compute units:** spend them only to run the benchmark notebook once (well under 1 CU on a T4). Do not run full experiments remotely unless all three E62 conditions are met:
- ≥ 3× exact-stage speed-up;
- ≤ 1e-10 agreement with production;
- a positive end-to-end saving.

The measurements above already show the third condition fails for this workload shape.

## Appendix A. Sources (read 2026-10-08)

Agent web check; re-verify time-sensitive items (rates, images) before relying on them.

**Packages**
- PyPI JSON for `qiskit-aer-gpu`, `qiskit-aer-gpu-cu11` and `qiskit-aer`: <https://pypi.org/pypi/qiskit-aer-gpu/json>, <https://pypi.org/pypi/qiskit-aer-gpu-cu11/json>, <https://pypi.org/pypi/qiskit-aer/json>.

**Qiskit Aer project**
- **Reduced maintenance and install notes:** README, <https://raw.githubusercontent.com/Qiskit/qiskit-aer/main/README.md>.
- **Issues:**
  - CUDA 12 wheels and the cu11 workaround: <https://github.com/Qiskit/qiskit-aer/issues/2336>
  - CUDA 13: <https://github.com/Qiskit/qiskit-aer/issues/2374>
  - batched GPU result differences: <https://github.com/Qiskit/qiskit-aer/issues/2393>
  - installing both packages: <https://github.com/Qiskit/qiskit-aer/issues/2351>
- **GPU architectures:** deploy workflow, <https://raw.githubusercontent.com/Qiskit/qiskit-aer/main/.github/workflows/deploy.yml>.
- **Library paths (RPATH):** <https://raw.githubusercontent.com/Qiskit/qiskit-aer/0.17.2/CMakeLists.txt>.
- **Options:** AerSimulator API, <https://qiskit.github.io/qiskit-aer/stubs/qiskit_aer.AerSimulator.html>.
- **Runtime parameter binding (0.13):** release notes, <https://qiskit.github.io/qiskit-aer/release_notes.html>.
- **Small circuits are slower on GPU:** Doi, Horii and Wood, Aer GPU paper, <https://arxiv.org/abs/2308.03399>.

**Colab**
- **Image** (Python 3.13, CUDA 13, Ubuntu 24.04): <https://github.com/googlecolab/backend-info>.
- **Pinned runtime 2026.07:** <https://research.google.com/colaboratory/runtime-version-faq.html>.
- **Limits:** FAQ, <https://research.google.com/colaboratory/faq.html>.
- **`UV_*` variables:** <https://github.com/googlecolab/colabtools/issues/5237>.
- **GPU list:** <https://github.com/googlecolab/google-colab-cli>.
- **Plans:** <https://colab.research.google.com/signup>.

**Compute-unit rates and VM sizes (third-party)**
- <http://mccormickml.com/2024/04/23/colab-gpus-features-and-pricing/> (checked March 2026).
- <https://varlog.info/colab-credit-consumption-comparison-2024/> (October 2024).
