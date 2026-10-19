"""Phase 4 configured run: mitigation characterization of the frozen P3A-R VQC.

Order (PREREG_P4): exact distributions for every gate-noise signature at noise
factors 1/3/5 and the calibration circuits -> run-time checks 1-5 (stop on failure)
-> exact diagnostics -> E08 on folded circuits + calibration checks (finite-shot
stage only if they pass) -> finite-shot study (two arms x 20 replicates, paired
draws, two-stage bootstrap) -> Tables A-D, hypotheses, G2.

Access phase "phase4": vqc_val only. No Q-TRACE, no pool, no PEC, no retraining;
one frozen threshold for every action.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from qtrace.classical.runner import vqc_val_bootstrap_seed
from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import MitigationStudyConfig, NoiseProfile
from qtrace.data.access import load_partitions
from qtrace.data.ingest import ROW_ID
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.verify import verify_phase1
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import percentile_interval, stratified_weights
from qtrace.mitigation import readout as RO
from qtrace.mitigation import zne as Z
from qtrace.mitigation.costs import action_costs, resource_matched_comparator
from qtrace.noise import diagnostics as D
from qtrace.noise import shots as S
from qtrace.noise.exact import exact_distributions
from qtrace.noise.frozen import FrozenCircuit, load_frozen
from qtrace.noise.models import apply_readout, gate_noise_model, has_gate_noise
from qtrace.noise.study import CLEAN
from qtrace.utils.hashing import file_sha256, stable_hash
from qtrace.utils.seeds import derive_seed, make_rng

EXPERIMENT_ID = "phase4_mitigation"
STUDY_ID = "p4_v1"
PHASE = "phase4"
MAIN = ("A0", "A1", "A2", "A3", "RM3")
VECTORS = (*MAIN, "RM9", "A1-oracle", "A2-rich", "A3-rich")
EXACT_VECTORS = ("A0", "A1", "A2", "A3", "A1-oracle", "A2-rich", "A3-rich")
BOOT_COMPARISONS = (
    ("A1", "A0"),
    ("A2", "A0"),
    ("A3", "A0"),
    ("RM3", "A0"),
    ("A2", "RM3"),
    ("A3", "RM3"),
)
REPLICATE_COMPARISONS = (
    *BOOT_COMPARISONS,
    ("RM9", "A0"),
    ("A2", "RM9"),
    ("A3", "RM9"),
    ("A1-oracle", "A0"),
    ("A2-rich", "A0"),
    ("A3-rich", "A0"),
    ("A2-rich", "RM3"),
    ("A3-rich", "RM3"),
)
BOOT_METRICS = ("auprc", "auroc", "brier", "ece", "precision", "recall", "f1")
G2_ENDPOINTS = ("auprc", "brier", "f1")
COST_ORDER = ("A0", "A1", "A2", "A3")
DIAGNOSTIC_VECTORS = ("RM9", "A1-oracle", "A2-rich", "A3-rich")


class StudyStopped(RuntimeError):
    """A registered stopping rule fired (PREREG_P4 §16)."""


# --------------------------------------------------------------------------- loading


def load_mitigation_study(config_root: Path | None = None):
    resolved = load_experiment(EXPERIMENT_ID, config_root)
    study: MitigationStudyConfig = load_component("mitigation_study", STUDY_ID, config_root)
    profiles = {
        p.profile_id: p
        for sid in study.noise_sets
        for p in load_component("noise", sid, config_root).profiles
    }
    profiles["clean"] = CLEAN
    return resolved, study, {c: profiles[c] for c in study.conditions}


def gate_key(p: NoiseProfile) -> tuple | None:
    if not has_gate_noise(p):
        return None
    return (p.p1, p.p2, p.thermal, p.gate_time_1q_ns, p.gate_time_2q_ns)


def _exact_job(circuit, values, profile, basis, factor, seed):
    t = time.perf_counter()
    model = gate_noise_model(profile, basis) if has_gate_noise(profile) else None
    folded = Z.fold_global(circuit, factor, basis, seed)
    out = exact_distributions(folded, values, model)
    return out, time.perf_counter() - t


def _calibration_exact(profile, basis, n_qubits) -> tuple[np.ndarray, np.ndarray]:
    model = gate_noise_model(profile, basis) if has_gate_noise(profile) else None
    dists = []
    for circ in RO.calibration_circuits(n_qubits):
        d = exact_distributions(circ, np.zeros((1, 0)), model)
        if profile.has_readout:
            d = apply_readout(d, profile.readout_p01, profile.readout_p10)
        dists.append(d[0])
    return dists[0], dists[1]


def true_calibration(profile: NoiseProfile, n_qubits: int) -> RO.ReadoutCalibration:
    """Oracle diagnostic only: the simulator's readout parameters (never used by A1/A3)."""
    return RO.ReadoutCalibration(
        np.full(n_qubits, profile.readout_p01), np.full(n_qubits, profile.readout_p10)
    )


