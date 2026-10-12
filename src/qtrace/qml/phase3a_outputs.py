"""Configured Phase 3A run and its committed (aggregate, deterministic) outputs."""

from __future__ import annotations

import io
import json
import time
from dataclasses import dataclass
from importlib import metadata as importlib_metadata
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit_aer.primitives import EstimatorV2 as AerEstimator

from qtrace.classical.runner import EVAL, FIT, ConfigResult
from qtrace.config import load_experiment
from qtrace.config.schemas import ResolvedExperiment
from qtrace.data.access import load_partitions
from qtrace.data.partition import PARTITION
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.verify import verify_phase1
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import percentile_interval
from qtrace.qml import circuit as C
from qtrace.qml.model import fraud_probability
from qtrace.qml.phase3a import PHASE, Phase3AResults, run_phase3a
from qtrace.utils.hashing import stable_hash

EXPERIMENT_ID = "phase3a_vqc"
DIGITS = 6
CI = ("auprc", "auroc", "precision", "recall", "f1", "f2", "brier")
THRESHOLD_NOTE = "exploratory/optimistic: threshold selected and reported on vqc_val"


@dataclass
class Phase3ARun:
    resolved: ResolvedExperiment
    results: Phase3AResults
    context: dict
    aer_crosscheck: dict


def _software() -> dict[str, str]:
    names = ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn")
    return {n: importlib_metadata.version(n) for n in names}


def _aer_crosscheck(cfg, results: Phase3AResults, val: pd.DataFrame) -> tuple[dict, float]:
    """Replay the frozen VQC on Aer density_matrix (noiseless) for agreement and timing."""
    n = min(cfg.aer_crosscheck_examples, len(val))
    angles = results.encoder.transform(val.iloc[:n])
    tc, _ = C.transpiled_statistics(cfg, results.circuit_stats["transpile_seed"])
    theta = np.array(results.frozen.theta)
    named = {f"x[{i}]": angles[:, i] for i in range(cfg.n_qubits)}
    named |= {f"θ[{i}]": np.full(n, theta[i]) for i in range(len(theta))}
    values = np.column_stack([named[p.name] for p in tc.parameters])
    estimator = AerEstimator(options={"backend_options": {"method": "density_matrix"}})
    start = time.perf_counter()
    z = estimator.run([(tc, C.parity_observable(cfg.n_qubits).apply_layout(tc.layout), values)])
    z = z.result()[0].data.evs
    seconds = time.perf_counter() - start
    diff = float(np.max(np.abs(fraud_probability(z) - results.vqc.scores[:n])))
    return {"examples": n, "agrees_within_1e-10": diff < 1e-10}, seconds


def run_configured(root: Path) -> Phase3ARun:
    resolved = load_experiment(EXPERIMENT_ID)
    spec, dataset, cfg = resolved.spec, resolved.dataset, resolved.vqc
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, PHASE, [FIT, EVAL])  # controller partitions never read
    verified = verify_phase1(root, dataset.dataset_id, frame, fitted, (FIT, EVAL))
    provenance = {
        "dataset_sha256": dataset.expected_sha256,
        "preprocessing_sha256": fitted.artifact_sha256(),
        "software": _software(),
    }
    val = frame[frame[PARTITION] == EVAL].sort_values("row_id").reset_index(drop=True)
    results = run_phase3a(
        frame[frame[PARTITION] == FIT],
        val,
        cfg,
        resolved.baseline,
        spec.seeds,
        dataset_id=dataset.dataset_id,
        target=dataset.target_column,
        feature_columns=fitted.output_columns,
        provenance=provenance,
    )
    aer, aer_seconds = _aer_crosscheck(cfg, results, val)
    results.timings["aer_density_matrix_noiseless_s"] = aer_seconds
    results.timings["aer_density_matrix_per_example_ms"] = 1e3 * aer_seconds / aer["examples"]
    context = {
        "experiment_id": spec.experiment_id,
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": dataset.expected_sha256,
        "experiment_config_sha256": resolved.config_hash(),
        "vqc_config_sha256": stable_hash(cfg),
        "baseline_config_sha256": stable_hash(resolved.baseline),
        "phase1_verification": verified,
        "software": provenance["software"],
    }
    return Phase3ARun(resolved, results, context, aer)


