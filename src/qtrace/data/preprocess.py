"""Leakage-safe preprocessing [RR §Transaction preprocessing; F15; A04].

``Amount`` -> log1p -> robust scaling; ``Time`` -> robust scaling;
``V1``-``V28`` pass through unchanged. Every learned parameter (medians and
quantiles) is computed from the ``vqc_train`` partition only: the fit function
selects those rows itself, so no other partition can reach it.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from qtrace.config.schemas import DatasetConfig
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import partition_ids
from qtrace.utils.hashing import stable_hash

TIME_OUT = "time_robust"
AMOUNT_OUT = "amount_log1p_robust"


class PreprocessingError(ValueError):
    pass


class RobustColumnParams(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    column: str
    output: str
    transform: Literal["identity", "log1p"]
    center: float  # median of the (transformed) training values
    q_low: float
    q_high: float
    scale: float  # q_high - q_low


class FittedPreprocessor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    version: Literal["1"] = "1"
    dataset_id: str
    dataset_sha256: str
    fit_partition: str
    fit_partition_rows: int
    fit_partition_hash: str
    quantile_range: tuple[float, float]
    quantile_method: Literal["linear"] = "linear"
    scaled: tuple[RobustColumnParams, ...]
    passthrough_columns: tuple[str, ...]
    output_columns: tuple[str, ...]

    def artifact_sha256(self) -> str:
        return stable_hash(self)


def fit_partition_hash(dataset_sha256: str, partition: str, ids: np.ndarray) -> str:
    return stable_hash(
        {"dataset_sha256": dataset_sha256, "partition": partition, "row_ids": row_ids_sha256(ids)}
    )


def _robust_params(values: np.ndarray, column: str, output: str, transform, q_range):
    low, high = q_range
    q_low, center, q_high = np.percentile(values, [low, 50.0, high], method="linear")
    scale = float(q_high - q_low)
    if not np.isfinite(scale) or scale <= 0:
        raise PreprocessingError(f"zero or invalid interquantile range for {column}")
    return RobustColumnParams(
        column=column,
        output=output,
        transform=transform,
        center=float(center),
        q_low=float(q_low),
        q_high=float(q_high),
        scale=scale,
    )


def fit_preprocessor(
    frame: pd.DataFrame, assignment: pd.DataFrame, config: DatasetConfig, dataset_sha256: str
) -> FittedPreprocessor:
    prep = config.preprocessing
    ids = partition_ids(assignment, prep.fit_on)
    if len(ids) == 0:
        raise PreprocessingError(f"partition {prep.fit_on!r} is empty")
    train = frame.loc[frame[ROW_ID].isin(ids)]
    amounts = train["Amount"].to_numpy(dtype=np.float64)
    if (amounts < 0).any():
        raise PreprocessingError("negative Amount: log1p is not valid")
    scaled = (
        _robust_params(
            train["Time"].to_numpy(dtype=np.float64),
            "Time",
            TIME_OUT,
            "identity",
            prep.quantile_range,
        ),
        _robust_params(np.log1p(amounts), "Amount", AMOUNT_OUT, "log1p", prep.quantile_range),
    )
    passthrough = tuple(c for c in config.feature_columns if c not in {"Time", "Amount"})
    outputs = tuple(
        TIME_OUT if c == "Time" else AMOUNT_OUT if c == "Amount" else c
        for c in config.feature_columns
    )
    return FittedPreprocessor(
        dataset_id=config.dataset_id,
        dataset_sha256=dataset_sha256,
        fit_partition=prep.fit_on,
        fit_partition_rows=len(train),
        fit_partition_hash=fit_partition_hash(dataset_sha256, prep.fit_on, ids),
        quantile_range=prep.quantile_range,
        scaled=scaled,
        passthrough_columns=passthrough,
        output_columns=outputs,
    )


def transform(frame: pd.DataFrame, fitted: FittedPreprocessor, target: str) -> pd.DataFrame:
    """Apply fitted parameters to any rows. Learns nothing."""
    out = pd.DataFrame({ROW_ID: frame[ROW_ID].to_numpy()})
    params = {p.column: p for p in fitted.scaled}
    for column, output in zip(
        (*params, *fitted.passthrough_columns),
        (*(p.output for p in params.values()), *fitted.passthrough_columns),
        strict=True,
    ):
        values = frame[column].to_numpy(dtype=np.float64)
        if column in params:
            p = params[column]
            if p.transform == "log1p":
                if (values < 0).any():
                    raise PreprocessingError("negative Amount: log1p is not valid")
                values = np.log1p(values)
            values = (values - p.center) / p.scale
        out[output] = values
    out = out[[ROW_ID, *fitted.output_columns]]
    out[target] = frame[target].to_numpy()
    return out
