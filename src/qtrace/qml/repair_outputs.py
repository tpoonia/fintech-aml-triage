"""Phase 3A-R configured runs.

Stage 1 ``run_selection``: vqc_train ONLY (access phase "phase3ar_select"). Folds,
encoding diagnostics, CV, deterministic selection, final training on the fixed 3A
subset, freezing.

Stage 2 ``run_evaluation``: the one-time vqc_val evaluation of the frozen selection
(access phase "phase3ar_eval"), compared with P3A-original and equal-input
classical models. It never revisits selection.
"""

from __future__ import annotations

import io
import json
import time
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path

import numpy as np
import pandas as pd

from qtrace.classical.models import build_model
from qtrace.classical.runner import (
    ConfigResult,
    bootstrap_metrics,
    crossfit_seed,
    point_metrics,
    vqc_val_bootstrap_seed,
)
from qtrace.config import load_component, load_experiment
from qtrace.data.access import load_partition_table, load_partitions
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.folds import assign_group_folds, fold_summary
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import GROUP_KEY, PARTITION
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.subset import SubsetSpec, build_vqc_training_subset
from qtrace.data.verify import verify_phase1
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import percentile_interval
from qtrace.qml import circuit as C
from qtrace.qml import repair as R
from qtrace.qml.encoding import AngleEncoder, fit_angle_encoder
from qtrace.qml.model import FrozenVQC, bce, predict, theta_sha256, train
from qtrace.qml.simulate import feature_states
from qtrace.utils.hashing import stable_hash
from qtrace.utils.seeds import derive_seed, make_rng

EXPERIMENT_ID = "phase3ar_vqc"
STUDY_ID = "p3ar_v1"
P3A_ARTIFACT = "artifacts/frozen_vqcs/vqc3a_top4_ra1.json"
DIGITS = 6
T = "results/tables/"


def _software() -> dict[str, str]:
    names = ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn")
    return {n: importlib_metadata.version(n) for n in names}


def _load_json_model(path: Path, model):
    data = json.loads(path.read_text())
    stored = data.pop("artifact_sha256")
    obj = model.model_validate(data)
    if obj.artifact_sha256() != stored:
        raise RuntimeError(f"{path}: artifact hash mismatch")
    return obj


