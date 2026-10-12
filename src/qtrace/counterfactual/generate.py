"""Phase 5B counterfactual generation: every model × condition × shot budget × replicate × action.

One isolated job per model (parallel). Each job reads nothing shared and writes only its
own parquet file; the parent merges the files in sorted order (deterministic). Draws are
paired within a context replicate exactly as in Phase 4 (common random numbers): A0, A1,
A2, A3 share the scale-1 draw; A4 (extra shots, 3S) and the RM9 diagnostic extend it
(nested); the readout probe is the calibration A1/A3 reuse; the gate probe uses its own
draws on fixed synthetic bindings.
"""

from __future__ import annotations

import hashlib
import io
import time
from pathlib import Path

import numpy as np
import pandas as pd

from qtrace.config.schemas import CounterfactualStudyConfig, MitigationStudyConfig, NoiseProfile
from qtrace.counterfactual import probes as PR
from qtrace.counterfactual.pool_models import BASIS, PoolModel
from qtrace.mitigation import readout as RO
from qtrace.mitigation import zne as Z
from qtrace.mitigation.costs import action_costs
from qtrace.mitigation.study import draw_context, gate_key, outcome_metrics
from qtrace.noise import shots as S
from qtrace.noise.exact import exact_distributions
from qtrace.noise.models import apply_readout, gate_noise_model, has_gate_noise
from qtrace.qml.model import predict
from qtrace.qml.simulate import feature_states
from qtrace.utils.seeds import make_rng

ACTIONS = ("A0", "A1", "A2", "A3", "A4")
VECTORS = (*ACTIONS, "RM9")
COST_NAME = {"A0": "A0", "A1": "A1", "A2": "A2", "A3": "A3", "A4": "RM3", "RM9": "RM9"}
KEYS = ("model_id", "condition", "arm", "replicate", "action")


def score(freq: np.ndarray, diagonal: np.ndarray) -> np.ndarray:
    return np.clip((1.0 - freq @ diagonal) / 2.0, 0.0, 1.0)


def action_vectors(freqs, extra, cal, diagonal, w_lin, min_det) -> tuple[dict, dict]:
    """A0-A4 and RM9 from per-factor frequencies, for any Z-type diagonal observable."""
    factors = sorted(freqs)
    z_raw = np.array([freqs[f] @ diagonal for f in factors])
    mit, info = {}, {}
    for f in factors:
        mit[f], info[f] = RO.mitigate(freqs[f], cal, min_det)
    z_mit = np.array([mit[f] @ diagonal for f in factors])
    z2, clip2 = Z.extrapolate(z_raw, w_lin)
    z3, clip3 = Z.extrapolate(z_mit, w_lin)
    out = {
        "A0": np.clip((1 - z_raw[0]) / 2, 0, 1),
        "A1": np.clip((1 - z_mit[0]) / 2, 0, 1),
        "A2": np.clip((1 - z2) / 2, 0, 1),
        "A3": np.clip((1 - z3) / 2, 0, 1),
        "A4": score(extra["RM3"], diagonal),
    }
    if "RM9" in extra:  # Phase 5B diagnostic only (Phase 5C does not draw it)
        out["RM9"] = score(extra["RM9"], diagonal)
    diag = {
        "A1": {"rows_projected": info[1].rows_projected, "unstable": info[1].unstable},
        "A2": {"clip_fraction": clip2},
        "A3": {
            "clip_fraction": clip3,
            "rows_projected": sum(info[f].rows_projected for f in factors),
            "unstable": any(info[f].unstable for f in factors),
        },
    }
    return out, diag


def calibration_exact(profile: NoiseProfile) -> tuple[np.ndarray, np.ndarray]:
    model = gate_noise_model(profile, BASIS) if has_gate_noise(profile) else None
    out = []
    for circ in RO.calibration_circuits(4):
        d = exact_distributions(circ, np.zeros((1, 0)), model)
        if profile.has_readout:
            d = apply_readout(d, profile.readout_p01, profile.readout_p10)
        out.append(d[0])
    return out[0], out[1]


def _with_readout(dist: np.ndarray, p: NoiseProfile) -> np.ndarray:
    return apply_readout(dist, p.readout_p01, p.readout_p10) if p.has_readout else dist