# ------------------------------------------------------------------------------ tables


def _csv(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.round(DIGITS).to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def _row(r: ConfigResult, family: str, inputs: str) -> dict:
    row = {
        "model": r.model_id,
        "family": family,
        "inputs": inputs,
        "input_dim": 4,
        "n_train": r.n_train,
        "n_train_fraud": r.n_train_fraud,
    }
    for name, value in r.metrics.items():
        row[name] = value
        if name in CI:
            row[f"{name}_ci_low"], row[f"{name}_ci_high"] = r.intervals[name]
    return row


def _delta(a: ConfigResult, b: ConfigResult, confidence: float) -> tuple[float, float, float]:
    lo, hi = percentile_interval(a.auprc_samples - b.auprc_samples, confidence)
    return a.metrics["auprc"] - b.metrics["auprc"], lo, hi


def comparison_table(res: Phase3AResults, confidence: float) -> pd.DataFrame:
    rows = [_row(res.vqc, "quantum (clean VQC)", "top-4 angles")]
    for r in res.classical:
        row = _row(r, "classical", "top-4 angles")
        row["delta_auprc_vs_vqc"], row["delta_ci_low"], row["delta_ci_high"] = _delta(
            r, res.vqc, confidence
        )
        rows.append(row)
    frame = pd.DataFrame(rows)
    frame["threshold_metrics"] = THRESHOLD_NOTE
    return frame


def unclipped_context(res: Phase3AResults, confidence: float) -> pd.DataFrame:
    clipped = {r.model_id: r for r in res.classical}
    rows = []
    for r in res.context_unclipped:
        delta, lo, hi = _delta(r, clipped[r.model_id], confidence)
        rows.append(
            {
                "model": r.model_id,
                "inputs": "top-4 robust-scaled, unclipped",
                "n_train": r.n_train,
                "auprc": r.metrics["auprc"],
                "auprc_ci_low": r.intervals["auprc"][0],
                "auprc_ci_high": r.intervals["auprc"][1],
                "auroc": r.metrics["auroc"],
                "delta_auprc_vs_clipped_angles": delta,
                "delta_ci_low": lo,
                "delta_ci_high": hi,
            }
        )
    return pd.DataFrame(rows)


def full_data_context(root: Path) -> pd.DataFrame:
    m = pd.read_csv(root / "results" / "tables" / "phase2_classical_metrics.csv")
    m = m[(m["regime"] == "a-full") & m["representation"].isin(["full", "top4-fclassif"])]
    out = m[
        ["model", "representation", "n_train", "auprc", "auprc_ci_low", "auprc_ci_high", "auroc"]
    ]
    return out.assign(source="phase2_classical_metrics.csv (full vqc_train, class-weighted)")


def trace_table(res: Phase3AResults) -> pd.DataFrame:
    return pd.DataFrame(
        {"evaluation": np.arange(1, len(res.training.trace) + 1), "bce_loss": res.training.trace}
    )


def score_histogram(res: Phase3AResults, bins: int = 50) -> pd.DataFrame:
    edges = np.linspace(0.0, 1.0, bins + 1)
    s, y = res.vqc.scores, res.y_val
    legit, _ = np.histogram(s[y == 0], bins=edges)
    fraud, _ = np.histogram(s[y == 1], bins=edges)
    return pd.DataFrame(
        {
            "bin_lower": edges[:-1],
            "bin_upper": edges[1:],
            "legit_count": legit,
            "fraud_count": fraud,
        }
    )


def pr_table(res: Phase3AResults, points: int) -> pd.DataFrame:
    grid = np.linspace(0.0, 1.0, points)
    rows = []
    for r in [res.vqc, *res.classical]:
        for recall, p in zip(
            grid, M.interpolated_precision(res.y_val, r.scores, grid), strict=True
        ):
            rows.append({"model": r.model_id, "recall": recall, "interpolated_precision": p})
    return pd.DataFrame(rows)


def calibration_table(res: Phase3AResults, n_bins: int) -> pd.DataFrame:
    rows = []
    for r in [res.vqc, *res.classical]:
        for strategy in ("uniform", "quantile"):
            for b in M.calibration_bins(res.y_val, r.scores, n_bins, strategy):
                rows.append({"model": r.model_id, "strategy": strategy, **b})
    return pd.DataFrame(rows)


def sanity(run: Phase3ARun) -> dict:
    res, s = run.results, run.resolved.vqc.sanity
    prevalence = float(res.y_val.mean())
    t = res.training
    reduction = (t.initial_loss - t.final_loss) / t.initial_loss
    distinct = int(np.unique(np.round(res.vqc.scores, 12)).size)
    tol = run.resolved.vqc.reproducibility_param_tolerance
    checks = {
        "trains_reproducibly": res.retrain_max_abs_param_diff <= tol,
        "objective_reduced": reduction >= s.min_relative_loss_reduction,
        "non_constant_predictions": distinct >= s.min_distinct_scores,
        "auprc_ci_low_above_threshold": res.vqc.intervals["auprc"][0]
        > s.min_auprc_ci_low_over_prevalence * prevalence,
        "auroc_ci_low_above_threshold": res.vqc.intervals["auroc"][0] > s.min_auroc_ci_low,
        "frozen_replay_deterministic": res.replay_max_abs_score_diff == 0.0,
        "aer_noiseless_agreement": run.aer_crosscheck["agrees_within_1e-10"],
    }
    return {
        "pre_registered": s.model_dump(mode="json"),
        "observed": {
            "relative_loss_reduction": round(reduction, DIGITS),
            "distinct_scores": distinct,
            "vqc_val_prevalence": round(prevalence, 8),
            "auprc_ci_low": round(res.vqc.intervals["auprc"][0], DIGITS),
            "auroc_ci_low": round(res.vqc.intervals["auroc"][0], DIGITS),
        },
        "checks": checks,
        "passed": all(checks.values()),
    }


def metadata(run: Phase3ARun) -> dict:
    res, cfg = run.results, run.resolved.vqc
    t = res.training
    sub = res.subset
    r6 = lambda v: round(float(v), DIGITS)  # noqa: E731
    return {
        **run.context,
        "feature_selection": {
            "method": "f_classif on all of vqc_train, top 4 (O02, provisional for 3A)",
            "features": list(res.features),
            "matches_expected": list(res.features) == list(cfg.expected_features),
            "f_classif_scores_selected": {
                f: round(res.selection_scores[f], 3) for f in res.features
            },
        },
        "encoding": {
            **res.encoder.model_dump(mode="json"),
            "artifact_sha256": res.encoder.artifact_sha256(),
            "formula": "theta = (pi / clip) * clip((x - median) / IQR, -clip, clip)",
            "clip_fractions": {
                k: {f: r6(v) for f, v in d.items()} for k, d in res.clip_fractions.items()
            },
        },
        "training_subset": {
            "subset_id": sub.spec.subset_id,
            "undersample_master_seed": sub.undersample_master_seed,
            "derived_seed": sub.derived_seed,
            "rows": len(sub.row_ids),
            "n_fraud": sub.n_fraud,
            "n_legit": sub.n_legit,
            "row_ids_sha256": sub.row_ids_sha256,
        },
        "circuit": {
            "feature_map": cfg.feature_map.model_dump(mode="json"),
            "ansatz": cfg.ansatz.model_dump(mode="json"),
            "transpiled": res.circuit_stats,
        },
        "readout": {**cfg.readout.model_dump(mode="json"), "formula": "p_fraud = (1 - z) / 2"},
        "training": {
            **cfg.training.model_dump(mode="json"),
            "optimizer": cfg.optimizer.model_dump(mode="json"),
            "init_seed": res.frozen.init_seed,
            "theta0": [r6(v) for v in t.theta0],
            "objective_evaluations": t.nfev,
            "optimizer_status": t.status,
            "optimizer_message": t.message,
            "initial_loss": r6(t.initial_loss),
            "final_loss": r6(t.final_loss),
        },
        "frozen_vqc": {
            "path": f"artifacts/frozen_vqcs/{cfg.vqc_id}.json",
            "theta_sha256": res.frozen.theta_sha256,
            "artifact_sha256": res.frozen.artifact_sha256(),
        },
        "reproducibility": {
            "retrain_max_abs_param_diff": res.retrain_max_abs_param_diff,
            "param_tolerance": cfg.reproducibility_param_tolerance,
            "replay_max_abs_score_diff": res.replay_max_abs_score_diff,
            "aer_density_matrix_crosscheck": run.aer_crosscheck,
        },
        "evaluation": {
            "partition": EVAL,
            "rows": len(res.y_val),
            "fraud": int(res.y_val.sum()),
            "prevalence": round(float(res.y_val.mean()), 8),
            "calibration_note": "VQC trained at 20% fraud prevalence, evaluated at ~0.17%: raw "
            "probabilities are not real-world fraud probabilities",
        },
        "sanity": sanity(run),
        "training_diagnostics": {
            k: (
                round(v, DIGITS)
                if isinstance(v, float)
                else {kk: round(vv, DIGITS) for kk, vv in v.items()}
                if isinstance(v, dict)
                else v
            )
            for k, v in res.training_diagnostics.items()
        },
        "diagnostic_flags": {
            "training_bce_above_constant_predictor": res.training_diagnostics["train_bce"]
            > res.training_diagnostics["constant_prevalence_bce"],
            "feature_map_aliases_on_encoding_range": res.training_diagnostics[
                "feature_map_alias_fidelity"
            ]["x0=-0.4 vs x0=-0.4+pi, partners=+pi"]
            > 1 - 1e-9,
            "majority_of_training_frauds_fully_clipped": res.training_diagnostics[
                "train_frauds_all_features_clipped"
            ]
            > res.subset.n_fraud / 2,
        },
    }


def render_committed(run: Phase3ARun, root: Path) -> dict[str, str]:
    """Exact text of every committed Phase 3A output, keyed by repository-relative path."""
    res, cfg = run.results, run.resolved.baseline
    conf = cfg.bootstrap.confidence
    t = "results/tables/"
    out = {
        t + "phase3a_comparison.csv": _csv(comparison_table(res, conf)),
        t + "phase3a_context_unclipped.csv": _csv(unclipped_context(res, conf)),
        t + "phase3a_context_full_data.csv": _csv(full_data_context(root)),
        t + "phase3a_optimization_trace.csv": _csv(trace_table(res)),
        t + "phase3a_score_histogram.csv": _csv(score_histogram(res)),
        t + "phase3a_pr_curves.csv": _csv(pr_table(res, cfg.pr_recall_grid_points)),
        t + "phase3a_calibration_bins.csv": _csv(calibration_table(res, cfg.calibration.n_bins)),
    }
    out[t + "phase3a_metadata.json"] = json.dumps(metadata(run), indent=2, sort_keys=True) + "\n"
    frozen = res.frozen.model_dump(mode="json") | {"artifact_sha256": res.frozen.artifact_sha256()}
    out[f"artifacts/frozen_vqcs/{run.resolved.vqc.vqc_id}.json"] = (
        json.dumps(frozen, indent=2, sort_keys=True) + "\n"
    )
    return out
