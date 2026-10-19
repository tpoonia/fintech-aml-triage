"""Phase 5C generation: every model x noise point x shot budget x replicate x action (A0-A4).

One isolated job per model, as in Phase 5B. Inside a job the gate plots are processed one
at a time: the exact noisy distributions of a plot (factors 1, 3, 5; panel and probe
bindings) are computed once and shared by the plot's readout points, whose readout noise is
applied classically. Draws are paired and nested exactly as in Phase 4/5B (A0-A3 share the
scale-1 draw; A4 extends it with 2S shots); RM9 is not drawn in Phase 5C.
"""

from __future__ import annotations

import time
from pathlib import Path

import numpy as np
import pandas as pd

from qtrace.config.schemas import (
    CounterfactualStudyConfig,
    MitigationStudyConfig,
    MixedNoiseStudyConfig,
)
from qtrace.counterfactual import probes as PR
from qtrace.counterfactual.generate import _with_readout, action_vectors
from qtrace.counterfactual.mixed import profile_of
from qtrace.counterfactual.pool_models import BASIS, PoolModel
from qtrace.evaluation import metrics as M
from qtrace.mitigation import readout as RO
from qtrace.mitigation import zne as Z
from qtrace.noise import shots as S
from qtrace.noise.exact import exact_distributions
from qtrace.noise.models import gate_noise_model, has_gate_noise
from qtrace.qml.model import predict
from qtrace.qml.simulate import feature_states
from qtrace.utils.seeds import make_rng

ACTIONS = ("A0", "A1", "A2", "A3", "A4")
KEYS = ("model_id", "point_id", "arm", "replicate", "action")
METRICS = ("brier", "ece", "auprc", "auroc", "precision", "recall", "f1", "f2")


def outcome_metrics(y: np.ndarray, s: np.ndarray, tau: float, bins: int = 10) -> dict:
    """The Phase 5C endpoints (Brier primary; ranking diagnostics are not computed)."""
    return {
        "brier": M.brier(y, s),
        "ece": M.expected_calibration_error(y, s, bins, "uniform"),
        "auprc": M.average_precision(y, s),
        "auroc": M.roc_auc(y, s),
        **M.threshold_metrics(y, s, tau),
    }


def draw_mixed(probs, cal_exact, shots: int, factors, rng) -> dict[str, np.ndarray]:
    """Phase 4 paired draws without RM9: lam_f (S each), A4 = lam1 + 2S, calibration (S each)."""
    out = {f"lam{f}": S.sample_counts(probs[f], shots, rng(f"lam{f}")) for f in factors}
    out["rm3"] = out["lam1"] + S.sample_counts(probs[1], 2 * shots, rng("rm_extra2"))
    out["cal0"] = S.sample_counts(cal_exact[0][None, :], shots, rng("cal0"))[0]
    out["cal1"] = S.sample_counts(cal_exact[1][None, :], shots, rng("cal1"))[0]
    return out


def mean_tv(a: np.ndarray, b: np.ndarray) -> float:
    return float(0.5 * np.abs(a - b).sum(axis=1).mean())


