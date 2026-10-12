"""Fraud, calibration and ranking metrics; stratified bootstrap (Phase 2)."""

from __future__ import annotations

import numpy as np
import pytest
from scipy import stats
from sklearn.calibration import calibration_curve
from sklearn.metrics import (
    average_precision_score,
    fbeta_score,
    precision_score,
    recall_score,
    roc_auc_score,
)

from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import (
    bootstrap_distribution,
    percentile_interval,
    stratified_weights,
)


@pytest.fixture(scope="module")
def data():
    rng = np.random.default_rng(0)
    y = (rng.random(3000) < 0.03).astype(int)
    s = np.clip(rng.normal(0.2 + 0.5 * y, 0.2), 0, 1)
    s[:50] = np.round(s[:50], 1)  # create ties
    return y, s


def test_discrimination_matches_sklearn(data):
    y, s = data
    assert M.average_precision(y, s) == average_precision_score(y, s)
    assert M.roc_auc(y, s) == roc_auc_score(y, s)


def test_threshold_metrics_match_sklearn(data):
    y, s = data
    for tau in (0.0, 0.3, 0.5, 0.8, 2.0):
        pred = (s >= tau).astype(int)
        got = M.threshold_metrics(y, s, tau)
        assert got["precision"] == pytest.approx(precision_score(y, pred, zero_division=0))
        assert got["recall"] == pytest.approx(recall_score(y, pred, zero_division=0))
        assert got["f1"] == pytest.approx(fbeta_score(y, pred, beta=1, zero_division=0))
        assert got["f2"] == pytest.approx(fbeta_score(y, pred, beta=2, zero_division=0))


def test_weights_equal_duplicated_rows(data):
    y, s = data
    w = np.random.default_rng(1).integers(0, 4, len(y)).astype(float)
    idx = np.repeat(np.arange(len(y)), w.astype(int))
    assert M.average_precision(y, s, w) == pytest.approx(average_precision_score(y[idx], s[idx]))
    assert M.roc_auc(y, s, w) == pytest.approx(roc_auc_score(y[idx], s[idx]))
    assert M.brier(y, s, w) == pytest.approx(np.mean((s[idx] - y[idx]) ** 2))
    a = M.threshold_metrics(y, s, 0.5, w)
    b = M.threshold_metrics(y[idx], s[idx], 0.5)
    assert a == pytest.approx(b)


def test_max_f1_threshold_and_ties():
    y = np.array([0, 0, 1, 1, 0, 1])
    s = np.array([0.1, 0.2, 0.7, 0.8, 0.75, 0.9])
    tau = M.max_f1_threshold(y, s)
    f1 = M.threshold_metrics(y, s, tau)["f1"]
    for t in s:  # no other threshold does better
        assert M.threshold_metrics(y, s, t)["f1"] <= f1 + 1e-12
    # Tie: thresholds 0.9 and 0.6 both give F1 = 2/3; the highest threshold is chosen.
    y2, s2 = np.array([1, 0, 0, 1]), np.array([0.9, 0.8, 0.7, 0.6])
    assert M.threshold_metrics(y2, s2, 0.9)["f1"] == pytest.approx(2 / 3)
    assert M.threshold_metrics(y2, s2, 0.6)["f1"] == pytest.approx(2 / 3)
    assert M.max_f1_threshold(y2, s2) == pytest.approx(0.9)


def test_calibration_bins_match_sklearn(data):
    y, s = data
    for strategy in ("uniform", "quantile"):
        bins = M.calibration_bins(y, s, 10, strategy)
        prob_true, prob_pred = calibration_curve(y, s, n_bins=10, strategy=strategy)
        np.testing.assert_allclose([b["fraction_positive"] for b in bins], prob_true)
        np.testing.assert_allclose([b["mean_predicted"] for b in bins], prob_pred)
        assert sum(b["count"] for b in bins) == len(y)