# ------------------------------------------------------------------------- metrics


def outcome_metrics(y, s, tau, clean_s, clean_flag, top_k, bins) -> dict[str, float]:
    flag = s >= tau
    cross = flag != clean_flag
    out = {
        "auprc": M.average_precision(y, s),
        "auroc": M.roc_auc(y, s),
        "brier": M.brier(y, s),
        "ece": M.expected_calibration_error(y, s, bins, "uniform"),
        **M.threshold_metrics(y, s, tau),
        "crossing_all": float(cross.mean()),
        "crossing_fraud": float(cross[y == 1].mean()),
        "crossing_legit": float(cross[y == 0].mean()),
        "spearman": M.spearman(clean_s, s),
        "kendall": M.kendall(clean_s, s),
    }
    for k in top_k:
        out[f"top{k}_overlap"] = M.top_k_overlap(clean_s, s, k)
    return out


def _weighted(y, s, tau, w, bins) -> dict[str, float]:
    return {
        "auprc": M.average_precision(y, s, w),
        "auroc": M.roc_auc(y, s, w),
        "brier": M.brier(y, s, w),
        "ece": M.expected_calibration_error_weighted(y, s, w, bins),
        **{k: v for k, v in M.threshold_metrics(y, s, tau, w).items() if k != "f2"},
    }


def score(z: np.ndarray) -> np.ndarray:
    return np.clip((1.0 - z) / 2.0, 0.0, 1.0)


# ------------------------------------------------------------------ action vectors


def action_scores(freqs, cal, oracle, w_lin, w_rich, min_det, extra=None) -> tuple[dict, dict]:
    """Scores of every action from per-factor frequencies (exact or finite-shot).

    ``freqs``: factor -> rows x 2^n frequencies (readout included); ``cal``: the
    estimated calibration (counts only); ``oracle``: the true calibration (diagnostic).
    ``extra``: optional {"RM3": freq, "RM9": freq} for finite-shot runs.
    """
    factors = sorted(freqs)
    z_raw = np.array([D.parity_z(freqs[f]) for f in factors])
    mit, diag = {}, {}
    for f in factors:
        mit[f], diag[f] = RO.mitigate(freqs[f], cal, min_det)
    z_mit = np.array([D.parity_z(mit[f]) for f in factors])
    z_a2, clip_a2 = Z.extrapolate(z_raw, w_lin)
    z_a3, clip_a3 = Z.extrapolate(z_mit, w_lin)
    z_a2r, clip_a2r = Z.extrapolate(z_raw, w_rich)
    z_a3r, clip_a3r = Z.extrapolate(z_mit, w_rich)
    oracle_mit, oracle_diag = RO.mitigate(freqs[1], oracle, min_det)
    out = {
        "A0": score(z_raw[0]),
        "A1": score(z_mit[0]),
        "A2": score(z_a2),
        "A3": score(z_a3),
        "A1-oracle": score(D.parity_z(oracle_mit)),
        "A2-rich": score(z_a2r),
        "A3-rich": score(z_a3r),
    }
    if extra is not None:
        out["RM3"] = score(D.parity_z(extra["RM3"]))
        out["RM9"] = score(D.parity_z(extra["RM9"]))
    info = {
        "A1": {
            "rows_projected": diag[1].rows_projected,
            "l1_moved": diag[1].mean_l1_moved,
            "min_det": diag[1].min_determinant,
            "unstable": diag[1].unstable,
        },
        "A2": {"clip_fraction": clip_a2},
        "A3": {
            "clip_fraction": clip_a3,
            "rows_projected": sum(diag[f].rows_projected for f in factors),
            "unstable": any(diag[f].unstable for f in factors),
        },
        "A1-oracle": {"rows_projected": oracle_diag.rows_projected},
        "A2-rich": {"clip_fraction": clip_a2r},
        "A3-rich": {"clip_fraction": clip_a3r},
    }
    return out, info


# -------------------------------------------------------------- finite-shot context


def draw_context(probs, cal_exact, shots: int, factors, rng) -> dict[str, np.ndarray]:
    """Paired draws of one replicate (PREREG_P4 §9). ``rng(component)`` -> Generator.

    The resource-matched baselines are nested: rm3 = lam1 + 2S extra shots and
    rm9 = rm3 + 6S extra shots, all on the base (factor 1) circuit.
    """
    out = {f"lam{f}": S.sample_counts(probs[f], shots, rng(f"lam{f}")) for f in factors}
    out["rm3"] = out["lam1"] + S.sample_counts(probs[1], 2 * shots, rng("rm_extra2"))
    out["rm9"] = out["rm3"] + S.sample_counts(probs[1], 6 * shots, rng("rm_extra6"))
    out["cal0"] = S.sample_counts(cal_exact[0][None, :], shots, rng("cal0"))[0]
    out["cal1"] = S.sample_counts(cal_exact[1][None, :], shots, rng("cal1"))[0]
    return out