def run_model(
    m: PoolModel,
    angles: np.ndarray,
    y: np.ndarray,
    probe_ang: np.ndarray,
    profiles: dict[str, NoiseProfile],
    cal_exact: dict[str, tuple[np.ndarray, np.ndarray]],
    study: CounterfactualStudyConfig,
    mit: MitigationStudyConfig,
    shots_master: int,
    out_dir: Path | None = None,
    conditions: tuple[str, ...] | None = None,
    arms: tuple[str, ...] | None = None,
    replicates: tuple[int, ...] | None = None,
) -> dict:
    """All (condition, arm, replicate, action) rows of one model on its own panel."""
    t_start = time.perf_counter()
    conditions = conditions or study.conditions
    budgets = [b for b in study.shot_budgets if arms is None or b.arm_id in arms]
    reps = replicates if replicates is not None else tuple(range(study.replicates))
    tc, diag_obs = m.transpiled, m.diagonal
    seed = m.circuit["transpile_seed"]
    values = m.values(angles)
    probe_values = m.values(probe_ang)
    head = study.validation_head_rows
    tol = study.validation_tol
    timings: dict[str, float] = {}

    # ---- exact distributions (panel and probe bindings) per gate signature
    t = time.perf_counter()
    exact: dict[tuple, dict[int, np.ndarray]] = {}
    probe_exact: dict[tuple, dict[int, np.ndarray]] = {}
    needed = {gate_key(profiles[c]): profiles[c] for c in conditions} | {None: profiles["clean"]}
    for key, prof in needed.items():
        model = gate_noise_model(prof, BASIS) if key is not None else None
        if key is None:  # clean folding is the identity (validated in Phase 4 and below)
            base = exact_distributions(tc, values, None)
            exact[key] = {1: base, 3: base, 5: base}
        else:
            exact[key] = {
                f: exact_distributions(Z.fold_global(tc, f, BASIS, seed), values, model)
                for f in mit.zne.noise_factors
            }
        probe_exact[key] = {
            f: exact_distributions(Z.fold_global(tc, f, BASIS, seed), probe_values, model)
            for f in study.gate_probe.noise_factors
        }
    timings["exact_s"] = time.perf_counter() - t

    # ---- validation (registered run-time checks; cheap)
    engine = predict(m.ansatz, feature_states(m.fmap, angles[:head]), m.theta, diag_obs)
    clean1 = exact[None][1]
    validation = {
        "aer_clean_vs_engine_max_abs_dz": float(
            np.max(np.abs(clean1[:head] @ diag_obs - (1 - 2 * engine)))
        ),
        "clean_folded_vs_unfolded_max_abs_dp": max(
            float(
                np.max(
                    np.abs(
                        exact_distributions(Z.fold_global(tc, f, BASIS, seed), values[:head], None)
                        - clean1[:head]
                    )
                )
            )
            for f in (3, 5)
        ),
    }
    exposure = {}
    for key, prof in needed.items():
        if key is not None:
            vals = [float(np.abs(exact[key][f] @ diag_obs).mean()) for f in mit.zne.noise_factors]
            exposure[prof.profile_id] = vals[0] > vals[1] > vals[2]
    validation["noise_exposure_decreasing"] = all(exposure.values()) if exposure else True
    if "ro-sym-high" in conditions:
        p = profiles["ro-sym-high"]
        cal = RO.estimate_calibration(*cal_exact["ro-sym-high"])
        rec, _ = RO.mitigate(_with_readout(clean1, p), cal, mit.readout.min_assignment_determinant)
        validation["exact_a1_symmetric_readout_recovers_clean"] = float(
            np.max(np.abs((rec - clean1) @ diag_obs))
        )
    validation["passed"] = (
        validation["aer_clean_vs_engine_max_abs_dz"] <= tol
        and validation["clean_folded_vs_unfolded_max_abs_dp"] <= tol
        and validation["noise_exposure_decreasing"]
        and validation.get("exact_a1_symmetric_readout_recovers_clean", 0.0) <= tol
    )

    # ---- finite-shot counterfactuals
    t = time.perf_counter()
    w_lin = Z.extrapolation_weights(mit.zne.noise_factors, mit.zne.primary_extrapolator)
    clean_s = score(clean1, diag_obs)
    clean_flag = clean_s >= m.tau
    n_rows, n_fraud = len(y), int(y.sum())
    top_k = (n_fraud, 100, int(round(0.01 * n_rows)))
    rows = []
    for cond in conditions:
        prof = profiles[cond]
        key = gate_key(prof)
        probs = {f: _with_readout(exact[key][f], prof) for f in mit.zne.noise_factors}
        pprobs = {
            f: _with_readout(probe_exact[key][f], prof) for f in study.gate_probe.noise_factors
        }
        for b in budgets:
            shots = b.shots_per_circuit
            for rep in reps:

                def rng(component, cond=cond, arm=b.arm_id, rep=rep):
                    return make_rng(
                        shots_master, "shots", study.seed_key, m.model_id, cond, arm, rep, component
                    )

                draws = draw_context(probs, cal_exact[cond], shots, mit.zne.noise_factors, rng)
                pc = {
                    f: S.sample_counts(pprobs[f], shots, rng(f"probe{f}"))
                    for f in study.gate_probe.noise_factors
                }
                cal = RO.estimate_calibration(draws["cal0"], draws["cal1"])
                freqs = {f: draws[f"lam{f}"] / shots for f in mit.zne.noise_factors}
                extra = {"RM3": draws["rm3"] / (3 * shots), "RM9": draws["rm9"] / (9 * shots)}
                vecs, info = action_vectors(
                    freqs, extra, cal, diag_obs, w_lin, mit.readout.min_assignment_determinant
                )
                probe = PR.readout_features(draws["cal0"], draws["cal1"], shots)
                probe |= PR.gate_features(pc[1], pc[3], diag_obs, shots)
                for v in VECTORS:
                    row = {
                        "model_id": m.model_id,
                        "struct_id": m.struct_id,
                        "seed_index": m.seed_index,
                        "split": m.split,
                        "partition": m.partition,
                        "condition": cond,
                        "arm": b.arm_id,
                        "shots_per_circuit": shots,
                        "replicate": rep,
                        "action": v,
                    }
                    row |= outcome_metrics(y, vecs[v], m.tau, clean_s, clean_flag, top_k, 10)
                    d = info.get(v, {})
                    row["clip_fraction"] = float(d.get("clip_fraction", 0.0))
                    row["rows_projected"] = int(d.get("rows_projected", 0))
                    row["unstable"] = bool(d.get("unstable", False))
                    rows.append(row | probe)
    timings["finite_shot_s"] = time.perf_counter() - t
    frame = pd.DataFrame(rows).sort_values(list(KEYS), kind="stable").reset_index(drop=True)
    out = {
        "model_id": m.model_id,
        "rows": len(frame),
        "validation": validation,
        "timings": timings | {"total_s": time.perf_counter() - t_start},
        "panel": {"rows": n_rows, "frauds": n_fraud},
    }
    if out_dir is not None:
        path = out_dir / f"{m.model_id}.parquet"
        frame.to_parquet(path, index=False)
        out["path"] = str(path)
    else:
        out["frame"] = frame
    return out


