"""Fixed-hyperparameter scikit-learn fraud classifiers (Phase 2; no XGBoost)."""

from __future__ import annotations

from sklearn.base import ClassifierMixin
from sklearn.ensemble import HistGradientBoostingClassifier, RandomForestClassifier
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline, make_pipeline
from sklearn.preprocessing import StandardScaler

from qtrace.config.schemas import ClassicalModelConfig


def build_model(
    cfg: ClassicalModelConfig, class_weight: str | None, seed: int
) -> ClassifierMixin | Pipeline:
    """Return an unfitted estimator. ``seed`` must fit in 32 bits."""
    params = dict(cfg.params)
    if cfg.kind == "logistic_regression":
        # Standardization is part of the model and is fitted on the training rows only.
        return make_pipeline(
            StandardScaler(),
            LogisticRegression(**params, class_weight=class_weight, random_state=seed),
        )
    if cfg.kind == "random_forest":
        return RandomForestClassifier(
            **params, class_weight=class_weight, n_jobs=-1, random_state=seed
        )
    if cfg.kind == "hist_gradient_boosting":
        return HistGradientBoostingClassifier(
            **params, class_weight=class_weight, random_state=seed
        )
    raise ValueError(f"unknown model kind {cfg.kind!r}")