def run_context(
    cond: str,
    arm_id: str,
    shots: int,
    probs: dict[int, np.ndarray],
    cal_exact: tuple[np.ndarray, np.ndarray],
    oracle: RO.ReadoutCalibration,
    y: np.ndarray,
    clean_s: np.ndarray,
    tau: float,
    study: MitigationStudyConfig,
    shots_master: int,
    boot_seed: int,
    rep_draws: np.ndarray,
) -> dict:
    """One (condition, arm): 20 paired replicates of every action + the two-stage bootstrap."""
    w_lin = Z.extrapolation_weights(study.zne.noise_factors, study.zne.primary_extrapolator)
    w_rich = Z.extrapolation_weights(study.zne.noise_factors, "richardson")
    clean_flag = clean_s >= tau
    rows, cal_rows, keep = [], [], {v: [] for v in MAIN}
    t_sample = t_metric = 0.0
    for rep in range(study.replicates):
        t = time.perf_counter()

        def rng(component, rep=rep):
            return make_rng(shots_master, "shots", study.seed_key, cond, arm_id, rep, component)

        draws = draw_context(probs, cal_exact, shots, study.zne.noise_factors, rng)
        cal = RO.estimate_calibration(draws["cal0"], draws["cal1"])
        freqs = {f: draws[f"lam{f}"] / shots for f in study.zne.noise_factors}
        extra = {"RM3": draws["rm3"] / (3 * shots), "RM9": draws["rm9"] / (9 * shots)}
        vecs, info = action_scores(
            freqs, cal, oracle, w_lin, w_rich, study.readout.min_assignment_determinant, extra
        )
        t_sample += time.perf_counter() - t
        t = time.perf_counter()
        for q in range(len(cal.p01)):
            cal_rows.append(
                {
                    "condition": cond,
                    "arm": arm_id,
                    "replicate": rep,
                    "qubit": q,
                    "p01_hat": cal.p01[q],
                    "p10_hat": cal.p10[q],
                    "determinant": cal.determinants[q],
                }
            )
        for v in VECTORS:
            row = {"condition": cond, "arm": arm_id, "replicate": rep, "vector": v}
            row |= outcome_metrics(
                y, vecs[v], tau, clean_s, clean_flag, study.top_k, study.ece_bins
            )
            d = info.get(v, {})
            row["clip_fraction"] = d.get("clip_fraction", 0.0)
            row["rows_projected"] = d.get("rows_projected", 0)
            row["unstable"] = bool(d.get("unstable", False))
            rows.append(row)
        for v in MAIN:
            keep[v].append(vecs[v])
        t_metric += time.perf_counter() - t
    t = time.perf_counter()
    boot = {c: {m: np.empty(len(rep_draws)) for m in BOOT_METRICS} for c in BOOT_COMPARISONS}
    for b, w in enumerate(stratified_weights(y, len(rep_draws), boot_seed)):
        r = int(rep_draws[b])
        vals = {v: _weighted(y, keep[v][r], tau, w, study.ece_bins) for v in MAIN}
        for a, ref in BOOT_COMPARISONS:
            for m in BOOT_METRICS:
                boot[(a, ref)][m][b] = vals[a][m] - vals[ref][m]
    intervals = {
        c: {m: percentile_interval(v, study.g2.confidence) for m, v in d.items()}
        for c, d in boot.items()
    }
    return {
        "condition": cond,
        "arm": arm_id,
        "rows": rows,
        "calibration": cal_rows,
        "intervals": intervals,
        "timing": {
            "sampling_and_mitigation_s": t_sample,
            "metrics_s": t_metric,
            "bootstrap_s": time.perf_counter() - t,
        },
    }


# ------------------------------------------------------------------------- the run


@dataclass
class MitigationRun:
    study: MitigationStudyConfig
    conditions: dict[str, NoiseProfile]
    y: np.ndarray
    tau: float
    circuits: dict[str, dict]
    validation: dict
    exact: dict[
        str, dict
    ]  # condition -> {"metrics": {v: {...}}, "intervals": ..., "scores": {...}}
    context: dict
    timings: dict[str, float]
    status: str
    replicate_rows: list[dict] = field(default_factory=list)
    calibration_rows: list[dict] = field(default_factory=list)
    intervals: dict = field(default_factory=dict)  # (cond, arm) -> comparison -> metric -> CI
    costs: list[dict] = field(default_factory=list)
    analysis: dict = field(default_factory=dict)


