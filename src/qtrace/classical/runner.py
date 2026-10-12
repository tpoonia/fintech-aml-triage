"""Phase 2 runner: fit on vqc_train, select thresholds and report on vqc_val.

Data enter only through ``qtrace.data.access.load_partitions`` (phase "phase2"),
so controller partitions are never read. Everything is deterministic given the
config and the seed masters:

* model ``random_state`` = derive_seed(model, "model", dataset, "phase2", model, rep, regime, draw)
* subsets: ``build_vqc_training_subset`` with the ``undersample`` stream
* bootstrap / cross-fit folds: the ``bootstrap`` stream (shared by all configs)
"""

from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from qtrace.classical.models import build_model
from qtrace.config.schemas import ClassicalBaselineConfig, RegimeConfig, SeedConfig
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import PARTITION
from qtrace.data.representation import FittedRepresentation, fit_representation
from qtrace.data.subset import SubsetRecord, SubsetSpec, build_vqc_training_subset
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import bootstrap_distribution, percentile_interval
from qtrace.utils.seeds import derive_seed

FIT, EVAL = "vqc_train", "vqc_val"
CI_METRICS = ("auprc", "auroc", "precision", "recall", "f1", "f2", "brier")


@dataclass
class TrainingSet:
    regime_id: str
    draw: int
    frame: pd.DataFrame
    class_weight: str | None
    rows_sha256: str
    subset: SubsetRecord | None = None


@dataclass
class ConfigResult:
    model_id: str
    rep_id: str
    regime_id: str
    draw: int
    n_train: int
    n_train_fraud: int
    train_rows_sha256: str
    model_seed: int
    scores: np.ndarray
    metrics: dict[str, float]
    intervals: dict[str, tuple[float, float]] = field(default_factory=dict)
    auprc_samples: np.ndarray | None = None


@dataclass
class Phase2Results:
    y_val: np.ndarray
    val_row_ids: np.ndarray
    representations: dict[str, FittedRepresentation]
    training_sets: list[TrainingSet]
    results: list[ConfigResult]
    bootstrap_seed: int
    crossfit_seed: int


def _training_sets(
    train: pd.DataFrame, regime: RegimeConfig, target: str, dataset_id: str, seeds: SeedConfig
) -> list[TrainingSet]:
    if regime.kind == "full_partition":
        return [
            TrainingSet(
                regime.regime_id, 0, train, regime.class_weight, row_ids_sha256(train[ROW_ID])
            )
        ]
    out = []
    assignment = train[[ROW_ID, PARTITION]]
    for draw in range(regime.draws):
        spec = SubsetSpec(
            subset_id=f"p2-{regime.regime_id}-d{draw}", legit_per_fraud=regime.legit_per_fraud
        )
        record = build_vqc_training_subset(
            train,
            assignment,
            spec,
            target=target,
            dataset_id=dataset_id,
            undersample_seed=seeds.undersample,
        )
        frame = train[train[ROW_ID].isin(record.row_ids)].sort_values(ROW_ID)
        out.append(
            TrainingSet(
                regime.regime_id, draw, frame, regime.class_weight, record.row_ids_sha256, record
            )
        )
    return out


def _crossfit_f1(y: np.ndarray, s: np.ndarray, folds: int, seed: int) -> float:
    """Threshold chosen on the other folds, applied to each held-out fold; counts pooled."""
    rng = np.random.default_rng(seed)
    fold_of = np.empty(len(y), dtype=int)
    for label in (0, 1):
        idx = np.flatnonzero(y == label)
        fold_of[rng.permutation(idx)] = np.arange(len(idx)) % folds
    tp = fp = fn = 0.0
    for f in range(folds):
        held, rest = fold_of == f, fold_of != f
        tau = M.max_f1_threshold(y[rest], s[rest])
        a, b, c, _ = M.confusion_at(y[held], s[held], tau)
        tp, fp, fn = tp + a, fp + b, fn + c
    return M.fbeta_from_counts(tp, fp, fn, 1.0)


def point_metrics(
    y: np.ndarray, s: np.ndarray, cfg: ClassicalBaselineConfig, crossfit_seed: int
) -> dict[str, float]:
    tau = M.max_f1_threshold(y, s)
    out = {
        "auprc": M.average_precision(y, s),
        "auroc": M.roc_auc(y, s),
        "threshold": tau,
        **M.threshold_metrics(y, s, tau),
        "f1_crossfit": _crossfit_f1(y, s, cfg.threshold.crossfit_folds, crossfit_seed),
        "brier": M.brier(y, s),
        "ece_uniform": M.expected_calibration_error(y, s, cfg.calibration.n_bins, "uniform"),
        "ece_quantile": M.expected_calibration_error(y, s, cfg.calibration.n_bins, "quantile"),
        "r_precision": M.precision_at_k(y, s, int(y.sum())),
    }
    for k in cfg.top_k:
        out[f"precision_at_{k}"] = M.precision_at_k(y, s, k)
    for target in cfg.precision_targets:
        out[f"recall_at_precision_{int(round(target * 100))}"] = M.recall_at_precision(y, s, target)
    return out