def costs_table(
    models: list[PoolModel], study: CounterfactualStudyConfig, panel_rows: dict[str, int]
) -> pd.DataFrame:
    """Raw resources per model x arm x vector (standalone action costs; probe cost separate)."""
    cal_stats = tuple(Z.circuit_statistics(c) for c in RO.calibration_circuits(4))
    rows = []
    for m in models:
        n = panel_rows[m.partition]
        for b in study.shot_budgets:
            probe = PR.probe_costs(
                b.shots_per_circuit, study.gate_probe.bindings, m.folded_stats, cal_stats, n
            )
            for v in VECTORS:
                c = action_costs(COST_NAME[v], b.shots_per_circuit, n, m.folded_stats, cal_stats)
                rows.append(
                    {
                        "model_id": m.model_id,
                        "arm": b.arm_id,
                        "action": v,
                        **c,
                        **{k: val for k, val in probe.items()},
                    }
                )
    return pd.DataFrame(rows)


def merge(paths: list[Path]) -> pd.DataFrame:
    """Deterministic merge of isolated per-model files (independent of completion order)."""
    frames = [pd.read_parquet(p) for p in sorted(paths, key=lambda p: p.name)]
    out = pd.concat(frames, ignore_index=True)
    out = out.sort_values(list(KEYS), kind="stable").reset_index(drop=True)
    if out.duplicated(list(KEYS)).any():
        raise RuntimeError("duplicate context/action rows")
    return out


def content_sha256(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n")
    return hashlib.sha256(buffer.getvalue().encode()).hexdigest()
