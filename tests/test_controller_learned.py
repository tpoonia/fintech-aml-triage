"""Learned-policy tooling on synthetic controller tables: both formulations recover a known
decision structure; structure-grouped folds never split a structure; unknown categories fail."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtrace.controller import learned as L

ORDER = ("A0", "A1", "A4", "A2", "A3")


def _synthetic(n=3000, seed=0):
    rng = np.random.default_rng(seed)
    feats = pd.DataFrame(
        {
            "probe_readout_error_mean": rng.uniform(0, 0.05, n),
            "probe_gate_contraction": rng.uniform(0.3, 1.0, n),
            "noisy_depth": rng.integers(10, 30, n).astype(float),
            "readout_observable": rng.choice(["parity", "mean_z"], n),
            "ansatz": rng.choice(["efficient_su2", "real_amplitudes"], n),
        }
    )
    ro = feats.probe_readout_error_mean.to_numpy()
    ga = feats.probe_gate_contraction.to_numpy()
    par = (feats.readout_observable == "parity").to_numpy()
    need_ro = (ro >= 0.01) & par  # mean-Z models do not need readout mitigation here
    need_ga = ga <= 0.8
    target = np.select([need_ro & need_ga, need_ro, need_ga], ["A3", "A1", "A2"], "A0")
    base = 0.02 + 0.8 * ro * par + 0.05 * (1 - ga)
    benefit = pd.DataFrame(
        {
            "A0": np.zeros(n),
            "A1": np.log((base - 0.8 * ro * par) / base),
            "A2": np.log((base - 0.05 * (1 - ga)) / base),
            "A3": np.log((base - 0.8 * ro * par - 0.05 * (1 - ga)) / base),
            "A4": np.log(0.999 * np.ones(n)),
        }
    )
    return feats, pd.Series(target), benefit


def _constrained_truth(benefit: pd.DataFrame, eps: float = 0.10) -> np.ndarray:
    """The registered rule on TRUE ratios: cheapest action within (1 + eps) of the minimum."""
    r = np.exp(benefit[list(L.ACTIONS)].to_numpy())
    ok = r <= (1 + eps) * r.min(axis=1, keepdims=True)
    order = [L.ACTIONS.index(a) for a in ORDER]
    return np.array([L.ACTIONS[order[i]] for i in np.argmax(ok[:, order], axis=1)])


@pytest.mark.parametrize(
    "spec",
    [
        L.Spec("tree", "classify", (("max_depth", 4),)),
        L.Spec("gbt", "classify"),
        L.Spec("forest", "benefit", (("n_estimators", 50),)),
    ],
    ids=lambda s: s.name,
)
def test_formulations_recover_a_known_structure(spec):
    feats, target, benefit = _synthetic()
    if spec.formulation == "benefit":
        target = pd.Series(_constrained_truth(benefit))
    pol = L.fit_policy(spec, feats, target, benefit, 0.10, ORDER, seed=1)
    test_feats, test_target, test_benefit = _synthetic(seed=2)
    truth = _constrained_truth(test_benefit) if spec.formulation == "benefit" else test_target
    acc = (pol.choose(test_feats) == np.asarray(truth)).mean()
    assert acc > 0.9, (spec.name, acc)


def test_group_folds_keep_structures_together():
    groups = pd.Series(np.repeat([f"s{i}" for i in range(8)], 10))
    folds = L.group_folds(groups, 4, seed=0)
    assert sorted(np.concatenate(folds)) == list(range(80))
    for f in folds:
        others = set(groups.drop(index=f))
        assert not set(groups.iloc[f]) & others


def test_unknown_category_is_rejected():
    feats, target, benefit = _synthetic(500)
    pol = L.fit_policy(L.Spec("logistic", "classify"), feats, target, None, 0.1, ORDER, 0)
    bad = feats.assign(ansatz="hardware_efficient")
    with pytest.raises(ValueError):
        pol.choose(bad)
