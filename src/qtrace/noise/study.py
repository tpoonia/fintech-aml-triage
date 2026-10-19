"""Phase 3B configured run: controlled-noise characterization of the frozen VQCs.

Order (PREREG_P3B): Stage 1 exact noisy distributions -> negative control (stop on
failure) -> E08 sampler validation (Stage 2 only if it passes) -> Stage 2
finite-shot pilot (primary model) -> A13 labels and the G1 verdict.

Access phase "phase3b": vqc_val only. No mitigation, no controller, no retraining.
"""

from __future__ import annotations

import io
import json
import platform
import resource
import time
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path

import numpy as np
import pandas as pd

from qtrace.classical.runner import vqc_val_bootstrap_seed
from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import NoiseProfile, NoiseStudyConfig
from qtrace.data.access import load_partitions
from qtrace.data.ingest import ROW_ID
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.verify import verify_phase1
from qtrace.evaluation import metrics as M
from qtrace.noise import diagnostics as D
from qtrace.noise import shots as S
from qtrace.noise.exact import exact_distributions
from qtrace.noise.frozen import FrozenCircuit, load_frozen
from qtrace.noise.models import (
    apply_readout,
    effective_configuration,
    gate_noise_model,
    has_gate_noise,
)
from qtrace.utils.hashing import file_sha256, stable_hash
from qtrace.utils.seeds import derive_seed, make_rng

EXPERIMENT_ID = "phase3b_noise"
STUDY_ID = "p3b_v1"
PHASE = "phase3b"
DIGITS = 9
T = "results/tables/"
CLEAN = NoiseProfile(profile_id="clean", family="none")
CLEAN_CROSSCHECK_TOL = 1e-10
HIST_BINS = 50


def _software() -> dict[str, str]:
    names = ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn")
    return {n: importlib_metadata.version(n) for n in names}


def _peak_rss_mib() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 2**20 if platform.system() == "Darwin" else rss / 2**10


def g1_family(profile: NoiseProfile) -> str:
    if profile.role == "synthetic_stress":
        return "synthetic_asymmetric_readout"
    if profile.role == "negative_control":
        return "symmetric_readout_negative_control"
    return profile.family


@dataclass
class ModelRun:
    model_id: str
    role: str
    circuit: FrozenCircuit
    values: np.ndarray  # transpiled-circuit parameter values per vqc_val row (row_id order)
    probs: dict[str, np.ndarray]  # condition -> exact (readout-included) distributions
    scores: dict[str, np.ndarray]  # condition -> exact p_fraud
    tau: float
    clean_crosscheck_max_abs_z: float
    metrics: dict[str, dict] = field(default_factory=dict)
    intervals: dict[str, dict] = field(default_factory=dict)
    labels: dict[str, dict] = field(default_factory=dict)
    negative_control: dict[str, dict] = field(default_factory=dict)


@dataclass
class NoiseStudyRun:
    study: NoiseStudyConfig
    profiles: list[NoiseProfile]
    y: np.ndarray
    row_ids: np.ndarray
    models: dict[str, ModelRun]
    context: dict
    timings: dict[str, float]
    status: str
    g1: dict | None = None
    e08: dict[str, dict] = field(default_factory=dict)
    shot_rows: list[dict] = field(default_factory=list)


def load_study(config_root: Path | None = None):
    """Resolved experiment, the registered study and its 15 noise conditions (matrix order)."""
    resolved = load_experiment(EXPERIMENT_ID, config_root)
    study = load_component("noise_study", STUDY_ID, config_root)
    profiles = [
        p for sid in study.noise_sets for p in load_component("noise", sid, config_root).profiles
    ]
    return resolved, study, profiles