def run_model_mixed(
    m: PoolModel,
    angles: np.ndarray,
    y: np.ndarray,
    probe_ang: np.ndarray,
    design: pd.DataFrame,
    cal_exact: dict[str, tuple[np.ndarray, np.ndarray]],
    study: MixedNoiseStudyConfig,
    base: CounterfactualStudyConfig,
    mit: MitigationStudyConfig,
    shots_master: int,
    out_dir: Path | None = None,
    points: tuple[str, ...] | None = None,
    arms: tuple[str, ...] | None = None,
    replicates: tuple[int, ...] | None = None,
) -> dict:
    """All (point, arm, replicate, action) rows of one model on its own controller panel."""
    t_start = time.perf_counter()
    design = design if points is None else design[design.point_id.isin(points)]
    budgets = [b for b in study.shot_budgets if arms is None or b.arm_id in arms]
    reps = replicates if replicates is not None else tuple(range(study.replicates))
    factors, pfactors = mit.zne.noise_factors, base.gate_probe.noise_factors
    tc, diag_obs, seed = m.transpiled, m.diagonal, m.circuit["transpile_seed"]
    values, probe_values = m.values(angles), m.values(probe_ang)
    head, tol = study.validation_head_rows, study.validation_tol
    w_lin = Z.extrapolation_weights(factors, mit.zne.primary_extrapolator)
    min_det = mit.readout.min_assignment_determinant

    # ---- clean reference and registered run-time checks (cheap; head rows)
    clean_head = exact_distributions(tc, values[:head], None)
    engine = predict(m.ansatz, feature_states(m.fmap, angles[:head]), m.theta, diag_obs)
    validation: dict = {
        "aer_clean_vs_engine_max_abs_dz": float(
            np.max(np.abs(clean_head @ diag_obs - (1 - 2 * engine)))
        ),
        "clean_folded_vs_unfolded_max_abs_dp": max(
            float(
                np.max(
                    np.abs(
                        exact_distributions(Z.fold_global(tc, f, BASIS, seed), values[:head], None)
                        - clean_head
                    )
                )
            )
            for f in factors[1:]
        ),
        "noise_amplification_monotone": {},
        "exact_a1_gate_free_recovers_clean": 0.0,
    }
    timings = {"exact_s": 0.0, "finite_shot_s": 0.0}
    rows = []
    for plot, pts in design.groupby("gate_plot", sort=True):
        t = time.perf_counter()
        gate_prof = profile_of(pts.iloc[0])
        noisy = has_gate_noise(gate_prof)
        model = gate_noise_model(gate_prof, BASIS) if noisy else None
        if noisy:
            exact = {
                f: exact_distributions(Z.fold_global(tc, f, BASIS, seed), values, model)
                for f in factors
            }
            tv = [mean_tv(exact[f][:head], clean_head) for f in factors]
            validation["noise_amplification_monotone"][plot] = bool(
                all(a < b for a, b in zip(tv, tv[1:], strict=False))
            )
        else:  # clean folding is the identity (validated above on the head rows)
            base_dist = exact_distributions(tc, values, None)
            exact = dict.fromkeys(factors, base_dist)
        probe_exact = {
            f: exact_distributions(Z.fold_global(tc, f, BASIS, seed), probe_values, model)
            for f in pfactors
        }
        timings["exact_s"] += time.perf_counter() - t
        t = time.perf_counter()
        for _, point in pts.iterrows():
            prof = profile_of(point)
            pid = point.point_id
            probs = {f: _with_readout(exact[f], prof) for f in factors}
            pprobs = {f: _with_readout(probe_exact[f], prof) for f in pfactors}
            if not noisy:  # exact tensored inversion recovers the clean distribution
                cal = RO.estimate_calibration(*cal_exact[pid])
                rec, _ = RO.mitigate(probs[1][:head], cal, min_det)
                validation["exact_a1_gate_free_recovers_clean"] = max(
                    validation["exact_a1_gate_free_recovers_clean"],
                    float(np.max(np.abs((rec - clean_head) @ diag_obs))),
                )
            for b in budgets:
                shots = b.shots_per_circuit
                for rep in reps:

                    def rng(component, pid=pid, arm=b.arm_id, rep=rep):
                        return make_rng(
                            shots_master,
                            "shots",
                            study.seed_key,
                            m.model_id,
                            pid,
                            arm,
                            rep,
                            component,
                        )

                    draws = draw_mixed(probs, cal_exact[pid], shots, factors, rng)
                    pc = {f: S.sample_counts(pprobs[f], shots, rng(f"probe{f}")) for f in pfactors}
                    cal = RO.estimate_calibration(draws["cal0"], draws["cal1"])
                    freqs = {f: draws[f"lam{f}"] / shots for f in factors}
                    vecs, info = action_vectors(
                        freqs, {"RM3": draws["rm3"] / (3 * shots)}, cal, diag_obs, w_lin, min_det
                    )
                    probe = PR.readout_features(draws["cal0"], draws["cal1"], shots)
                    probe |= PR.gate_features(pc[1], pc[3], diag_obs, shots)
                    for a in ACTIONS:
                        d = info.get(a, {})
                        rows.append(
                            {
                                "model_id": m.model_id,
                                "struct_id": m.struct_id,
                                "seed_index": m.seed_index,
                                "split": m.split,
                                "partition": m.partition,
                                "point_id": pid,
                                "gate_plot": plot,
                                "arm": b.arm_id,
                                "shots_per_circuit": shots,
                                "replicate": rep,
                                "action": a,
                                **outcome_metrics(y, vecs[a], m.tau),
                                "clip_fraction": float(d.get("clip_fraction", 0.0)),
                                "rows_projected": int(d.get("rows_projected", 0)),
                                "unstable": bool(d.get("unstable", False)),
                                **probe,
                            }
                        )
        timings["finite_shot_s"] += time.perf_counter() - t
        del exact, probe_exact
    mono = validation["noise_amplification_monotone"]
    validation["passed"] = bool(
        validation["aer_clean_vs_engine_max_abs_dz"] <= tol
        and validation["clean_folded_vs_unfolded_max_abs_dp"] <= tol
        and all(mono.values())
        and validation["exact_a1_gate_free_recovers_clean"] <= tol
    )
    frame = pd.DataFrame(rows).sort_values(list(KEYS), kind="stable").reset_index(drop=True)
    out = {
        "model_id": m.model_id,
        "rows": len(frame),
        "validation": validation,
        "timings": timings | {"total_s": time.perf_counter() - t_start},
        "panel": {"rows": len(y), "frauds": int(y.sum())},
    }
    if out_dir is not None:
        path = out_dir / f"{m.model_id}.parquet"
        frame.to_parquet(path, index=False)
        out["path"] = str(path)
    else:
        out["frame"] = frame
    return out


def merge(paths: list[Path]) -> pd.DataFrame:
    """Deterministic merge of the isolated per-model files (independent of completion order)."""
    frames = [pd.read_parquet(p) for p in sorted(paths, key=lambda p: p.name)]
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(list(KEYS), kind="stable").reset_index(drop=True)
    if out.duplicated(list(KEYS)).any():
        raise RuntimeError("duplicate context/action rows")
    return out
