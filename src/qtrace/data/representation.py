"""Candidate low-dimensional input representations (evidence for O02, not a decision).

All learned parameters are fitted on ``vqc_train`` only (the caller passes those
rows) and stored explicitly, so a representation is fully described by its
parameters and their hash.

* ``full``: the 30 preprocessed features unchanged (classical reference).
* ``pca``: ``sklearn.decomposition.PCA(n_components, svd_solver="full")``,
  optionally after standardization with training mean and standard deviation.
  ``transform(X) = (Z - mean) @ components.T``.
* ``select_k_best``: features ranked by ``sklearn.feature_selection.f_classif``
  (one-way ANOVA F statistic of each feature against the label on the training
  rows); the ``k`` highest are kept, ties broken by original column order, and
  output in descending-score order.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict
from sklearn.decomposition import PCA
from sklearn.feature_selection import f_classif

from qtrace.config.schemas import RepresentationConfig
from qtrace.utils.hashing import stable_hash


class FittedRepresentation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rep_id: str
    kind: Literal["full", "pca", "select_k_best"]
    input_columns: tuple[str, ...]
    output_columns: tuple[str, ...]
    fit_partition: Literal["vqc_train"] = "vqc_train"
    fit_rows: int
    fit_rows_sha256: str
    standardize_mean: tuple[float, ...] | None = None
    standardize_scale: tuple[float, ...] | None = None
    pca_mean: tuple[float, ...] | None = None
    pca_components: tuple[tuple[float, ...], ...] | None = None
    explained_variance_ratio: tuple[float, ...] | None = None
    selector_scores: dict[str, float] | None = None

    def artifact_sha256(self) -> str:
        return stable_hash(self)

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        x = frame[list(self.input_columns)].to_numpy(dtype=np.float64)
        if self.kind == "full":
            return x
        if self.kind == "select_k_best":
            return frame[list(self.output_columns)].to_numpy(dtype=np.float64)
        if self.standardize_mean is not None:
            x = (x - np.array(self.standardize_mean)) / np.array(self.standardize_scale)
        return (x - np.array(self.pca_mean)) @ np.array(self.pca_components).T


def fit_representation(
    cfg: RepresentationConfig,
    train: pd.DataFrame,
    target: str,
    feature_columns: tuple[str, ...],
    fit_rows_sha256: str,
) -> FittedRepresentation:
    x = train[list(feature_columns)].to_numpy(dtype=np.float64)
    y = train[target].to_numpy()
    common = {
        "rep_id": cfg.rep_id,
        "kind": cfg.kind,
        "input_columns": tuple(feature_columns),
        "fit_rows": len(train),
        "fit_rows_sha256": fit_rows_sha256,
    }
    if cfg.kind == "full":
        return FittedRepresentation(**common, output_columns=tuple(feature_columns))
    if cfg.kind == "select_k_best":
        scores, _ = f_classif(x, y)
        order = sorted(range(len(feature_columns)), key=lambda i: (-scores[i], i))
        chosen = tuple(feature_columns[i] for i in order[: cfg.n_components])
        return FittedRepresentation(
            **common,
            output_columns=chosen,
            selector_scores={c: float(s) for c, s in zip(feature_columns, scores, strict=True)},
        )
    extra = {}
    if cfg.standardize:
        mean, scale = x.mean(axis=0), x.std(axis=0)
        if (scale == 0).any():
            raise ValueError("cannot standardize a constant feature")
        x = (x - mean) / scale
        extra = {
            "standardize_mean": tuple(mean.tolist()),
            "standardize_scale": tuple(scale.tolist()),
        }
    pca = PCA(n_components=cfg.n_components, svd_solver="full").fit(x)
    return FittedRepresentation(
        **common,
        **extra,
        output_columns=tuple(f"{cfg.rep_id}_pc{i + 1}" for i in range(cfg.n_components)),
        pca_mean=tuple(pca.mean_.tolist()),
        pca_components=tuple(tuple(row) for row in pca.components_.tolist()),
        explained_variance_ratio=tuple(pca.explained_variance_ratio_.tolist()),
    )