def stage1(root: Path, ref, base, study, profiles, val, y, timings) -> ModelRun:
    circuit = load_frozen(root, ref, base)
    if tuple(base.basis_gates) != tuple(study.basis_gates) or (
        base.optimization_level != study.optimization_level
    ):
        raise RuntimeError("transpilation settings differ from the registered study")
    values = circuit.values(val)
    key = ref.model_id
    t = time.perf_counter()
    clean = exact_distributions(circuit.transpiled, values, None)
    timings[f"{key}_exact_clean_s"] = time.perf_counter() - t
    z_engine = 1.0 - 2.0 * circuit.exact_engine_scores(val)
    dev = float(np.max(np.abs(D.parity_z(clean) - z_engine)))
    if dev > CLEAN_CROSSCHECK_TOL:
        raise RuntimeError(f"{key}: Aer clean deviates from the frozen exact engine by {dev:.2e}")
    probs = {"clean": clean}
    gate_cache: dict[tuple, np.ndarray] = {}
    for prof in profiles:
        if has_gate_noise(prof):
            sig = (prof.p1, prof.p2, prof.thermal, prof.gate_time_1q_ns, prof.gate_time_2q_ns)
            if sig not in gate_cache:
                model = gate_noise_model(
                    prof,
                    study.basis_gates,
                    study.one_qubit_noisy_gates,
                    study.two_qubit_noisy_gates,
                )
                t = time.perf_counter()
                gate_cache[sig] = exact_distributions(circuit.transpiled, values, model)
                timings[f"{key}_exact_{prof.profile_id}_s"] = time.perf_counter() - t
            gate = gate_cache[sig]
        else:
            gate = clean
        probs[prof.profile_id] = (
            apply_readout(gate, prof.readout_p01, prof.readout_p10) if prof.has_readout else gate
        )
    scores = {c: D.fraud_score(p) for c, p in probs.items()}
    tau = M.max_f1_threshold(y, scores["clean"])
    return ModelRun(key, ref.role, circuit, values, probs, scores, tau, dev)


def diagnose(run: ModelRun, study, profiles, y, boot_seed, n_jobs, timings) -> None:
    clean = run.scores["clean"]
    t = time.perf_counter()
    for prof in profiles:
        run.metrics[prof.profile_id] = D.condition_metrics(
            y, clean, run.scores[prof.profile_id], run.tau, study.top_k, study.ece_bins
        )
    run.intervals = D.paired_bootstrap(
        y,
        clean,
        {p.profile_id: run.scores[p.profile_id] for p in profiles},
        study.bootstrap_resamples,
        boot_seed,
        study.ece_bins,
        n_jobs=n_jobs,
    )
    clean_brier = M.brier(y, clean)
    for prof in profiles:
        pid = prof.profile_id
        run.labels[pid] = D.a13_labels(run.metrics[pid], run.intervals[pid], clean_brier, study.a13)
        if prof.role == "negative_control":
            run.negative_control[pid] = D.negative_control(
                y,
                D.parity_z(run.probs["clean"]),
                D.parity_z(run.probs[pid]),
                prof.readout_p01,
                run.circuit.transpiled.num_qubits,
            )
    timings[f"{run.model_id}_diagnostics_s"] = time.perf_counter() - t


def run_e08(root_seeds, run: ModelRun, study, profiles, timings) -> dict[str, dict]:
    cfg = study.e08
    by_id = {p.profile_id: p for p in [CLEAN, *profiles]}
    values = run.values[: cfg.n_rows]
    out = {}
    t0 = time.perf_counter()
    for pid in cfg.profiles:
        prof = by_id[pid]
        model = (
            gate_noise_model(
                prof,
                study.basis_gates,
                study.one_qubit_noisy_gates,
                study.two_qubit_noisy_gates,
                include_readout=True,
            )
            if (has_gate_noise(prof) or prof.has_readout)
            else None
        )
        aer_seed = derive_seed(root_seeds.shots, "shots", cfg.seed_key, pid, "aer") % (2**32)
        aer = S.direct_aer_counts(run.circuit.transpiled, values, model, cfg.shots, aer_seed)
        rng = make_rng(root_seeds.shots, "shots", cfg.seed_key, pid, "multinomial")
        exact = run.probs[pid][: cfg.n_rows]
        mult = S.sample_counts(exact, cfg.shots, rng)
        out[pid] = S.e08_tests(exact, aer, mult, cfg.shots, cfg)
    timings["e08_s"] = time.perf_counter() - t0
    return out