def _phase3b_crosscheck(root: Path, exact_metrics: dict[str, dict], tol: float) -> dict:
    ref = pd.read_csv(root / "results" / "tables" / "p3b_exact_metrics.csv")
    ref = ref[ref["model"] == "p3a_r"].set_index("condition")
    worst = 0.0
    for cond, m in exact_metrics.items():
        for k in ("auprc", "auroc", "brier", "ece"):
            worst = max(worst, abs(m["A0"][k] - ref.loc[cond, k]))
    return {"max_abs_diff_vs_p3b_exact_metrics": worst, "tolerance": tol, "passed": worst <= tol}


def run_mitigation_study(root: Path, n_jobs: int = -1) -> MitigationRun:
    timings: dict[str, float] = {}
    t_all = time.perf_counter()
    resolved, study, conds = load_mitigation_study()
    spec, dataset, base = resolved.spec, resolved.dataset, resolved.vqc
    basis = ("rz", "sx", "x", "cx")
    seed = study.model.transpile_seed
    before = file_sha256(root / study.model.artifact)
    fc: FrozenCircuit = load_frozen(root, study.model, base)
    if tuple(base.basis_gates) != basis or base.optimization_level != 1:
        raise StudyStopped("transpilation settings differ from Phase 3B")
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, PHASE, [study.partition])
    verified = verify_phase1(root, dataset.dataset_id, frame, fitted, (study.partition,))
    val = frame.sort_values(ROW_ID).reset_index(drop=True)
    y = val[dataset.target_column].to_numpy(dtype=np.int64)
    values = fc.values(val)
    n_qubits = fc.transpiled.num_qubits
    validation: dict = {}

    # ---- circuits
    folded_stats = {
        f: Z.circuit_statistics(Z.fold_global(fc.transpiled, f, basis, seed))
        for f in study.zne.noise_factors
    }
    cal_stats = tuple(Z.circuit_statistics(c) for c in RO.calibration_circuits(n_qubits))
    circuits = {f"lambda_{f}": s for f, s in folded_stats.items()}
    circuits |= {"cal_all_zeros": cal_stats[0], "cal_all_ones": cal_stats[1]}

    # ---- exact stage: every gate-noise signature x noise factor (parallel)
    t = time.perf_counter()
    keys = {}
    for prof in conds.values():
        keys.setdefault(gate_key(prof), prof)
    jobs = [(k, f) for k in keys for f in study.zne.noise_factors]
    results = Parallel(n_jobs=n_jobs)(
        delayed(_exact_job)(fc.transpiled, values, keys[k], basis, f, seed) for k, f in jobs
    )
    gate = {job: r[0] for job, r in zip(jobs, results, strict=True)}
    for (k, f), r in zip(jobs, results, strict=True):
        name = keys[k].profile_id if k is not None else "clean"
        timings[f"exact_{name}_lambda{f}_simulator_s"] = r[1]
    probs: dict[str, dict[int, np.ndarray]] = {}
    cal_exact: dict[str, tuple[np.ndarray, np.ndarray]] = {}
    for cond, prof in conds.items():
        k = gate_key(prof)
        probs[cond] = {
            f: (
                apply_readout(gate[(k, f)], prof.readout_p01, prof.readout_p10)
                if prof.has_readout
                else gate[(k, f)]
            )
            for f in study.zne.noise_factors
        }
        cal_exact[cond] = _calibration_exact(prof, basis, n_qubits)
    timings["exact_stage_wall_s"] = time.perf_counter() - t

    # ---- run-time checks 1-4
    clean_s = D.fraud_score(probs["clean"][1])
    tau = M.max_f1_threshold(y, clean_s)
    validation["frozen_tau"] = {
        "recomputed": tau,
        "registered": study.frozen_tau,
        "passed": abs(tau - study.frozen_tau) <= 1e-12,
    }
    if not validation["frozen_tau"]["passed"]:
        raise StudyStopped("frozen threshold does not reproduce")
    tau = study.frozen_tau
    dev = max(
        float(np.max(np.abs(gate[(None, f)] - gate[(None, 1)])))
        for f in study.zne.noise_factors
        if f != 1
    )
    validation["ideal_computation_preserved"] = {
        "max_abs_prob_diff_clean_folded_vs_unfolded": dev,
        "tolerance": study.validation.ideal_unitary_tol,
        "passed": dev <= study.validation.ideal_unitary_tol,
    }
    exposure = {}
    for cond, prof in conds.items():
        if has_gate_noise(prof):
            m = [float(np.abs(D.parity_z(probs[cond][f])).mean()) for f in study.zne.noise_factors]
            exposure[cond] = {"mean_abs_z": m, "strictly_decreasing": m[0] > m[1] > m[2]}
    validation["noise_exposure"] = {
        "conditions": exposure,
        "passed": all(e["strictly_decreasing"] for e in exposure.values()),
    }

    # ---- exact diagnostics
    t = time.perf_counter()
    w_lin = Z.extrapolation_weights(study.zne.noise_factors, study.zne.primary_extrapolator)
    w_rich = Z.extrapolation_weights(study.zne.noise_factors, "richardson")
    clean_flag = clean_s >= tau
    clean_z = D.parity_z(probs["clean"][1])
    boot_seed = vqc_val_bootstrap_seed(spec.seeds, dataset.dataset_id)
    exact: dict[str, dict] = {}
    for cond, prof in conds.items():
        cal = RO.estimate_calibration(*cal_exact[cond])
        vecs, info = action_scores(
            probs[cond],
            cal,
            true_calibration(prof, n_qubits),
            w_lin,
            w_rich,
            study.readout.min_assignment_determinant,
        )
        metrics = {
            v: outcome_metrics(y, s, tau, clean_s, clean_flag, study.top_k, study.ece_bins)
            for v, s in vecs.items()
        }
        for v, s in vecs.items():
            metrics[v]["max_abs_z_vs_clean"] = float(np.max(np.abs((1 - 2 * s) - clean_z)))
            metrics[v]["max_abs_z_vs_none"] = float(
                np.max(np.abs((1 - 2 * s) - (1 - 2 * vecs["A0"])))
            )
            metrics[v] |= {f"diag_{k}": val for k, val in info.get(v, {}).items()}
        intervals = D.paired_bootstrap(
            y,
            vecs["A0"],
            {v: vecs[v] for v in EXACT_VECTORS if v != "A0"},
            study.bootstrap_resamples,
            boot_seed,
            study.ece_bins,
            confidence=study.g2.confidence,
            n_jobs=n_jobs,
        )
        exact[cond] = {
            "metrics": metrics,
            "intervals": intervals,
            "calibration": {"p01": cal.p01.tolist(), "p10": cal.p10.tolist()},
            "scores": vecs,
        }
    timings["exact_diagnostics_s"] = time.perf_counter() - t
    validation["phase3b_crosscheck"] = _phase3b_crosscheck(
        root, {c: e["metrics"] for c, e in exact.items()}, study.validation.phase3b_crosscheck_tol
    )
    validation["negative_controls"] = _negative_controls(exact, conds, study)
    hard = (
        "ideal_computation_preserved",
        "noise_exposure",
        "phase3b_crosscheck",
        "negative_controls",
    )
    status = "completed"
    failed = [k for k in hard if not validation[k]["passed"]]
    context = {
        **verified,
        "rows": len(val),
        "frauds": int(y.sum()),
        "artifact_file_sha256_before": before,
        "experiment_config_hash": resolved.config_hash(),
        "study_config_hash": _hash(study),
        "frozen_tau": tau,
    }
    run = MitigationRun(study, conds, y, tau, circuits, validation, exact, context, timings, status)
    run.costs = [
        {
            "arm": b.arm_id,
            "shots_per_circuit": b.shots_per_circuit,
            "vector": v,
            **action_costs(v, b.shots_per_circuit, len(val), folded_stats, cal_stats),
        }
        for b in study.shot_budgets
        for v in VECTORS
    ]
    if failed:
        run.status = "stopped_" + "+".join(failed)
        return _finish(run, root, before, t_all)

    # ---- E08 on folded circuits + calibration checks
    t = time.perf_counter()
    validation["e08_folded"] = {}
    for pid in study.e08.profiles:
        prof = conds[pid]
        model = gate_noise_model(prof, basis, include_readout=True)
        for f in study.validation.e08_noise_factors:
            folded = Z.fold_global(fc.transpiled, f, basis, seed)
            aer_seed = derive_seed(spec.seeds.shots, "shots", study.e08.seed_key, pid, f, "aer") % (
                2**32
            )
            n = study.e08.n_rows
            aer = S.direct_aer_counts(folded, values[:n], model, study.e08.shots, aer_seed)
            rng = make_rng(spec.seeds.shots, "shots", study.e08.seed_key, pid, f, "multinomial")
            ex = probs[pid][f][:n]
            mult = S.sample_counts(ex, study.e08.shots, rng)
            validation["e08_folded"][f"{pid}_lambda{f}"] = S.e08_tests(
                ex, aer, mult, study.e08.shots, study.e08
            )
    validation["calibration_circuits"] = {}
    for pid in study.validation.calibration_check_profiles:
        prof = conds[pid]
        model = gate_noise_model(prof, basis, include_readout=True)
        for name, circ, ex in zip(
            ("all_zeros", "all_ones"),
            RO.calibration_circuits(n_qubits),
            cal_exact[pid],
            strict=True,
        ):
            aer_seed = derive_seed(spec.seeds.shots, "shots", "p4-calcheck", pid, name) % (2**32)
            shots_n = study.validation.calibration_check_shots
            counts = S.direct_aer_counts(circ, np.zeros((1, 0)), model, shots_n, aer_seed)
            stat, dof, p = S.merged_chi2(counts, ex[None, :], shots_n, study.e08.min_expected_count)
            validation["calibration_circuits"][f"{pid}_{name}"] = {
                "chi2": stat,
                "dof": dof,
                "p": p,
                "passed": p >= study.validation.calibration_chi2_p_min,
            }
    timings["validation_direct_shots_s"] = time.perf_counter() - t
    sampler_ok = all(r["passed"] for r in validation["e08_folded"].values()) and all(
        r["passed"] for r in validation["calibration_circuits"].values()
    )
    validation["sampler_validation_passed"] = sampler_ok
    if not sampler_ok:
        run.status = "stopped_sampler_validation"
        return _finish(run, root, before, t_all)

    # ---- finite-shot study (parallel over condition x arm)
    t = time.perf_counter()
    rep_draws = make_rng(spec.seeds.bootstrap, "bootstrap", "p4-replicate-draw").integers(
        0, study.replicates, study.bootstrap_resamples
    )
    outs = Parallel(n_jobs=n_jobs)(
        delayed(run_context)(
            cond,
            b.arm_id,
            b.shots_per_circuit,
            probs[cond],
            cal_exact[cond],
            true_calibration(conds[cond], n_qubits),
            y,
            clean_s,
            tau,
            study,
            spec.seeds.shots,
            boot_seed,
            rep_draws,
        )
        for cond in study.conditions
        for b in study.shot_budgets
    )
    timings["finite_shot_wall_s"] = time.perf_counter() - t
    for o in outs:
        run.replicate_rows += o["rows"]
        run.calibration_rows += o["calibration"]
        run.intervals[(o["condition"], o["arm"])] = o["intervals"]
        for k, v in o["timing"].items():
            timings[f"finite_{o['condition']}_{o['arm']}_{k}"] = v
    run.analysis = analyse(run)
    return _finish(run, root, before, t_all)


