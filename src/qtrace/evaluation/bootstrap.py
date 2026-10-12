"""Stratified bootstrap with fixed class counts.

Procedure: each resample draws, with replacement, exactly ``n_pos`` rows from
the positives and ``n_neg`` rows from the negatives of the evaluation set.
Every resample therefore contains the original number of frauds and can never
be empty of positives. Resamples are represented as multiplicity weights, which
the scikit-learn metrics accept as ``sample_weight``; this is equivalent to
materializing the resampled rows (tested). One seeded generator produces the
whole sequence, so all models evaluated on the same rows see the *same*
resamples (common random numbers), enabling paired differences. Intervals are
percentile intervals. They describe evaluation-set sampling variability only:
they do not include threshold-selection or training variability.
"""

from __future__ import annotations

from collections.abc import Callable, Iterator

import numpy as np


def stratified_weights(y, n_resamples: int, seed: int) -> Iterator[np.ndarray]:
    y = np.asarray(y)
    pos, neg = np.flatnonzero(y == 1), np.flatnonzero(y == 0)
    if len(pos) == 0 or len(neg) == 0:
        raise ValueError("stratified bootstrap needs both classes")
    rng = np.random.default_rng(seed)
    for _ in range(n_resamples):
        idx = np.concatenate(
            [rng.choice(pos, size=len(pos), replace=True), rng.choice(neg, size=len(neg))]
        )
        yield np.bincount(idx, minlength=len(y)).astype(np.float64)


def bootstrap_distribution(
    y, metric_fns: dict[str, Callable[[np.ndarray], float]], n_resamples: int, seed: int
) -> dict[str, np.ndarray]:
    """Evaluate ``fn(weights)`` for every metric on every resample."""
    out = {name: np.empty(n_resamples) for name in metric_fns}
    for b, weights in enumerate(stratified_weights(y, n_resamples, seed)):
        for name, fn in metric_fns.items():
            out[name][b] = fn(weights)
    return out


def percentile_interval(samples: np.ndarray, confidence: float) -> tuple[float, float]:
    alpha = (1 - confidence) / 2
    lo, hi = np.percentile(samples, [100 * alpha, 100 * (1 - alpha)])
    return float(lo), float(hi)
