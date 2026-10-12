"""Aggregate, deterministic Phase 2 output tables (no transaction-level data)."""

from __future__ import annotations

from typing import Any

import numpy as np
import pandas as pd

from qtrace.classical.runner import CI_METRICS, Phase2Results
from qtrace.config.schemas import ClassicalBaselineConfig
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import percentile_interval

DIGITS = 6


def _round(frame: pd.DataFrame) -> pd.DataFrame:
    return frame.round(DIGITS)


def _full_regimes(cfg: ClassicalBaselineConfig) -> set[str]:
    return {r.regime_id for r in cfg.regimes if r.kind == "full_partition"}


def metrics_table(res: Phase2Results) -> pd.DataFrame:
    rows = []
    for r in res.results:
        row: dict[str, Any] = {
            "regime": r.regime_id,
            "draw": r.draw,
            "model": r.model_id,
            "representation": r.rep_id,
            "n_train": r.n_train,
            "n_train_fraud": r.n_train_fraud,
            "train_rows_sha256": r.train_rows_sha256,
            "model_seed": r.model_seed,
        }
        for name, value in r.metrics.items():
            row[name] = value
            if name in CI_METRICS:
                lo, hi = r.intervals.get(name, (np.nan, np.nan))
                row[f"{name}_ci_low"], row[f"{name}_ci_high"] = lo, hi
        rows.append(row)
    return _round(pd.DataFrame(rows))


def regime_summary(res: Phase2Results) -> pd.DataFrame:
    """Across subset draws: how much is lost by training at VQC scale (Regime B vs A)."""
    frame = pd.DataFrame(
        [
            {
                "regime": r.regime_id,
                "model": r.model_id,
                "representation": r.rep_id,
                "n_train": r.n_train,
                "auprc": r.metrics["auprc"],
                "auroc": r.metrics["auroc"],
            }
            for r in res.results
        ]
    )
    out = (
        frame.groupby(["regime", "model", "representation"], sort=False)
        .agg(
            draws=("auprc", "size"),
            n_train=("n_train", "first"),
            auprc_mean=("auprc", "mean"),
            auprc_min=("auprc", "min"),
            auprc_max=("auprc", "max"),
            auroc_mean=("auroc", "mean"),
        )
        .reset_index()
    )
    return _round(out)


def representation_comparison(res: Phase2Results, confidence: float) -> pd.DataFrame:
    """Paired bootstrap difference in AUPRC: representation minus full features (draw 0)."""
    base = {(r.model_id, r.regime_id): r for r in res.results if r.draw == 0 and r.rep_id == "full"}
    rows = []
    for r in res.results:
        if r.draw != 0 or r.rep_id == "full":
            continue
        ref = base[(r.model_id, r.regime_id)]
        delta = r.auprc_samples - ref.auprc_samples
        lo, hi = percentile_interval(delta, confidence)
        rows.append(
            {
                "regime": r.regime_id,
                "model": r.model_id,
                "representation": r.rep_id,
                "auprc": r.metrics["auprc"],
                "auprc_full": ref.metrics["auprc"],
                "delta_auprc": r.metrics["auprc"] - ref.metrics["auprc"],
                "delta_ci_low": lo,
                "delta_ci_high": hi,
                "fraction_resamples_worse": float(np.mean(delta < 0)),
            }
        )
    return _round(pd.DataFrame(rows))


def calibration_table(res: Phase2Results, cfg: ClassicalBaselineConfig) -> pd.DataFrame:
    """Calibration-curve data for the principal baselines (full partition, full features)."""
    rows = []
    for r in res.results:
        if r.regime_id in _full_regimes(cfg) and r.rep_id == "full":
            for strategy in (cfg.calibration.strategy, cfg.calibration.sensitivity_strategy):
                for b in M.calibration_bins(res.y_val, r.scores, cfg.calibration.n_bins, strategy):
                    rows.append({"model": r.model_id, "strategy": strategy, **b})
    return _round(pd.DataFrame(rows))


def pr_curve_table(res: Phase2Results, cfg: ClassicalBaselineConfig) -> pd.DataFrame:
    """Interpolated precision on a fixed recall grid for the full-partition regime(s).

    Aggregate only (no per-row scores). Restricted to full-partition training so
    the table stays small; every regime's AUPRC is in the metrics table.
    """
    grid = np.linspace(0.0, 1.0, cfg.pr_recall_grid_points)
    rows = []
    for r in res.results:
        if r.draw != 0 or r.regime_id not in _full_regimes(cfg):
            continue
        precision = M.interpolated_precision(res.y_val, r.scores, grid)
        for recall, p in zip(grid, precision, strict=True):
            rows.append(
                {
                    "regime": r.regime_id,
                    "model": r.model_id,
                    "representation": r.rep_id,
                    "recall": recall,
                    "interpolated_precision": p,
                }
            )
    return _round(pd.DataFrame(rows))


def metadata(res: Phase2Results, cfg: ClassicalBaselineConfig, context: dict) -> dict:
    reps = {}
    for rep_id, rep in res.representations.items():
        entry: dict[str, Any] = {
            "kind": rep.kind,
            "artifact_sha256": rep.artifact_sha256(),
            "fit_partition": rep.fit_partition,
            "fit_rows": rep.fit_rows,
            "output_columns": list(rep.output_columns),
        }
        if rep.explained_variance_ratio is not None:
            entry["explained_variance_ratio"] = [
                round(v, DIGITS) for v in rep.explained_variance_ratio
            ]
            entry["components"] = [[round(v, DIGITS) for v in row] for row in rep.pca_components]
            entry["component_input_columns"] = list(rep.input_columns)
        if rep.selector_scores is not None:
            entry["f_classif_scores"] = {k: round(v, 3) for k, v in rep.selector_scores.items()}
        reps[rep_id] = entry
    subsets = [
        {
            "regime": ts.regime_id,
            "draw": ts.draw,
            "subset_id": ts.subset.spec.subset_id,
            "undersample_master_seed": ts.subset.undersample_master_seed,
            "n_fraud": ts.subset.n_fraud,
            "n_legit": ts.subset.n_legit,
            "row_ids_sha256": ts.subset.row_ids_sha256,
        }
        for ts in res.training_sets
        if ts.subset is not None
    ]
    return {
        **context,
        "evaluation": {
            "partition": cfg.eval_partition,
            "rows": len(res.y_val),
            "fraud": int(res.y_val.sum()),
            "prevalence": round(float(res.y_val.mean()), 8),
        },
        "threshold_selection": cfg.threshold.model_dump(mode="json")
        | {
            "selected_on": cfg.eval_partition,
            "note": "threshold metrics are optimistic: tuned "
            "and reported on the same partition; f1_crossfit is the honest comparison",
        },
        "bootstrap": cfg.bootstrap.model_dump(mode="json")
        | {
            "seed_stream": "bootstrap",
            "derived_seed": res.bootstrap_seed,
            "applied_to": "every draw-0 configuration, identical resamples (paired)",
        },
        "crossfit_seed": res.crossfit_seed,
        "calibration": cfg.calibration.model_dump(mode="json"),
        "representations": reps,
        "regime_b_subsets": subsets,
    }