def _finish(run: MitigationRun, root: Path, before: str, t_all: float) -> MitigationRun:
    after = file_sha256(root / run.study.model.artifact)
    run.context["artifact_file_sha256_after"] = after
    if after != before:
        raise StudyStopped("the frozen artifact changed during the run")
    run.timings["total_wall_s"] = time.perf_counter() - t_all
    return run


def _hash(obj) -> str:
    return stable_hash(obj)


def _negative_controls(exact, conds, study) -> dict:
    tol_s, tol_m = (
        study.validation.negative_control_score_tol,
        study.validation.negative_control_metric_tol,
    )
    out = {}
    for cond, prof in conds.items():
        m = exact[cond]["metrics"]
        pure_readout = prof.has_readout and not has_gate_noise(prof)
        if pure_readout:  # NC1: A1 (infinite-shot calibration) recovers clean; NC3: A2 = A0
            out[f"NC1_{cond}"] = {
                "max_abs_z_A1_vs_clean": m["A1"]["max_abs_z_vs_clean"],
                "passed": m["A1"]["max_abs_z_vs_clean"] <= tol_s,
            }
            out[f"NC3_{cond}"] = {
                "max_abs_z_A2_vs_A0": m["A2"]["max_abs_z_vs_none"],
                "passed": m["A2"]["max_abs_z_vs_none"] <= tol_s,
            }
            if prof.readout_symmetric:
                d_auprc = abs(m["A1"]["auprc"] - m["A0"]["auprc"])
                d_auroc = abs(m["A1"]["auroc"] - m["A0"]["auroc"])
                out[f"NC1_H4.2_{cond}"] = {
                    "abs_delta_auprc": d_auprc,
                    "abs_delta_auroc": d_auroc,
                    "passed": d_auprc <= tol_m and d_auroc <= tol_m,
                }
        if cond == "clean":  # NC2: A2 under clean = clean; NC4: A1 under clean = identity
            out["NC2_clean"] = {
                "max_abs_z_A2_vs_clean": m["A2"]["max_abs_z_vs_clean"],
                "passed": m["A2"]["max_abs_z_vs_clean"] <= tol_s,
            }
            out["NC4_clean"] = {
                "max_abs_z_A1_vs_clean": m["A1"]["max_abs_z_vs_clean"],
                "passed": m["A1"]["max_abs_z_vs_clean"] <= tol_s,
            }
    return {"checks": out, "passed": all(c["passed"] for c in out.values())}