def run_stage2(root_seeds, run: ModelRun, study, profiles, y, timings) -> list[dict]:
    cfg = study.finite_shot
    conditions = ["clean", *[p.profile_id for p in profiles]]
    exact_clean = run.scores["clean"]
    rows: list[dict] = []
    t_sample = t_metric = 0.0
    shot_clean: dict[int, dict] = {}
    for cond in conditions:
        for rep in range(cfg.replicates):
            t = time.perf_counter()
            rng = make_rng(root_seeds.shots, "shots", cfg.seed_key, cond, rep)
            s = S.counts_score(S.sample_counts(run.probs[cond], cfg.shots, rng), cfg.shots)
            t_sample += time.perf_counter() - t
            t = time.perf_counter()
            row = {
                "model": run.model_id,
                "condition": cond,
                "replicate": rep,
                "auprc": M.average_precision(y, s),
                "auroc": M.roc_auc(y, s),
                "brier": M.brier(y, s),
                "spearman_vs_exact_clean": M.spearman(exact_clean, s),
                "distinct_scores": int(np.unique(s).size),
            }
            if cond == "clean":
                shot_clean[rep] = row
            ref = shot_clean[rep]
            for m in ("auprc", "auroc", "brier"):
                row[f"delta_{m}_vs_shot_clean"] = row[m] - ref[m]
            t_metric += time.perf_counter() - t
            rows.append(row)
    timings["finite_shot_sampling_s"] = t_sample
    timings["finite_shot_metrics_s"] = t_metric
    return rows


def run_noise_study(root: Path, n_jobs: int = -1) -> NoiseStudyRun:
    timings: dict[str, float] = {}
    t_all = time.perf_counter()
    resolved, study, profiles = load_study()
    spec, dataset, base = resolved.spec, resolved.dataset, resolved.vqc
    before = {m.model_id: file_sha256(root / m.artifact) for m in study.models}
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, PHASE, [study.partition])
    verified = verify_phase1(root, dataset.dataset_id, frame, fitted, (study.partition,))
    val = frame.sort_values(ROW_ID).reset_index(drop=True)
    y = val[dataset.target_column].to_numpy(dtype=np.int64)
    boot_seed = vqc_val_bootstrap_seed(spec.seeds, dataset.dataset_id)

    models: dict[str, ModelRun] = {}
    t1 = time.perf_counter()
    for ref in study.models:
        models[ref.model_id] = stage1(root, ref, base, study, profiles, val, y, timings)
    timings["stage1_exact_total_s"] = time.perf_counter() - t1
    for run in models.values():
        diagnose(run, study, profiles, y, boot_seed, n_jobs, timings)

    primary = next(m for m in study.models if m.role == "primary").model_id
    nc_pass = all(nc["passed"] for r in models.values() for nc in r.negative_control.values())
    status, g1, e08, shot_rows = "completed", None, {}, []
    if not nc_pass:
        status = "stopped_negative_control_failed"
    else:
        e08 = run_e08(spec.seeds, models[primary], study, profiles, timings)
        if not all(r["passed"] for r in e08.values()):
            status = "stopped_e08_failed"
        else:
            shot_rows = run_stage2(spec.seeds, models[primary], study, profiles, y, timings)
        g1 = D.g1_verdict(
            [
                {
                    "condition": p.profile_id,
                    "g1_family": g1_family(p),
                    "severity": p.severity,
                    "role": p.role,
                    "labels": models[primary].labels[p.profile_id],
                    **models[primary].metrics[p.profile_id],
                }
                for p in profiles
            ],
            study.a13,
        )
    after = {m.model_id: file_sha256(root / m.artifact) for m in study.models}
    if before != after:
        raise RuntimeError("a frozen artifact changed during the run")
    timings["total_s"] = time.perf_counter() - t_all
    timings["peak_rss_mib_main_process"] = _peak_rss_mib()
    context = {
        **verified,
        "rows": len(val),
        "frauds": int(y.sum()),
        "artifact_file_sha256_before": before,
        "artifact_file_sha256_after": after,
        "experiment_config_hash": resolved.config_hash(),
        "study_config_hash": stable_hash(study),
    }
    return NoiseStudyRun(
        study,
        profiles,
        y,
        val[ROW_ID].to_numpy(),
        models,
        context,
        timings,
        status,
        g1,
        e08,
        shot_rows,
    )


