"""Representative Q-TRACE simulation benchmark (CPU vs GPU), runnable locally or on Colab.

Workload = the production hot path of Phases 4-5C, on deterministic SYNTHETIC parameter
bindings (no transaction data, no controller partition, nothing sealed):

- **exact stage**: Aer density-matrix probabilities of a frozen pool model's transpiled circuit,
  globally folded at lambda = 1, 3, 5, under three registered Phase 5C gate-noise plots
  (low / medium / high), one row per binding (exactly as ``qtrace.noise.exact``);
- **finite-shot stage**: one replicate of paired draws, mitigation vectors and endpoint metrics
  (numpy; CPU only), to measure the share of time a GPU cannot touch.

The CPU "production" variant calls the unchanged ``exact_distributions``; device/option
variants use a local copy of the same loop so production code is never modified. Every variant
is compared with the production reference (max |dp|), and the reference is fingerprinted so
outputs from different machines can be compared offline.
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import resource
import shutil
import subprocess
import sys
import time
from importlib import metadata
from pathlib import Path

import numpy as np

BENCH_MODEL = "p5a-top4-e3-ra2-parity-s0"  # P3A-R-like structure: 18 CX, noisy depth 21
BENCH_PLOTS = ("g04", "g14", "g06")  # registered 5C gate plots: low / medium / high
FACTORS = (1, 3, 5)
SEED_KEY = "remote-bench-bindings"


def hardware() -> dict:
    info = {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": sys.version.split()[0],
        "logical_cpus": os.cpu_count(),
    }
    try:
        info["ram_gb"] = round(os.sysconf("SC_PAGE_SIZE") * os.sysconf("SC_PHYS_PAGES") / 2**30, 1)
    except (ValueError, OSError):
        info["ram_gb"] = None
    if sys.platform == "darwin":
        for key, name in (
            ("cpu_model", "machdep.cpu.brand_string"),
            ("perf_cores", "hw.perflevel0.physicalcpu"),
            ("efficiency_cores", "hw.perflevel1.physicalcpu"),
        ):
            try:
                info[key] = subprocess.run(
                    ["sysctl", "-n", name], capture_output=True, text=True, check=True
                ).stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                info[key] = None
    elif Path("/proc/cpuinfo").exists():
        models = [
            line.split(":", 1)[1].strip()
            for line in Path("/proc/cpuinfo").read_text().splitlines()
            if line.startswith("model name")
        ]
        info["cpu_model"] = models[0] if models else None
    if shutil.which("nvidia-smi"):
        q = "name,memory.total,driver_version"
        out = subprocess.run(
            ["nvidia-smi", f"--query-gpu={q}", "--format=csv,noheader"],
            capture_output=True,
            text=True,
        ).stdout.strip()
        info["gpu"] = out or None
        smi = subprocess.run(["nvidia-smi"], capture_output=True, text=True).stdout
        cuda = [w for w in smi.split("|") if "CUDA Version" in w]
        info["cuda_driver_version"] = cuda[0].split("CUDA Version:")[1].strip() if cuda else None
    else:
        info["gpu"] = None
    info["packages"] = {
        p: _version(p)
        for p in ("qiskit", "qiskit-aer", "qiskit-aer-gpu", "numpy", "scipy", "pandas")
    }
    return info


def _version(pkg: str) -> str | None:
    try:
        return metadata.version(pkg)
    except metadata.PackageNotFoundError:
        return None


def peak_rss_mb() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 2**20 if sys.platform == "darwin" else rss / 2**10


def gpu_memory_used_mb() -> float | None:
    if not shutil.which("nvidia-smi"):
        return None
    out = subprocess.run(
        ["nvidia-smi", "--query-gpu=memory.used", "--format=csv,noheader,nounits"],
        capture_output=True,
        text=True,
    ).stdout.strip()
    try:
        return float(out.splitlines()[0])
    except (ValueError, IndexError):
        return None


METADATA_KEYS = (
    "batched_shots_optimization",
    "runtime_parameter_bind",
    "device",
    "method",
    "parallel_experiments",
    "parallel_state_update",
    "num_bind_params",
)


def run_exact(
    circuit, values, noise_model, device: str, options: dict, chunk: int, meta: dict | None = None
) -> np.ndarray:
    """Same loop as ``qtrace.noise.exact.exact_distributions`` with device/options exposed.

    ``meta`` (if given) receives Aer's result metadata of the first chunk, which shows whether
    batched GPU execution / runtime binding actually engaged.
    """
    from qiskit_aer import AerSimulator

    circ = circuit.copy()
    circ.save_probabilities()
    sim = AerSimulator(method="density_matrix", noise_model=noise_model, device=device, **options)
    params = list(circ.parameters)
    out = np.empty((len(values), 2**circ.num_qubits))
    for start in range(0, len(values), chunk):
        block = values[start : start + chunk]
        binds = [{p: block[:, j].tolist() for j, p in enumerate(params)}]
        result = sim.run(circ, parameter_binds=binds).result()
        if meta is not None and start == 0:
            first = result.results[0].metadata or {}
            meta.update({k: first[k] for k in METADATA_KEYS if k in first})
            top = result.metadata or {}
            meta.update(
                {f"run_{k}": top[k] for k in ("parallel_experiments", "omp_enabled") if k in top}
            )
        out[start : start + len(block)] = [
            result.data(i)["probabilities"] for i in range(len(block))
        ]
    return out


def fingerprint(arr: np.ndarray) -> str:
    """Platform-comparable hash of probabilities rounded to 10 decimals."""
    return hashlib.sha256(np.round(arr, 10).tobytes()).hexdigest()


def flatten_parameters(circuit):
    """Replace every parametrised gate angle by a fresh Parameter (one per distinct expression).

    Returns (flat circuit, evaluator) where ``evaluator(values)`` maps the original per-row
    parameter values (columns in ``circuit.parameters`` order) to the new parameters' values.
    Aer's runtime parameter binding (the batched GPU path) does not accept multi-parameter
    expressions such as the ZZ feature map's (pi - x0)(pi - x1); this makes it applicable
    without changing the simulated circuit. Expressions are evaluated with numpy from their
    exact string form (plain arithmetic over indexed parameter vectors), in a sandbox.
    """
    import re

    from qiskit.circuit import Parameter, ParameterExpression

    originals = list(circuit.parameters)
    fresh: dict[str, Parameter] = {}
    flat = circuit.copy_empty_like()  # same qubits and layout
    flat.global_phase = 0.0  # a (parametrised) global phase never changes probabilities
    for inst in circuit.data:
        params = []
        for prm in inst.operation.params:
            if isinstance(prm, ParameterExpression) and prm.parameters:
                key = str(prm)
                if key not in fresh:
                    fresh[key] = Parameter(f"_flat{len(fresh):04d}")
                params.append(fresh[key])
            else:
                params.append(prm)
        if params == list(inst.operation.params):
            flat.append(inst.operation, inst.qubits, inst.clbits)
            continue
        op = inst.operation.to_mutable()
        op.params = params
        flat.append(op, inst.qubits, inst.clbits)
    codes = {k: compile(k, "<expr>", "eval") for k in fresh}
    order = sorted(fresh, key=lambda k: fresh[k].name)  # the flat circuit's parameter order
    pattern = re.compile(r"^(.+)\[(\d+)\]$")

    def evaluate(values: np.ndarray) -> np.ndarray:
        space: dict = {"__builtins__": {}, "pi": np.pi, "sin": np.sin, "cos": np.cos}
        vectors: dict[str, dict[int, np.ndarray]] = {}
        for j, prm in enumerate(originals):
            m = pattern.match(prm.name)
            if m:
                vectors.setdefault(m.group(1), {})[int(m.group(2))] = values[:, j]
            else:
                space[prm.name] = values[:, j]
        for name, items in vectors.items():
            space[name] = [items[k] for k in range(max(items) + 1)]
        cols = [np.broadcast_to(eval(codes[k], space), (len(values),)) for k in order]  # noqa: S307
        return np.column_stack(cols).astype(float)

    if [p.name for p in flat.parameters] != [fresh[k].name for k in order]:
        raise RuntimeError("unexpected parameter order in the flattened circuit")
    return flat, evaluate


VARIANTS = {
    # name: (device, options, chunk). "_flat" = fresh Parameter per angle expression (exact).
    "cpu_default_chunk4096": ("CPU", {}, 4096),
    "cpu_parallel_experiments": ("CPU", {"max_parallel_experiments": 0}, 4096),
    "cpu_runtime_bind": ("CPU", {"runtime_parameter_bind_enable": True}, 4096),  # fails: exprs
    "cpu_flat_default": ("CPU", {"_flat": True}, 4096),
    "cpu_flat_parallel_experiments": ("CPU", {"_flat": True, "max_parallel_experiments": 0}, 4096),
    "gpu_default_chunk4096": ("GPU", {}, 4096),  # one experiment per binding
    "gpu_flat_parallel_experiments": ("GPU", {"_flat": True, "max_parallel_experiments": 0}, 4096),
    # Aer 0.13+ batched parameter binding on GPU (runtime bind + batched_shots_gpu)
    "gpu_flat_batched_chunk4096": (
        "GPU",
        {"_flat": True, "runtime_parameter_bind_enable": True, "batched_shots_gpu": True},
        4096,
    ),
    "gpu_flat_batched_chunk32768": (
        "GPU",
        {"_flat": True, "runtime_parameter_bind_enable": True, "batched_shots_gpu": True},
        32768,
    ),
}


def available_devices() -> tuple[str, ...]:
    from qiskit_aer import AerSimulator

    try:
        return tuple(AerSimulator().available_devices())
    except Exception:  # noqa: BLE001 - report, never fail the benchmark on discovery
        return ("CPU",)


def run(rows: tuple[int, ...], variants: tuple[str, ...], out_dir: Path, tag: str) -> dict:
    """Benchmark the exact and finite-shot stages; write JSON + reference arrays to ``out_dir``."""
    from qtrace.config import repo_root
    from qtrace.counterfactual import mixed as MX
    from qtrace.counterfactual.mixed_study import load_mixed_study
    from qtrace.counterfactual.pool_models import BASIS, load_pool
    from qtrace.mitigation import zne as Z
    from qtrace.noise.exact import exact_distributions
    from qtrace.noise.models import gate_noise_model
    from qtrace.utils.seeds import make_rng

    t_all = time.perf_counter()
    out_dir.mkdir(parents=True, exist_ok=True)
    resolved, study, base, pool, mit, design = load_mixed_study()  # verifies the design hash
    model = {m.model_id: m for m in load_pool(repo_root(), base, pool)}[BENCH_MODEL]  # hashes
    devices = available_devices()
    seed = model.circuit["transpile_seed"]
    folded = {f: Z.fold_global(model.transpiled, f, BASIS, seed) for f in FACTORS}
    flat = {f: flatten_parameters(folded[f]) for f in FACTORS}
    noise = {
        g: gate_noise_model(MX.profile_of(design[design.gate_plot == g].iloc[0]), BASIS)
        for g in BENCH_PLOTS
    }
    report: dict = {
        "tag": tag,
        "hardware": hardware(),
        "aer_devices": list(devices),
        "model": BENCH_MODEL,
        "gate_plots": list(BENCH_PLOTS),
        "factors": list(FACTORS),
        "design_sha256": study.design.design_sha256,
        "exact": [],
        "finite_shot": [],
        "skipped": [],
    }
    refs, failed = {}, set()
    for n in rows:
        ang = make_rng(resolved.spec.seeds.model, "model", SEED_KEY, n).uniform(
            -np.pi / 4, np.pi / 4, size=(n, 4)
        )
        values = model.values(ang)
        for g in BENCH_PLOTS:
            t = time.perf_counter()
            ref = {f: exact_distributions(folded[f], values, noise[g]) for f in FACTORS}
            prod_s = time.perf_counter() - t
            refs[(n, g)] = ref
            report["exact"].append(
                {
                    "rows": n,
                    "plot": g,
                    "variant": "cpu_production",
                    "seconds": prod_s,
                    "ms_per_row_all_factors": 1e3 * prod_s / n,
                    "max_abs_dp_vs_reference": 0.0,
                    "fingerprint": {f: fingerprint(ref[f]) for f in FACTORS},
                }
            )
            for name in variants:
                device, opts, chunk = VARIANTS[name]
                if name in failed:
                    continue
                if device not in devices:
                    failed.add(name)
                    report["skipped"].append({"variant": name, "reason": f"{device} unavailable"})
                    continue
                opts = dict(opts)
                use_flat = opts.pop("_flat", False)
                t = time.perf_counter()
                try:
                    got = {}
                    for f in FACTORS:
                        if use_flat:
                            circ, evaluate = flat[f]
                            vals = evaluate(values)
                        else:
                            circ, vals = folded[f], values
                        meta: dict = {}
                        got[f] = run_exact(circ, vals, noise[g], device, opts, chunk, meta)
                except Exception as exc:  # noqa: BLE001 - an unsupported option is a result
                    failed.add(name)
                    report["skipped"].append(
                        {"variant": name, "rows": n, "reason": repr(exc)[:300]}
                    )
                    continue
                sec = time.perf_counter() - t
                report["exact"].append(
                    {
                        "rows": n,
                        "plot": g,
                        "variant": name,
                        "seconds": sec,
                        "ms_per_row_all_factors": 1e3 * sec / n,
                        "max_abs_dp_vs_reference": float(
                            max(np.max(np.abs(got[f] - ref[f])) for f in FACTORS)
                        ),
                        "gpu_memory_used_mb": gpu_memory_used_mb(),
                        "aer_metadata": {k: str(v) for k, v in meta.items()},
                    }
                )
        report["finite_shot"].append(_finite_shot(n, refs[(n, BENCH_PLOTS[1])], model, mit, design))
    smallest = min(rows)
    np.savez_compressed(
        out_dir / f"reference_{tag}.npz",
        **{f"{g}_f{f}": refs[(smallest, g)][f] for g in BENCH_PLOTS for f in FACTORS},
    )
    report["peak_rss_mb"] = peak_rss_mb()
    report["total_seconds"] = time.perf_counter() - t_all
    (out_dir / f"bench_{tag}.json").write_text(json.dumps(report, indent=2) + "\n")
    return report


def _finite_shot(n: int, exact: dict, model, mit, design) -> dict:
    """One replicate of the Phase 5C finite-shot stage at 1,024 shots (numpy; CPU)."""
    from qtrace.counterfactual import generate as G
    from qtrace.counterfactual import mixed as MX
    from qtrace.counterfactual import mixed_generate as MG
    from qtrace.mitigation import readout as RO
    from qtrace.mitigation import zne as Z
    from qtrace.utils.seeds import make_rng

    point = design[design.gate_plot == BENCH_PLOTS[1]].iloc[2]
    prof = MX.profile_of(point)
    cal_exact = G.calibration_exact(prof)
    probs = {f: G._with_readout(exact[f], prof) for f in FACTORS}
    y = (np.arange(n) % 600 == 0).astype(int)  # synthetic labels (no transaction data)
    w = Z.extrapolation_weights(FACTORS, mit.zne.primary_extrapolator)
    t = time.perf_counter()
    draws = MG.draw_mixed(
        probs, cal_exact, 1024, FACTORS, lambda c: make_rng(1, "shots", "bench", c)
    )
    t_draw = time.perf_counter() - t
    cal = RO.estimate_calibration(draws["cal0"], draws["cal1"])
    freqs = {f: draws[f"lam{f}"] / 1024 for f in FACTORS}
    t = time.perf_counter()
    vecs, _ = G.action_vectors(
        freqs,
        {"RM3": draws["rm3"] / 3072},
        cal,
        model.diagonal,
        w,
        mit.readout.min_assignment_determinant,
    )
    t_vec = time.perf_counter() - t
    t = time.perf_counter()
    for v in vecs.values():
        MG.outcome_metrics(y, v, model.tau)
    t_met = time.perf_counter() - t
    return {
        "rows": n,
        "draw_s": t_draw,
        "vectors_s": t_vec,
        "metrics_s": t_met,
        "total_per_replicate_context_s": t_draw + t_vec + t_met,
    }