# ------------------------------------------------------------------------ analysis


def replicate_frame(run: MitigationRun) -> pd.DataFrame:
    return pd.DataFrame(run.replicate_rows)


def deltas(run: MitigationRun) -> pd.DataFrame:
    """Per (condition, arm, comparison, metric): replicate mean, quantiles, bootstrap CI."""
    rep = replicate_frame(run)
    metrics = (
        *BOOT_METRICS,
        "f2",
        "crossing_all",
        "crossing_fraud",
        "crossing_legit",
        "spearman",
        "kendall",
        *[f"top{k}_overlap" for k in run.study.top_k],
    )
    rows = []
    for (cond, arm), grp in rep.groupby(["condition", "arm"], sort=False):
        piv = {v: g.sort_values("replicate") for v, g in grp.groupby("vector")}
        for a, ref in REPLICATE_COMPARISONS:
            for m in metrics:
                d = piv[a][m].to_numpy() - piv[ref][m].to_numpy()
                row = {
                    "condition": cond,
                    "arm": arm,
                    "action": a,
                    "comparator": ref,
                    "metric": m,
                    "mean_delta": d.mean(),
                    "replicate_q05": np.quantile(d, 0.05),
                    "replicate_q50": np.quantile(d, 0.50),
                    "replicate_q95": np.quantile(d, 0.95),
                    "comparator_mean": piv[ref][m].mean(),
                    "action_mean": piv[a][m].mean(),
                    "ci_low": np.nan,
                    "ci_high": np.nan,
                    "diagnostic": a in DIAGNOSTIC_VECTORS or ref in DIAGNOSTIC_VECTORS,
                }
                ci = run.intervals[(cond, arm)].get((a, ref), {}).get(m)
                if ci is not None:
                    row["ci_low"], row["ci_high"] = ci
                rows.append(row)
    return pd.DataFrame(rows)