def test_ece_hand_computed():
    y = np.array([0, 0, 1, 1])
    p = np.array([0.05, 0.15, 0.95, 0.85])
    # bins: [0,.1]: p=.05,y=0 ; (.1,.2]: p=.15,y=0 ; (.8,.9]: .85,1 ; (.9,1]: .95,1
    expected = (0.05 + 0.15 + 0.15 + 0.05) / 4
    assert M.expected_calibration_error(y, p, 10, "uniform") == pytest.approx(expected)
    with pytest.raises(ValueError):
        M.calibration_bins(y, p + 1.0)


def test_precision_at_k_and_recall_at_precision():
    y = np.array([1, 0, 1, 0, 0, 1])
    s = np.array([0.9, 0.8, 0.8, 0.3, 0.2, 0.1])
    assert M.precision_at_k(y, s, 1) == 1.0
    assert M.precision_at_k(y, s, 2) == 0.5  # tie at 0.8 keeps input order: row 1 (legit) first
    assert M.precision_at_k(y, s, 3) == pytest.approx(2 / 3)
    assert M.recall_at_precision(y, s, 0.6) == pytest.approx(2 / 3)
    assert np.isnan(M.recall_at_precision(np.array([0, 1]), np.array([0.9, 0.1]), 0.9))


def test_interpolated_precision_is_non_increasing(data):
    y, s = data
    p = M.interpolated_precision(y, s, np.linspace(0, 1, 51))
    assert np.all(np.diff(p) <= 1e-12) and p[0] <= 1.0


def test_ranking_distortion_utilities(data):
    _, s = data
    t = s * 0.5 + 0.1  # monotone transform
    assert M.spearman(s, t) == pytest.approx(1.0)
    assert M.kendall(s, t) == pytest.approx(stats.kendalltau(s, t).statistic)
    assert M.top_k_overlap(s, t, 100) == 1.0
    assert M.mean_abs_score_shift(s, s) == 0.0
    assert M.threshold_crossing_fraction(s, s, 0.5) == 0.0
    assert M.threshold_crossing_fraction(s, t, 0.5) == pytest.approx(
        np.mean((s >= 0.5) != (t >= 0.5))
    )
    assert M.spearman(s, -s) == pytest.approx(-1.0)


# ------------------------------------------------------------------------ bootstrap


def test_bootstrap_keeps_class_counts_and_is_deterministic(data):
    y, _ = data
    n_pos = int(y.sum())
    a = list(stratified_weights(y, 20, seed=7))
    b = list(stratified_weights(y, 20, seed=7))
    c = list(stratified_weights(y, 20, seed=8))
    for w in a:
        assert w[y == 1].sum() == n_pos and w[y == 0].sum() == len(y) - n_pos
    assert all(np.array_equal(u, v) for u, v in zip(a, b, strict=True))
    assert not all(np.array_equal(u, v) for u, v in zip(a, c, strict=True))


def test_bootstrap_weights_equal_materialized_resample(data):
    y, s = data
    w = next(stratified_weights(y, 1, seed=3))
    idx = np.repeat(np.arange(len(y)), w.astype(int))
    assert M.average_precision(y, s, w) == pytest.approx(average_precision_score(y[idx], s[idx]))


def test_bootstrap_distribution_and_interval(data):
    y, s = data
    out = bootstrap_distribution(y, {"ap": lambda w: M.average_precision(y, s, w)}, 200, seed=1)
    lo, hi = percentile_interval(out["ap"], 0.95)
    assert lo < M.average_precision(y, s) < hi
    again = bootstrap_distribution(y, {"ap": lambda w: M.average_precision(y, s, w)}, 200, seed=1)
    np.testing.assert_array_equal(out["ap"], again["ap"])


def test_bootstrap_requires_both_classes():
    with pytest.raises(ValueError):
        next(stratified_weights(np.zeros(10, dtype=int), 1, seed=0))