def _csv(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.round(DIGITS).to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def _json(obj) -> str:
    return json.dumps(obj, indent=2, sort_keys=True, default=str) + "\n"


# ========================================================================= stage 1


@dataclass
class SelectionRun:
    resolved: object
    study: object
    folds_table: list[dict]
    diagnostics: dict[str, dict]
    eligibility: dict[str, dict[str, bool]]
    records: list
    summary: pd.DataFrame
    chosen: str
    reason: dict
    final_results: list
    kept: int
    retrain_max_abs_param_diff: float
    frozen: R.FrozenRepairVQC
    circuit_stats: dict
    context: dict
    timings: dict = field(default_factory=dict)


def run_selection(root: Path) -> SelectionRun:
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    resolved = load_experiment(EXPERIMENT_ID)
    study = load_component("repair", STUDY_ID)
    spec, dataset, base = resolved.spec, resolved.dataset, resolved.vqc
    target, dataset_id = dataset.target_column, dataset.dataset_id
    processed = root / "data" / "processed" / dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    train_df = load_partitions(processed, "phase3ar_select", ["vqc_train"])  # vqc_train ONLY
    train_df = train_df.sort_values(ROW_ID).reset_index(drop=True)
    verified = verify_phase1(root, dataset_id, train_df, fitted, ("vqc_train",))
    if tuple(study.features) != tuple(base.expected_features):
        raise RuntimeError("Phase 3A-R keeps the 3A features")
    train_hash = row_ids_sha256(train_df[ROW_ID])

    # P3A-original encoder statistics, re-derived and checked against the frozen 3A artifact.
    p3a = _load_json_model(root / P3A_ARTIFACT, FrozenVQC)
    base_enc = fit_angle_encoder(base.encoding, train_df, tuple(study.features), train_hash)
    if (base_enc.median, base_enc.iqr) != (tuple(p3a.encoder["median"]), tuple(p3a.encoder["iqr"])):
        raise RuntimeError("encoder statistics differ from the frozen P3A-original artifact")
    encoders = {e.enc_id: R.make_encoder(e, base_enc) for e in study.encodings}

    # Authoritative Phase 1 group keys (raw V1-V28 + Amount), vqc_train rows only.
    keys = load_partition_table(processed, "phase3ar_select", ["vqc_train"])
    keyed = train_df[[ROW_ID, target]].merge(keys[[ROW_ID, GROUP_KEY]], on=ROW_ID, validate="1:1")
    folds = assign_group_folds(
        keyed, dataset, study.cv.n_folds, spec.seeds.split, study.cv.seed_key
    )
    if folds[ROW_ID].tolist() != train_df[ROW_ID].tolist():
        raise RuntimeError("fold table misaligned with vqc_train")
    folds_table = fold_summary(folds, train_df.set_index(ROW_ID)[target])
    timings["data_folds_s"] = time.perf_counter() - t0

    t = time.perf_counter()
    fmap = C.feature_map(base)
    states = {k: feature_states(fmap, enc.transform(train_df)) for k, enc in encoders.items()}
    timings["feature_states_all_encodings_s"] = time.perf_counter() - t

    t = time.perf_counter()
    y = train_df[target].to_numpy()
    rng = make_rng(spec.seeds.bootstrap, "bootstrap", dataset_id, "p3ar-probe")
    legit = rng.choice(np.flatnonzero(y == 0), study.collision_probe_legit_sample, replace=False)
    probe = np.sort(np.concatenate([np.flatnonzero(y == 1), legit]))
    diagnostics = {
        k: R.encoding_diagnostics(enc, train_df, target, fmap, probe, study)
        for k, enc in encoders.items()
    }
    control = diagnostics[study.control_encoding]
    elig = {
        k: R.eligibility(d, control, study.selection.eligibility) for k, d in diagnostics.items()
    }
    eligible_enc = {k: all(v.values()) and k != study.control_encoding for k, v in elig.items()}
    timings["diagnostics_s"] = time.perf_counter() - t

    t = time.perf_counter()
    records, _ = R.run_cv(
        train_df, folds, study, base, spec.seeds, states, target=target, dataset_id=dataset_id
    )
    timings["cv_s"] = time.perf_counter() - t
    summary = R.summarize(records, study, eligible_enc, base.n_qubits)
    chosen, reason = R.select(summary, study)

    # Final training on the fixed P3A subset with the same restart seeds.
    t = time.perf_counter()
    subset = build_vqc_training_subset(
        train_df,
        train_df[[ROW_ID, PARTITION]],
        SubsetSpec(subset_id=base.subset.subset_id, legit_per_fraud=base.subset.legit_per_fraud),
        target=target,
        dataset_id=dataset_id,
        undersample_seed=spec.seeds.undersample,
    )
    if subset.row_ids_sha256 != p3a.subset_rows_sha256:
        raise RuntimeError("final-training subset differs from the P3A-original subset")
    pos = np.flatnonzero(train_df[ROW_ID].isin(subset.row_ids).to_numpy())
    cand = R.candidate_by_id(study, chosen)
    ccfg = R.candidate_vqc(base, cand.ansatz_reps)
    _, ans, _ = C.build(ccfg)
    diag = R.observable_diagonal(cand.observable, base.n_qubits)
    seeds_r = R.restart_seeds(study, spec.seeds, dataset_id)
    eps = base.training.bce_epsilon
    st = states[cand.encoding][pos]
    kept, finals = R.final_train(ans, st, y[pos], diag, study, seeds_r, eps)
    again = train(ans, st, y[pos], study.optimizer, eps, seeds_r[kept], diag)
    retrain_diff = float(np.max(np.abs(again.theta - finals[kept].theta)))
    timings["final_training_s"] = time.perf_counter() - t

    transpile_seed = derive_seed(
        spec.seeds.model, "model", dataset_id, "phase3ar", chosen, "transpile"
    ) % (2**31)
    _, stats = C.transpiled_statistics(ccfg, transpile_seed)
    theta = finals[kept].theta
    frozen = R.FrozenRepairVQC(
        vqc_id=f"vqc3ar_{chosen}",
        study_id=study.study_id,
        study_config_sha256=stable_hash(study),
        candidate=cand.model_dump(mode="json"),
        base_vqc_config_sha256=stable_hash(base),
        theta=tuple(float(v) for v in theta),
        theta_sha256=theta_sha256(theta),
        encoder=encoders[cand.encoding].model_dump(mode="json"),
        encoder_sha256=encoders[cand.encoding].artifact_sha256(),
        dataset_sha256=dataset.expected_sha256,
        split_vqc_train_sha256=train_hash,
        preprocessing_sha256=fitted.artifact_sha256(),
        subset_rows_sha256=subset.row_ids_sha256,
        restart_seeds=tuple(seeds_r),
        kept_restart=kept,
        readout=f"{cand.observable}; p_fraud = (1 - z) / 2",
        software=_software(),
    )
    context = {
        "experiment_id": spec.experiment_id,
        "study_id": study.study_id,
        "study_config_sha256": stable_hash(study),
        "experiment_config_sha256": resolved.config_hash(),
        "dataset_sha256": dataset.expected_sha256,
        "phase1_verification": verified,
        "partitions_read_during_selection": ["vqc_train"],
    }
    return SelectionRun(
        resolved,
        study,
        folds_table,
        diagnostics,
        elig,
        records,
        summary,
        chosen,
        reason,
        finals,
        kept,
        retrain_diff,
        frozen,
        stats,
        context,
        timings,
    )


def render_selection(run: SelectionRun) -> dict[str, str]:
    diag = pd.DataFrame(
        [
            {**d, **{f"eligible_{k}": v for k, v in run.eligibility[e].items()}}
            for e, d in run.diagnostics.items()
        ]
    )
    runs = pd.DataFrame(
        [
            {
                "cand_id": r.cand_id,
                "fold": r.fold,
                "restart": r.restart,
                "init_seed": r.init_seed,
                "evaluations": r.result.nfev,
                "status": r.result.status,
                "initial_train_bce": r.result.initial_loss,
                "final_train_bce": r.result.final_loss,
                "train_auprc": r.train_auprc,
                **{f"val_{k}": v for k, v in r.val.items()},
            }
            for r in run.records
        ]
    )
    final = pd.DataFrame(
        [
            {
                "restart": i,
                "init_seed": run.frozen.restart_seeds[i],
                "evaluations": f.nfev,
                "status": f.status,
                "message": f.message,
                "initial_train_bce": f.initial_loss,
                "final_train_bce": f.final_loss,
                "kept": i == run.kept,
            }
            for i, f in enumerate(run.final_results)
        ]
    )
    trace = run.final_results[run.kept].trace
    selection = {
        **run.context,
        "folds": run.folds_table,
        "restart_seeds": list(run.frozen.restart_seeds),
        "selection": run.reason,
        "selected_candidate": run.frozen.candidate,
        "final_training": {
            "subset_rows_sha256": run.frozen.subset_rows_sha256,
            "kept_restart": run.kept,
            "retrain_max_abs_param_diff": run.retrain_max_abs_param_diff,
        },
        "circuit": run.circuit_stats,
        "frozen_vqc": {
            "path": f"artifacts/frozen_vqcs/{run.frozen.vqc_id}.json",
            "theta_sha256": run.frozen.theta_sha256,
            "artifact_sha256": run.frozen.artifact_sha256(),
        },
    }
    frozen = run.frozen.model_dump(mode="json") | {"artifact_sha256": run.frozen.artifact_sha256()}
    return {
        T + "p3ar_encoding_diagnostics.csv": _csv(diag),
        T + "p3ar_folds.csv": _csv(pd.DataFrame(run.folds_table)),
        T + "p3ar_cv_runs.csv": _csv(runs),
        T + "p3ar_cv_summary.csv": _csv(run.summary),
        T + "p3ar_final_training.csv": _csv(final),
        T + "p3ar_final_trace.csv": _csv(
            pd.DataFrame({"evaluation": np.arange(1, len(trace) + 1), "bce_loss": trace})
        ),
        T + "p3ar_selection.json": _json(selection),
        f"artifacts/frozen_vqcs/{run.frozen.vqc_id}.json": _json(frozen),
    }


# ========================================================================= stage 2


@dataclass
class EvaluationRun:
    results: dict[str, ConfigResult]
    y_val: np.ndarray
    sanity: dict
    context: dict
    timings: dict = field(default_factory=dict)


def _score(y, scores, model_id, rep, n_train, n_fraud, rows_sha, seed, cfg, boot, cross):
    metrics = point_metrics(y, scores, cfg, cross)
    intervals, samples = bootstrap_metrics(
        y, scores, metrics["threshold"], cfg.bootstrap.n_resamples, boot, cfg.bootstrap.confidence
    )
    return ConfigResult(
        model_id,
        rep,
        "p3a-lpf4",
        0,
        n_train,
        n_fraud,
        rows_sha,
        seed,
        scores,
        metrics,
        intervals,
        samples,
    )


def run_evaluation(root: Path) -> EvaluationRun:
    """One-time vqc_val evaluation of the FROZEN selection (never revisits selection)."""
    timings: dict[str, float] = {}
    resolved = load_experiment(EXPERIMENT_ID)
    spec, dataset, base, cfg = resolved.spec, resolved.dataset, resolved.vqc, resolved.baseline
    selection = json.loads((root / T / "p3ar_selection.json").read_text())
    frozen = _load_json_model(root / selection["frozen_vqc"]["path"], R.FrozenRepairVQC)
    p3a = _load_json_model(root / P3A_ARTIFACT, FrozenVQC)
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, "phase3ar_eval", ["vqc_train", "vqc_val"])
    verified = verify_phase1(root, dataset.dataset_id, frame, fitted, ("vqc_train", "vqc_val"))
    target = dataset.target_column
    train_df = frame[frame[PARTITION] == "vqc_train"].sort_values(ROW_ID).reset_index(drop=True)
    val = frame[frame[PARTITION] == "vqc_val"].sort_values(ROW_ID).reset_index(drop=True)
    y_val = val[target].to_numpy(dtype=np.int64)

    cand = frozen.candidate
    enc = R.RepairEncoder.model_validate(frozen.encoder)
    fmap = C.feature_map(base)
    _, ans, _ = C.build(R.candidate_vqc(base, cand["ansatz_reps"]))
    diag = R.observable_diagonal(cand["observable"], base.n_qubits)
    t = time.perf_counter()
    p_rep = predict(ans, feature_states(fmap, enc.transform(val)), np.array(frozen.theta), diag)
    timings["p3ar_val_inference_s"] = time.perf_counter() - t

    enc3a = AngleEncoder.model_validate(p3a.encoder)
    _, ans3a, _ = C.build(base)
    p_orig = predict(ans3a, feature_states(fmap, enc3a.transform(val)), np.array(p3a.theta))

    sub = train_df[
        train_df[ROW_ID].isin(
            build_vqc_training_subset(
                train_df,
                train_df[[ROW_ID, PARTITION]],
                SubsetSpec(
                    subset_id=base.subset.subset_id, legit_per_fraud=base.subset.legit_per_fraud
                ),
                target=target,
                dataset_id=dataset.dataset_id,
                undersample_seed=spec.seeds.undersample,
            ).row_ids
        )
    ].sort_values(ROW_ID)
    if row_ids_sha256(sub[ROW_ID]) != frozen.subset_rows_sha256:
        raise RuntimeError("subset mismatch")
    y_sub = sub[target].to_numpy()
    boot = vqc_val_bootstrap_seed(spec.seeds, dataset.dataset_id)
    cross = crossfit_seed(spec.seeds, dataset.dataset_id)
    n_sub, n_fraud, sha = len(sub), int(y_sub.sum()), frozen.subset_rows_sha256
    results = {
        "p3a_original": _score(
            y_val,
            p_orig,
            "p3a_original",
            "e0 angles",
            n_sub,
            n_fraud,
            sha,
            p3a.init_seed,
            cfg,
            boot,
            cross,
        ),
        "p3a_r": _score(
            y_val,
            p_rep,
            "p3a_r",
            f"{cand['encoding']} angles",
            n_sub,
            n_fraud,
            sha,
            frozen.restart_seeds[frozen.kept_restart],
            cfg,
            boot,
            cross,
        ),
    }
    x_sub, x_val = enc.transform(sub), enc.transform(val)
    for model_cfg in cfg.models:
        seed = derive_seed(
            spec.seeds.model,
            "model",
            dataset.dataset_id,
            "phase3ar",
            model_cfg.model_id,
            cand["encoding"],
        ) % (2**32)
        scores = build_model(model_cfg, None, seed).fit(x_sub, y_sub).predict_proba(x_val)[:, 1]
        results[model_cfg.model_id] = _score(
            y_val,
            scores,
            model_cfg.model_id,
            f"{cand['encoding']} angles",
            n_sub,
            n_fraud,
            sha,
            seed,
            cfg,
            boot,
            cross,
        )
    s = base.sanity
    final = pd.read_csv(root / T / "p3ar_final_training.csv")
    kept = final[final["kept"]].iloc[0]
    reduction = (kept["initial_train_bce"] - kept["final_train_bce"]) / kept["initial_train_bce"]
    r = results["p3a_r"]
    prevalence = float(y_val.mean())
    checks = {
        "trains_reproducibly": selection["final_training"]["retrain_max_abs_param_diff"]
        <= base.reproducibility_param_tolerance,
        "objective_reduced": reduction >= s.min_relative_loss_reduction,
        "non_constant_predictions": int(np.unique(np.round(p_rep, 12)).size)
        >= s.min_distinct_scores,
        "auprc_ci_low_above_threshold": r.intervals["auprc"][0]
        > s.min_auprc_ci_low_over_prevalence * prevalence,
        "auroc_ci_low_above_threshold": r.intervals["auroc"][0] > s.min_auroc_ci_low,
    }
    checks = {k: bool(v) for k, v in checks.items()}
    sanity = {
        "pre_registered": s.model_dump(mode="json"),
        "observed": {
            "relative_loss_reduction": round(float(reduction), DIGITS),
            "distinct_scores": int(np.unique(np.round(p_rep, 12)).size),
            "auprc_ci_low": round(r.intervals["auprc"][0], DIGITS),
            "auroc_ci_low": round(r.intervals["auroc"][0], DIGITS),
            "vqc_val_prevalence": round(prevalence, 8),
        },
        "checks": checks,
        "passed": all(checks.values()),
    }
    context = {
        "experiment_id": spec.experiment_id,
        "phase1_verification": verified,
        "selected_vqc": frozen.vqc_id,
        "frozen_artifact_sha256": frozen.artifact_sha256(),
        "p3a_original_artifact_sha256": p3a.artifact_sha256(),
        "evaluation_note": "one-time vqc_val evaluation of the frozen Phase 3A-R selection",
        "bce_val": {
            k: round(bce(y_val, v.scores, base.training.bce_epsilon), DIGITS)
            for k, v in results.items()
        },
    }
    return EvaluationRun(results, y_val, sanity, context, timings)


