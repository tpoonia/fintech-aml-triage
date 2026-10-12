"""Robust symmetric angle encoding (O03; PI Phase 3A decision).

For each input feature, fitted on ``vqc_train`` rows only:

    r       = (x - median) / IQR             (IQR = Q75 - Q25, NumPy linear percentiles)
    r_clip  = clip(r, -c, c)                  (c = 3 IQR units, provisional)
    theta   = (pi / c) * r_clip               -> theta in [-pi, pi]

Sign and local magnitude are preserved; heavy tails saturate at +-pi instead of
compressing the legitimate population.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from qtrace.config.schemas import AngleEncodingConfig
from qtrace.utils.hashing import stable_hash


class AngleEncoder(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    kind: Literal["robust_symmetric"] = "robust_symmetric"
    features: tuple[str, ...]
    median: tuple[float, ...]
    iqr: tuple[float, ...]
    clip: float
    quantile_range: tuple[float, float]
    fit_partition: Literal["vqc_train"] = "vqc_train"
    fit_rows: int
    fit_rows_sha256: str

    def artifact_sha256(self) -> str:
        return stable_hash(self)

    def robust(self, frame: pd.DataFrame) -> np.ndarray:
        x = frame[list(self.features)].to_numpy(dtype=np.float64)
        return (x - np.array(self.median)) / np.array(self.iqr)

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        """Angles in [-pi, pi], one column per feature (= per qubit)."""
        return (np.pi / self.clip) * np.clip(self.robust(frame), -self.clip, self.clip)

    def clip_fractions(self, frame: pd.DataFrame) -> dict[str, float]:
        clipped = np.abs(self.robust(frame)) > self.clip
        return {f: float(v) for f, v in zip(self.features, clipped.mean(axis=0), strict=True)}


def fit_angle_encoder(
    cfg: AngleEncodingConfig, train: pd.DataFrame, features: tuple[str, ...], fit_rows_sha256: str
) -> AngleEncoder:
    """Fit on the rows passed in, which must be vqc_train (the caller's responsibility)."""
    x = train[list(features)].to_numpy(dtype=np.float64)
    low, high = cfg.quantile_range
    q_low, median, q_high = np.percentile(x, [low, 50.0, high], axis=0, method="linear")
    iqr = q_high - q_low
    if (iqr <= 0).any():
        raise ValueError("zero interquartile range: cannot encode")
    return AngleEncoder(
        features=tuple(features),
        median=tuple(float(v) for v in median),
        iqr=tuple(float(v) for v in iqr),
        clip=cfg.clip,
        quantile_range=cfg.quantile_range,
        fit_rows=len(train),
        fit_rows_sha256=fit_rows_sha256,
    )