def vqc_val_bootstrap_seed(seeds: SeedConfig, dataset_id: str) -> int:
    """Seed of the shared vqc_val bootstrap: every model in every phase sees the same resamples."""
    return derive_seed(seeds.bootstrap, "bootstrap", dataset_id, "phase2", EVAL)


def crossfit_seed(seeds: SeedConfig, dataset_id: str) -> int:
    return derive_seed(seeds.bootstrap, "bootstrap", dataset_id, "phase2", "crossfit")


def bootstrap_metrics(y, s, tau, n_resamples, seed, confidence):
    fns = {
        "auprc": lambda w: M.average_precision(y, s, w),
        "auroc": lambda w: M.roc_auc(y, s, w),
        "brier": lambda w: M.brier(y, s, w),
    }
    for name in ("precision", "recall", "f1", "f2"):
        fns[name] = lambda w, name=name: M.threshold_metrics(y, s, tau, w)[name]
    samples = bootstrap_distribution(y, fns, n_resamples, seed)
    return {k: percentile_interval(v, confidence) for k, v in samples.items()}, samples["auprc"]


def run_phase2(
    train: pd.DataFrame,
    val: pd.DataFrame,
    cfg: ClassicalBaselineConfig,
    seeds: SeedConfig,
    *,
    dataset_id: str,
    target: str,
    feature_columns: tuple[str, ...],
    n_jobs: int = -1,
) -> Phase2Results:
    if set(train[PARTITION]) != {FIT} or set(val[PARTITION]) != {EVAL}:
        raise ValueError("Phase 2 fits on vqc_train and evaluates on vqc_val only")
    train = train.sort_values(ROW_ID).reset_index(drop=True)
    val = val.sort_values(ROW_ID).reset_index(drop=True)
    y_val = val[target].to_numpy(dtype=np.int64)
    boot_seed = vqc_val_bootstrap_seed(seeds, dataset_id)
    cross_seed = crossfit_seed(seeds, dataset_id)

    train_hash = row_ids_sha256(train[ROW_ID])
    reps = {
        r.rep_id: fit_representation(r, train, target, feature_columns, train_hash)
        for r in cfg.representations
    }
    val_x = {rep_id: rep.transform(val) for rep_id, rep in reps.items()}

    sets = [
        ts
        for regime in cfg.regimes
        for ts in _training_sets(train, regime, target, dataset_id, seeds)
    ]
    results: list[ConfigResult] = []
    for ts in sets:
        y_train = ts.frame[target].to_numpy()
        for rep_id, rep in reps.items():
            x_train = rep.transform(ts.frame)
            for model_cfg in cfg.models:
                seed = derive_seed(
                    seeds.model,
                    "model",
                    dataset_id,
                    "phase2",
                    model_cfg.model_id,
                    rep_id,
                    ts.regime_id,
                    ts.draw,
                ) % (2**32)
                model = build_model(model_cfg, ts.class_weight, seed).fit(x_train, y_train)
                scores = model.predict_proba(val_x[rep_id])[:, 1]
                results.append(
                    ConfigResult(
                        model_id=model_cfg.model_id,
                        rep_id=rep_id,
                        regime_id=ts.regime_id,
                        draw=ts.draw,
                        n_train=len(ts.frame),
                        n_train_fraud=int(y_train.sum()),
                        train_rows_sha256=ts.rows_sha256,
                        model_seed=seed,
                        scores=scores,
                        metrics=point_metrics(y_val, scores, cfg, cross_seed),
                    )
                )

    # Bootstrap intervals for every draw-0 configuration (same resamples for all: paired).
    need = [r for r in results if r.draw == 0]
    boots = Parallel(n_jobs=n_jobs)(
        delayed(bootstrap_metrics)(
            y_val,
            r.scores,
            r.metrics["threshold"],
            cfg.bootstrap.n_resamples,
            boot_seed,
            cfg.bootstrap.confidence,
        )
        for r in need
    )
    for r, (intervals, auprc_samples) in zip(need, boots, strict=True):
        r.intervals, r.auprc_samples = intervals, auprc_samples
    return Phase2Results(y_val, val[ROW_ID].to_numpy(), reps, sets, results, boot_seed, cross_seed)