CI = ("auprc", "auroc", "precision", "recall", "f1", "f2", "brier")


def render_evaluation(run: EvaluationRun, cfg) -> dict[str, str]:
    res, y = run.results, run.y_val
    conf = cfg.bootstrap.confidence
    rows = []
    for key, r in res.items():
        row = {
            "model": key,
            "inputs": r.rep_id,
            "input_dim": 4,
            "n_train": r.n_train,
            "n_train_fraud": r.n_train_fraud,
        }
        for name, value in r.metrics.items():
            row[name] = value
            if name in CI:
                row[f"{name}_ci_low"], row[f"{name}_ci_high"] = r.intervals[name]
        ref = res["p3a_original"] if key == "p3a_r" else res["p3a_r"]
        if key != "p3a_original":
            delta = r.auprc_samples - ref.auprc_samples
            row["delta_auprc_reference"] = ref.model_id
            row["delta_auprc"] = r.metrics["auprc"] - ref.metrics["auprc"]
            row["delta_ci_low"], row["delta_ci_high"] = percentile_interval(delta, conf)
        row["threshold_metrics"] = "exploratory: threshold selected and reported on vqc_val"
        rows.append(row)
    grid = np.linspace(0.0, 1.0, cfg.pr_recall_grid_points)
    pr = [
        {"model": k, "recall": rc, "interpolated_precision": p}
        for k, r in res.items()
        for rc, p in zip(grid, M.interpolated_precision(y, r.scores, grid), strict=True)
    ]
    edges = np.linspace(0, 1, 51)
    hist = []
    for k in ("p3a_original", "p3a_r"):
        s = res[k].scores
        legit, _ = np.histogram(s[y == 0], bins=edges)
        fraud, _ = np.histogram(s[y == 1], bins=edges)
        hist += [
            {
                "model": k,
                "bin_lower": edges[i],
                "bin_upper": edges[i + 1],
                "legit_count": int(legit[i]),
                "fraud_count": int(fraud[i]),
            }
            for i in range(len(edges) - 1)
        ]
    cal = [
        {"model": k, "strategy": st, **b}
        for k, r in res.items()
        for st in ("uniform", "quantile")
        for b in M.calibration_bins(y, r.scores, cfg.calibration.n_bins, st)
    ]
    evaluation = {
        **run.context,
        "sanity": run.sanity,
        "evaluation": {"partition": "vqc_val", "rows": len(y), "fraud": int(y.sum())},
    }
    return {
        T + "p3ar_validation_comparison.csv": _csv(pd.DataFrame(rows)),
        T + "p3ar_pr_curves.csv": _csv(pd.DataFrame(pr)),
        T + "p3ar_score_histogram.csv": _csv(pd.DataFrame(hist)),
        T + "p3ar_calibration_bins.csv": _csv(pd.DataFrame(cal)),
        T + "p3ar_evaluation.json": _json(evaluation),
    }
