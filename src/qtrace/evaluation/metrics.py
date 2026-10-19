"""Fraud, calibration and ranking-distortion metrics.

scikit-learn definitions are used wherever they exist. Conventions for the rest:

* **Decision rule**: a transaction is flagged iff ``score >= threshold``.
* **Threshold criterion** (``max_f1_threshold``): the threshold maximizing F1
  over all distinct scores (``precision_recall_curve``); ties go to the highest
  threshold.
* **Precision/recall/F-beta at a threshold** use confusion counts; with
  ``zero_division`` the value is 0.0 (matches scikit-learn ``zero_division=0``).
* **ECE**: equal-width (``uniform``) or equal-mass (``quantile``) bins with the
  exact bin assignment of ``sklearn.calibration.calibration_curve``: edges
  ``linspace(0, 1, n+1)``; bin *i* is ``(e_i, e_{i+1}]`` except the first,
  which also contains 0. ECE = sum over non-empty bins of
  ``(n_b / N) * |mean(y)_b - mean(p)_b|``.
* **precision@k**: scores sorted descending with a stable sort, so ties keep
  input order (callers pass rows ordered by ``row_id``).
* **recall@precision**: the largest recall over real operating points (the
  artificial ``(P=1, R=0)`` end point is excluded) whose precision reaches the
  target; ``nan`` when no operating point reaches it.
"""

from __future__ import annotations

import numpy as np
from scipy import stats
from sklearn.metrics import (
    average_precision_score,
    brier_score_loss,
    precision_recall_curve,
    roc_auc_score,
)


def _arr(x) -> np.ndarray:
    return np.asarray(x, dtype=np.float64)


# ----------------------------------------------------------------- discrimination


def average_precision(y, scores, weights=None) -> float:
    return float(average_precision_score(y, scores, sample_weight=weights))


def roc_auc(y, scores, weights=None) -> float:
    return float(roc_auc_score(y, scores, sample_weight=weights))


def max_f1_threshold(y, scores) -> float:
    precision, recall, thresholds = precision_recall_curve(y, scores)
    p, r = precision[:-1], recall[:-1]  # drop the artificial end point (no threshold)
    with np.errstate(divide="ignore", invalid="ignore"):
        f1 = np.where(p + r > 0, 2 * p * r / (p + r), 0.0)
    best = np.flatnonzero(f1 == f1.max())
    return float(thresholds[best.max()])  # thresholds ascend: highest threshold among ties


def confusion_at(y, scores, threshold: float, weights=None) -> tuple[float, float, float, float]:
    y, s = _arr(y), _arr(scores)
    w = np.ones_like(y) if weights is None else _arr(weights)
    flagged = s >= threshold
    tp = float(np.sum(w * flagged * y))
    fp = float(np.sum(w * flagged * (1 - y)))
    fn = float(np.sum(w * ~flagged * y))
    tn = float(np.sum(w * ~flagged * (1 - y)))
    return tp, fp, fn, tn


def _ratio(num: float, den: float) -> float:
    return num / den if den > 0 else 0.0


def fbeta_from_counts(tp: float, fp: float, fn: float, beta: float) -> float:
    b2 = beta * beta
    return _ratio((1 + b2) * tp, (1 + b2) * tp + b2 * fn + fp)


def threshold_metrics(y, scores, threshold: float, weights=None) -> dict[str, float]:
    tp, fp, fn, _ = confusion_at(y, scores, threshold, weights)
    return {
        "precision": _ratio(tp, tp + fp),
        "recall": _ratio(tp, tp + fn),
        "f1": fbeta_from_counts(tp, fp, fn, 1.0),
        "f2": fbeta_from_counts(tp, fp, fn, 2.0),
    }


def precision_at_k(y, scores, k: int) -> float:
    y, s = _arr(y), _arr(scores)
    order = np.argsort(-s, kind="stable")
    return float(y[order[: min(k, len(y))]].mean())


def recall_at_precision(y, scores, target: float) -> float:
    precision, recall, _ = precision_recall_curve(y, scores)
    ok = precision[:-1] >= target
    return float(recall[:-1][ok].max()) if ok.any() else float("nan")


