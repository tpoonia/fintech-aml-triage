"""Learned selective-mitigation policies on the registered observable context.

Inputs are exactly the Phase 5B/5C controller features (16 static + 11 probe), built through
``mixed_controller_table`` (registry and prohibited-list checks). Two formulations:

- **classify**: predict the Oracle action p* directly (multi-class);
- **benefit**: predict each action's context-mean Brier *relative to A0* (log ratio), then
  choose the cheapest action whose predicted Brier is within (1 + eps) of the predicted
  minimum: the registered constrained rule applied to predictions.

Models: multinomial logistic regression, decision tree, random forest, histogram gradient
boosting (scikit-learn). Fitting uses TRAIN rows only; any hyper-parameter choice uses
structure-grouped cross-validation on TRAIN (models of one structure never straddle folds).
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import (
    HistGradientBoostingClassifier,
    HistGradientBoostingRegressor,
    RandomForestClassifier,
    RandomForestRegressor,
)
from sklearn.linear_model import LogisticRegression, Ridge
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler
from sklearn.tree import DecisionTreeClassifier, DecisionTreeRegressor

ACTIONS = ("A0", "A1", "A2", "A3", "A4")
CATEGORICAL = ("ansatz", "readout_observable", "encoding_family", "feature_set")
# Category sets come from the registered pool design (Phase 5A), not from outcomes.
CATEGORIES = {
    "ansatz": ["efficient_su2", "real_amplitudes"],
    "readout_observable": ["mean_z", "parity"],
    "encoding_family": ["e2", "e3", "s5"],
    "feature_set": ["next4", "pca4", "top4"],
}


@dataclass(frozen=True)
class Spec:
    """One candidate: model family, formulation and hyper-parameters (fixed before fitting)."""

    kind: str  # logistic | tree | forest | gbt
    formulation: str  # classify | benefit
    params: tuple[tuple[str, object], ...] = ()

    @property
    def name(self) -> str:
        p = ",".join(f"{k}={v}" for k, v in self.params)
        return f"{self.kind}/{self.formulation}" + (f"[{p}]" if p else "")


def _preprocessor(columns: list[str]) -> ColumnTransformer:
    cats = [c for c in CATEGORICAL if c in columns]
    nums = [c for c in columns if c not in cats]
    return ColumnTransformer(
        [
            ("num", StandardScaler(), nums),
            (
                "cat",
                OneHotEncoder(categories=[CATEGORIES[c] for c in cats], handle_unknown="error"),
                cats,
            ),
        ]
    )


def _estimator(spec: Spec, seed: int, regression: bool):
    p = dict(spec.params)
    if spec.kind == "logistic":
        return (
            Ridge(alpha=p.get("alpha", 1.0))
            if regression
            else LogisticRegression(C=p.get("C", 1.0), max_iter=5000)
        )
    if spec.kind == "tree":
        cls = DecisionTreeRegressor if regression else DecisionTreeClassifier
        return cls(
            max_depth=p.get("max_depth", 3),
            min_samples_leaf=p.get("min_leaf", 50),
            random_state=seed,
        )
    if spec.kind == "forest":
        cls = RandomForestRegressor if regression else RandomForestClassifier
        return cls(
            n_estimators=p.get("n_estimators", 200),
            max_depth=p.get("max_depth", 8),
            min_samples_leaf=p.get("min_leaf", 20),
            random_state=seed,
            n_jobs=1,
        )
    if spec.kind == "gbt":
        cls = HistGradientBoostingRegressor if regression else HistGradientBoostingClassifier
        return cls(
            max_depth=p.get("max_depth", 4),
            learning_rate=p.get("learning_rate", 0.1),
            max_iter=p.get("max_iter", 200),
            random_state=seed,
        )
    raise ValueError(f"unknown model kind {spec.kind!r}")


@dataclass
class FittedPolicy:
    spec: Spec
    columns: list[str]
    models: dict  # "classify" -> pipeline; "benefit" -> {action: pipeline}
    eps: float
    cost_order: tuple[str, ...]

    def choose(self, feats: pd.DataFrame) -> np.ndarray:
        x = feats[self.columns]
        if self.spec.formulation == "classify":
            return self.models["classify"].predict(x).astype(object)
        pred = np.column_stack([self.models[a].predict(x) for a in ACTIONS])  # log(B_a / B_A0)
        ok = pred <= np.log1p(self.eps) + pred.min(axis=1, keepdims=True)
        order = [ACTIONS.index(a) for a in self.cost_order]
        first = np.argmax(ok[:, order], axis=1)
        return np.array([ACTIONS[order[i]] for i in first], dtype=object)


def benefit_targets(orc: pd.DataFrame) -> pd.DataFrame:
    """Per-context log(Brier_a / Brier_A0) for every action (context means; A0 = 0)."""
    return pd.DataFrame(
        {a: np.log(orc[f"brier_{a}"] / orc["brier_A0"]) for a in ACTIONS}, index=orc.index
    )


def fit_policy(
    spec: Spec,
    feats: pd.DataFrame,
    target_action: pd.Series,
    benefit: pd.DataFrame | None,
    eps: float,
    cost_order: tuple[str, ...],
    seed: int,
) -> FittedPolicy:
    """Fit on TRAIN rows: ``feats`` (controller table), the Oracle action per row, and (for
    the benefit formulation) the per-row context-mean log Brier ratios."""
    cols = list(feats.columns)
    if spec.formulation == "classify":
        pipe = Pipeline([("prep", _preprocessor(cols)), ("est", _estimator(spec, seed, False))])
        models = {"classify": pipe.fit(feats, target_action.to_numpy())}
    elif spec.formulation == "benefit":
        if benefit is None:
            raise ValueError("the benefit formulation needs per-action targets")
        models = {}
        for a in ACTIONS:
            pipe = Pipeline([("prep", _preprocessor(cols)), ("est", _estimator(spec, seed, True))])
            models[a] = pipe.fit(feats, benefit[a].to_numpy())
    else:
        raise ValueError(f"unknown formulation {spec.formulation!r}")
    return FittedPolicy(spec, cols, models, eps, cost_order)


def group_folds(groups: pd.Series, n_folds: int, seed: int) -> list[np.ndarray]:
    """Fold index per row: whole structures are assigned to folds (seeded, balanced)."""
    uniq = np.array(sorted(groups.unique()))
    rng = np.random.default_rng(seed)
    order = uniq[rng.permutation(len(uniq))]
    fold_of = {g: i % n_folds for i, g in enumerate(order)}
    f = groups.map(fold_of).to_numpy()
    return [np.flatnonzero(f == k) for k in range(n_folds)]