def _rrb(row, g2) -> tuple[bool, bool]:
    """(benefit, harm) of one action-vs-comparator delta row on a G2 endpoint."""
    d, lo, hi = row["mean_delta"], row["ci_low"], row["ci_high"]
    if row["metric"] == "auprc":
        return d >= g2.min_delta_auprc and lo > 0, d <= -g2.min_delta_auprc and hi < 0
    if row["metric"] == "f1":
        return d >= g2.min_delta_f1_at_tau and lo > 0, d <= -g2.min_delta_f1_at_tau and hi < 0
    if row["metric"] == "brier":
        lim = g2.min_relative_brier * row["comparator_mean"]
        return d <= -lim and hi < 0, d >= lim and lo > 0
    raise ValueError(row["metric"])


def analyse(run: MitigationRun) -> dict:
    study, g2 = run.study, run.study.g2
    dl = deltas(run)
    rep = replicate_frame(run)
    cells = []
    for cond in study.conditions:
        for b in study.shot_budgets:
            for a in ("A1", "A2", "A3"):
                ref = resource_matched_comparator(a)
                label = study.applicability[cond][a]
                for e in G2_ENDPOINTS:
                    row = dl[
                        (dl.condition == cond)
                        & (dl.arm == b.arm_id)
                        & (dl.action == a)
                        & (dl.comparator == ref)
                        & (dl.metric == e)
                    ].iloc[0]
                    benefit, harm = _rrb(row, g2)
                    cells.append(
                        {
                            "condition": cond,
                            "arm": b.arm_id,
                            "action": a,
                            "comparator": ref,
                            "applicability": label,
                            "qualifying": label in ("applicable", "partial"),
                            "endpoint": e,
                            "mean_delta": row["mean_delta"],
                            "ci_low": row["ci_low"],
                            "ci_high": row["ci_high"],
                            "comparator_mean": row["comparator_mean"],
                            "rrb_benefit": bool(benefit),
                            "rrb_harm": bool(harm),
                        }
                    )
    cells = pd.DataFrame(cells)
    best = best_actions(rep, study)
    g2_out = g2_verdict(cells, best, g2)
    return {
        "cells": cells,
        "best": best,
        "deltas": dl,
        "g2": g2_out,
        "hypotheses": hypotheses(run, cells, best, dl),
    }


def g2_verdict(cells: pd.DataFrame, best: pd.DataFrame, g2) -> dict:
    """The registered G2 rule (PREREG_P4 §13) on the cell table and Table D."""
    q = cells[cells.qualifying]
    any_rrb = bool(q.rrb_benefit.any())
    constant = all(best[best.endpoint == e].best_action.nunique() == 1 for e in G2_ENDPOINTS)
    auprc_cells = q[(q.endpoint == "auprc") & q.rrb_benefit]
    clean_flag = cells[
        (cells.condition == "clean") & (cells.endpoint == "auprc") & cells.rrb_benefit
    ]
    if not any_rrb or constant:
        verdict = "FAIL"
    elif len(auprc_cells) >= g2.pass_min_auprc_cells:
        verdict = "PASS"
    else:
        verdict = "CONDITIONAL PASS"
    cols = ["condition", "arm", "action", "endpoint"]
    return {
        "verdict": verdict if clean_flag.empty else "NOT ISSUED (clean negative-control flag)",
        "computed_verdict": verdict,
        "qualifying_cells_with_rrb": q[q.rrb_benefit][cols].to_dict("records"),
        "auprc_rrb_cells": auprc_cells[cols[:3]].to_dict("records"),
        "fail_clause_i_no_rrb": not any_rrb,
        "fail_clause_ii_table_d_constant": constant,
        "clean_negative_control_flags": clean_flag[["arm", "action"]].to_dict("records"),
        "negative_control_cells_with_rrb": cells[(~cells.qualifying) & cells.rrb_benefit][
            cols
        ].to_dict("records"),
    }