def interpolated_precision(y, scores, recall_grid) -> np.ndarray:
    """Interpolated precision: max precision at recall >= r, for each grid point r."""
    precision, recall, _ = precision_recall_curve(y, scores)
    grid = _arr(recall_grid)
    return np.array([precision[recall >= r].max() if (recall >= r).any() else 0.0 for r in grid])


# -------------------------------------------------------------------- calibration


def brier(y, probs, weights=None) -> float:
    return float(brier_score_loss(y, probs, sample_weight=weights))


def _bin_edges(probs: np.ndarray, n_bins: int, strategy: str) -> np.ndarray:
    if strategy == "uniform":
        return np.linspace(0.0, 1.0, n_bins + 1)
    if strategy == "quantile":
        return np.percentile(probs, np.linspace(0, 1, n_bins + 1) * 100)
    raise ValueError(f"unknown binning strategy {strategy!r}")


def calibration_bins(y, probs, n_bins: int = 10, strategy: str = "uniform") -> list[dict]:
    """Per-bin counts, mean predicted probability and observed fraud rate (non-empty bins)."""
    y, p = _arr(y), _arr(probs)
    if p.min() < 0 or p.max() > 1:
        raise ValueError("probabilities must lie in [0, 1]")
    edges = _bin_edges(p, n_bins, strategy)
    ids = np.searchsorted(edges[1:-1], p)  # identical to sklearn.calibration.calibration_curve
    out = []
    for b in range(len(edges) - 1):
        mask = ids == b
        if mask.any():
            out.append(
                {
                    "bin": b,
                    "lower": float(edges[b]),
                    "upper": float(edges[b + 1]),
                    "count": int(mask.sum()),
                    "mean_predicted": float(p[mask].mean()),
                    "fraction_positive": float(y[mask].mean()),
                }
            )
    return out


def expected_calibration_error_weighted(y, probs, weights, n_bins: int = 10) -> float:
    """Equal-width-bin ECE with sample weights (e.g. bootstrap multiplicities).

    Same bin assignment as ``calibration_bins(strategy="uniform")``; equals the
    unweighted ECE on the materialized resample (tested).
    """
    y, p, w = _arr(y), _arr(probs), _arr(weights)
    edges = np.linspace(0.0, 1.0, n_bins + 1)
    ids = np.searchsorted(edges[1:-1], p)
    count = np.bincount(ids, weights=w, minlength=n_bins)
    pred = np.bincount(ids, weights=w * p, minlength=n_bins)
    pos = np.bincount(ids, weights=w * y, minlength=n_bins)
    keep = count > 0
    return float(np.sum(np.abs(pos[keep] - pred[keep])) / count.sum())


def expected_calibration_error(y, probs, n_bins: int = 10, strategy: str = "uniform") -> float:
    bins = calibration_bins(y, probs, n_bins, strategy)
    total = sum(b["count"] for b in bins)
    return float(
        sum(b["count"] / total * abs(b["fraction_positive"] - b["mean_predicted"]) for b in bins)
    )


# ------------------------------------------------- ranking / distortion (A13, later phases)


def spearman(a, b) -> float:
    return float(stats.spearmanr(_arr(a), _arr(b)).statistic)


def kendall(a, b) -> float:
    return float(stats.kendalltau(_arr(a), _arr(b)).statistic)


def threshold_crossing_fraction(
    a, b, threshold_a: float, threshold_b: float | None = None
) -> float:
    """Fraction of items whose flag decision differs between two score vectors."""
    threshold_b = threshold_a if threshold_b is None else threshold_b
    return float(np.mean((_arr(a) >= threshold_a) != (_arr(b) >= threshold_b)))


def mean_abs_score_shift(a, b) -> float:
    return float(np.mean(np.abs(_arr(a) - _arr(b))))


def top_k_overlap(a, b, k: int) -> float:
    """|top-k(a) ∩ top-k(b)| / k with stable tie-breaking."""
    top_a = set(np.argsort(-_arr(a), kind="stable")[:k].tolist())
    top_b = set(np.argsort(-_arr(b), kind="stable")[:k].tolist())
    return len(top_a & top_b) / k