# ------------------------------------------------------------------------- rendering


def _csv(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.round(DIGITS).to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def _sci(x: float) -> str:
    return f"{x:.3e}"


def _profile_rows(run: NoiseStudyRun) -> list[NoiseProfile]:
    return [CLEAN, *run.profiles]


def render_noise_study(run: NoiseStudyRun) -> dict[str, str]:
    study, y = run.study, run.y
    out: dict[str, str] = {}
    prof_by_id = {p.profile_id: p for p in _profile_rows(run)}

    matrix = []
    for p in _profile_rows(run):
        row = effective_configuration(p, study)
        row["g1_family"] = g1_family(p) if p.profile_id != "clean" else "reference"
        row["role"] = "reference" if p.profile_id == "clean" else p.role
        row["label"] = (
            "synthetic asymmetric readout stress-test profile (not device calibration)"
            if p.role == "synthetic_stress"
            else ("negative control" if p.role == "negative_control" else row["role"])
        )
        matrix.append(row)
    out[T + "p3b_noise_matrix.csv"] = _csv(pd.DataFrame(matrix))

    metric_rows, label_rows, nc_rows = [], [], []
    for mid, mr in run.models.items():
        clean_row = {
            "model": mid,
            "model_role": mr.role,
            "condition": "clean",
            "g1_family": "reference",
            "severity": "",
            "auprc": M.average_precision(y, mr.scores["clean"]),
            "auroc": M.roc_auc(y, mr.scores["clean"]),
            "brier": M.brier(y, mr.scores["clean"]),
            "ece": M.expected_calibration_error(y, mr.scores["clean"], study.ece_bins, "uniform"),
            "tau_frozen_clean": mr.tau,
        }
        for m in D.BOOT_METRICS:
            clean_row[f"{m}_ci_low"], clean_row[f"{m}_ci_high"] = mr.intervals["clean"][m]
        metric_rows.append(clean_row)
        for p in run.profiles:
            pid = p.profile_id
            row = {
                "model": mid,
                "model_role": mr.role,
                "condition": pid,
                "g1_family": g1_family(p),
                "severity": p.severity,
                **mr.metrics[pid],
                "tau_frozen_clean": mr.tau,
            }
            for name, (lo, hi) in mr.intervals[pid].items():
                row[f"{name}_ci_low"], row[f"{name}_ci_high"] = lo, hi
            metric_rows.append(row)
            lab = mr.labels[pid]
            label_rows.append(
                {
                    "model": mid,
                    "model_role": mr.role,
                    "condition": pid,
                    "g1_family": g1_family(p),
                    "severity": p.severity,
                    **{k: bool(v) for k, v in lab.items()},
                    "labels": "|".join(k for k in D.LABELS if lab[k]) or "none",
                    "spearman": mr.metrics[pid]["spearman"],
                    "kendall": mr.metrics[pid]["kendall"],
                    "top47_overlap": mr.metrics[pid]["top47_overlap"],
                    "delta_auprc_ci_high": mr.intervals[pid]["delta_auprc"][1],
                    "delta_auroc_ci_high": mr.intervals[pid]["delta_auroc"][1],
                    "crossing_fraction": mr.metrics[pid]["crossing_fraction"],
                    "fraud_crossing_rate": mr.metrics[pid]["fraud_crossing_rate"],
                    "in_g1": mr.role == "primary" and p.role != "negative_control",
                }
            )
            if pid in mr.negative_control:
                nc = mr.negative_control[pid]
                nc_rows.append(
                    {
                        "model": mid,
                        "condition": pid,
                        "readout_p": nc["readout_p"],
                        "contraction_factor": nc["contraction_factor"],
                        "max_abs_affine_residual": _sci(nc["max_abs_affine_residual"]),
                        "abs_delta_auprc": _sci(nc["abs_delta_auprc"]),
                        "abs_delta_auroc": _sci(nc["abs_delta_auroc"]),
                        "one_minus_spearman": _sci(1 - nc["spearman"]),
                        "tolerances": "residual<=1e-10; |dAUPRC|,|dAUROC|<=1e-9; 1-rho<=1e-9",
                        "passed": nc["passed"],
                    }
                )
    out[T + "p3b_exact_metrics.csv"] = _csv(pd.DataFrame(metric_rows))
    out[T + "p3b_a13_labels.csv"] = _csv(pd.DataFrame(label_rows))
    out[T + "p3b_negative_control.csv"] = _csv(pd.DataFrame(nc_rows))

    if run.e08:
        out[T + "p3b_e08_validation.csv"] = _csv(
            pd.DataFrame([{"profile": k, **v} for k, v in run.e08.items()])
        )
    if run.shot_rows:
        reps = pd.DataFrame(run.shot_rows)
        out[T + "p3b_finite_shot_replicates.csv"] = _csv(reps)
        out[T + "p3b_finite_shot_summary.csv"] = _csv(_shot_summary(run, reps))

    rep_conditions = ["clean", *study.representative_conditions]
    edges = np.linspace(0.0, 1.0, HIST_BINS + 1)
    hist, hist2d, cal = [], [], []
    for mid, mr in run.models.items():
        clean = mr.scores["clean"]
        for cond in rep_conditions:
            s = mr.scores[cond]
            legit, _ = np.histogram(s[y == 0], bins=edges)
            fraud, _ = np.histogram(s[y == 1], bins=edges)
            hist += [
                {
                    "model": mid,
                    "condition": cond,
                    "bin_lower": edges[i],
                    "bin_upper": edges[i + 1],
                    "legit_count": int(legit[i]),
                    "fraud_count": int(fraud[i]),
                }
                for i in range(HIST_BINS)
            ]
            cal += [
                {"model": mid, "condition": cond, **b}
                for b in M.calibration_bins(y, s, study.ece_bins, "uniform")
            ]
            if cond == "clean":
                continue
            for cls, name in ((0, "legit_count"), (1, "fraud_count")):
                h, _, _ = np.histogram2d(clean[y == cls], s[y == cls], bins=[edges, edges])
                for i, j in zip(*np.nonzero(h), strict=True):
                    hist2d.append(
                        {
                            "model": mid,
                            "condition": cond,
                            "clean_bin": int(i),
                            "noisy_bin": int(j),
                            "class": name.removesuffix("_count"),
                            "count": int(h[i, j]),
                        }
                    )
    out[T + "p3b_score_histogram.csv"] = _csv(pd.DataFrame(hist))
    out[T + "p3b_calibration_bins.csv"] = _csv(pd.DataFrame(cal))
    hist2d_frame = pd.DataFrame(hist2d).sort_values(
        ["model", "condition", "class", "clean_bin", "noisy_bin"], kind="stable"
    )
    out[T + "p3b_score_hist2d.csv"] = _csv(hist2d_frame)
    out[T + "p3b_metadata.json"] = json.dumps(_metadata(run, prof_by_id), indent=2) + "\n"
    return out


def _shot_summary(run: NoiseStudyRun, reps: pd.DataFrame) -> pd.DataFrame:
    primary = next(m for m in run.models.values() if m.role == "primary")
    metrics = [
        "auprc",
        "auroc",
        "brier",
        "spearman_vs_exact_clean",
        "delta_auprc_vs_shot_clean",
        "delta_auroc_vs_shot_clean",
        "delta_brier_vs_shot_clean",
    ]
    rows = []
    for cond, grp in reps.groupby("condition", sort=False):
        exact = (
            {"auprc": 0.0, "auroc": 0.0, "brier": 0.0}
            if cond == "clean"
            else {m: primary.metrics[cond][f"delta_{m}"] for m in ("auprc", "auroc", "brier")}
        )
        for m in metrics:
            v = grp[m].to_numpy()
            row = {
                "model": primary.model_id,
                "condition": cond,
                "metric": m,
                "n_replicates": len(v),
                "mean": v.mean(),
                "sd": v.std(ddof=1),
                "min": v.min(),
                "q05": np.quantile(v, 0.05),
                "q50": np.quantile(v, 0.50),
                "q95": np.quantile(v, 0.95),
                "max": v.max(),
            }
            if m.startswith("delta_"):
                row["exact_delta_vs_exact_clean"] = exact[m.split("_")[1]]
            rows.append(row)
    return pd.DataFrame(rows)


def _metadata(run: NoiseStudyRun, prof_by_id) -> dict:
    study = run.study
    models = {}
    for mid, mr in run.models.items():
        models[mid] = {
            "role": mr.role,
            "artifact": mr.circuit.ref.artifact,
            "artifact_content_sha256": mr.circuit.ref.artifact_sha256,
            "artifact_file_sha256": mr.circuit.artifact_file_sha256,
            "transpiled_circuit": mr.circuit.stats,
            "tau_frozen_clean": mr.tau,
            "clean_crosscheck_max_abs_z_vs_exact_engine": _sci(mr.clean_crosscheck_max_abs_z),
            "clean_crosscheck_tolerance": CLEAN_CROSSCHECK_TOL,
            "negative_control_passed": all(nc["passed"] for nc in mr.negative_control.values()),
            "label_counts": {
                lab: sum(bool(v[lab]) for v in mr.labels.values()) for lab in D.LABELS
            },
        }
    return {
        "experiment_id": EXPERIMENT_ID,
        "study_id": study.study_id,
        "preregistration": "docs/PREREG_P3B.md (committed b5a14bb before the experiment)",
        "status": run.status,
        "g1": run.g1 if run.g1 is not None else "not issued",
        "e08_passed": bool(run.e08) and all(r["passed"] for r in run.e08.values()),
        "context": run.context,
        "models": models,
        "noise_conditions": [p.profile_id for p in run.profiles],
        "representative_conditions": list(study.representative_conditions),
        "synthetic_profiles_note": (
            "ar-005/ar-020/ar-050 are synthetic asymmetric readout stress-test profiles, "
            "not IBM or device calibration data (O20 open)"
        ),
        "finite_shot_note": (
            "O07 pilot only (1,024 shots x 20 replicates); does not freeze the final shot protocol"
        ),
        "bootstrap": {
            "resamples": study.bootstrap_resamples,
            "scheme": "stratified, fixed class counts; shared Phase 2 vqc_val resamples; paired",
            "confidence": 0.95,
        },
        "seeds": {
            "finite_shot": (
                f"shots stream, key ({study.finite_shot.seed_key}, condition, replicate)"
            ),
            "e08": f"shots stream, key ({study.e08.seed_key}, profile, aer|multinomial)",
        },
        "exclusions": (
            "no mitigation, no Q-TRACE controller, no retraining; "
            "controller partitions not read (access phase phase3b)"
        ),
        "software": _software(),
    }