def best_actions(rep: pd.DataFrame, study: MitigationStudyConfig) -> pd.DataFrame:
    g2 = study.g2
    rows = []
    means = (
        rep[rep.vector.isin(COST_ORDER)]
        .groupby(["condition", "arm", "vector"])[list(G2_ENDPOINTS)]
        .mean()
    )
    for cond in study.conditions:
        for b in study.shot_budgets:
            m = means.loc[(cond, b.arm_id)]
            for e in G2_ENDPOINTS:
                vals = m[e]
                if e == "brier":
                    top = vals.min()
                    ok = [a for a in COST_ORDER if vals[a] <= top * (1 + g2.min_relative_brier)]
                else:
                    tol = g2.min_delta_auprc if e == "auprc" else g2.min_delta_f1_at_tau
                    top = vals.max()
                    ok = [a for a in COST_ORDER if vals[a] >= top - tol]
                rows.append(
                    {
                        "condition": cond,
                        "arm": b.arm_id,
                        "endpoint": e,
                        "best_action": ok[0],
                        "best_mean_value": top,
                        **{f"mean_{a}": vals[a] for a in COST_ORDER},
                        "rule": "cheapest action within the minimum effect of the best mean",
                    }
                )
    return pd.DataFrame(rows)


def hypotheses(run: MitigationRun, cells, best, dl) -> dict:
    ro = ["ro-sym-high", "ar-020", "ar-050"]
    h41 = cells[cells.condition.isin(ro) & (cells.action == "A1") & (cells.endpoint == "brier")]
    n41 = int(h41.rrb_benefit.sum())
    nc = run.validation["negative_controls"]["checks"]
    exact42 = nc.get("NC1_H4.2_ro-sym-high", {}).get("passed", False) and nc.get(
        "NC1_ro-sym-high", {}
    ).get("passed", False)
    fin42 = dl[
        (dl.condition == "ro-sym-high")
        & (dl.action == "A1")
        & (dl.comparator == "A0")
        & (dl.metric == "auprc")
    ]
    fin42_ok = bool(((fin42.ci_low <= 0) & (fin42.ci_high >= 0)).all())
    gate = ["dep-high", "th-high", "comb-medium", "comb-high"]
    h43 = cells[
        (cells.endpoint == "auprc")
        & cells.rrb_benefit
        & (
            (cells.condition.isin(gate) & cells.action.isin(["A2", "A3"]))
            | (cells.condition.isin(["comb-medium", "comb-high"]) & (cells.action == "A1"))
        )
    ]
    q = cells[cells.qualifying]
    varies = any(g.rrb_benefit.nunique() > 1 for _, g in q.groupby(["action", "endpoint"]))
    table_d_varies = any(best[best.endpoint == e].best_action.nunique() > 1 for e in G2_ENDPOINTS)
    ranges = {
        f"{a}_{e}": float(np.ptp(g.mean_delta)) for (a, e), g in q.groupby(["action", "endpoint"])
    }
    costly = q[q.action.isin(["A2", "A3"])]
    no_benefit = []
    for (c, arm, a), g in costly.groupby(["condition", "arm", "action"]):
        if not g.rrb_benefit.any() or g.rrb_harm.any():
            no_benefit.append(
                {"condition": c, "arm": arm, "action": a, "harm": bool(g.rrb_harm.any())}
            )
    return {
        "H4.1": {
            "cells_with_brier_rrb": n41,
            "of": len(h41),
            "outcome": "supported" if n41 == len(h41) else ("partial" if n41 else "not supported"),
        },
        "H4.2": {
            "exact_negative_control": bool(exact42),
            "finite_shot_ci_contains_zero_both_arms": fin42_ok,
            "outcome": "supported" if exact42 and fin42_ok else "not supported",
        },
        "H4.3": {
            "auprc_rrb_cells": h43[["condition", "arm", "action"]].to_dict("records"),
            "outcome": "supported" if len(h43) else "not supported",
            "prior_expectation": "not supported against RM3 (PREREG_P4 §14b)",
        },
        "H4.4": {
            "table_d_varies": table_d_varies,
            "rrb_status_varies": varies,
            "range_of_mean_delta_across_contexts": ranges,
            "outcome": "supported" if table_d_varies and varies else "not supported",
        },
        "H4.5": {
            "costly_cells_without_benefit_or_with_harm": no_benefit,
            "outcome": "supported" if no_benefit else "not supported",
        },
    }
