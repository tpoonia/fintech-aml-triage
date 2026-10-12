"""Load the raw ULB file: checksum verification and schema validation."""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from qtrace.config.schemas import DatasetConfig
from qtrace.utils.hashing import file_sha256

ROW_ID = "row_id"  # 0-based position of the record in the checksum-verified raw file


class DataValidationError(ValueError):
    """The raw data does not match the recorded checksum or expected schema."""


class SchemaReport(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    rows: int
    columns: tuple[str, ...]
    fraud: int
    legit: int
    prevalence: float
    time_min: float
    time_max: float
    time_non_decreasing: bool
    amount_min: float
    amount_max: float
    amount_zero_rows: int


def verify_checksum(path: str | Path, expected_sha256: str | None) -> str:
    """Return the file's SHA-256, raising unless it matches the recorded value."""
    if expected_sha256 is None:
        raise DataValidationError("no expected_sha256 recorded for this dataset")
    actual = file_sha256(path)
    if actual != expected_sha256:
        raise DataValidationError(f"checksum mismatch for {path}: {actual} != {expected_sha256}")
    return actual


def validate_schema(frame: pd.DataFrame, config: DatasetConfig) -> SchemaReport:
    expected = (*config.feature_columns, config.target_column)
    if tuple(frame.columns) != expected:
        raise DataValidationError(f"columns {tuple(frame.columns)} != expected {expected}")
    features = frame[list(config.feature_columns)]
    if not all(pd.api.types.is_float_dtype(t) for t in features.dtypes):
        raise DataValidationError("all feature columns must be floating point")
    values = features.to_numpy(dtype=np.float64)
    if not np.isfinite(values).all():
        raise DataValidationError("feature columns contain NaN or infinite values")
    target = frame[config.target_column]
    if not pd.api.types.is_integer_dtype(target.dtype) or not set(target.unique()) <= {0, 1}:
        raise DataValidationError("target must be integer-valued in {0, 1}")
    if (frame["Amount"] < 0).any():
        raise DataValidationError("negative Amount values: log1p preprocessing would be invalid")
    if (frame["Time"] < 0).any():
        raise DataValidationError("negative Time values")
    rows, fraud = len(frame), int(target.sum())
    if rows != config.expected_rows or fraud != config.expected_frauds:
        raise DataValidationError(
            f"expected {config.expected_rows} rows / {config.expected_frauds} frauds, "
            f"found {rows} / {fraud}"
        )
    return SchemaReport(
        rows=rows,
        columns=expected,
        fraud=fraud,
        legit=rows - fraud,
        prevalence=fraud / rows,
        time_min=float(frame["Time"].min()),
        time_max=float(frame["Time"].max()),
        time_non_decreasing=bool(frame["Time"].is_monotonic_increasing),
        amount_min=float(frame["Amount"].min()),
        amount_max=float(frame["Amount"].max()),
        amount_zero_rows=int((frame["Amount"] == 0).sum()),
    )


def load_raw(path: str | Path, config: DatasetConfig) -> tuple[pd.DataFrame, SchemaReport, str]:
    """Verify, parse and validate the raw CSV; add the stable ``row_id`` column."""
    sha256 = verify_checksum(path, config.expected_sha256)
    # round_trip parsing gives exact, platform-independent float values.
    frame = pd.read_csv(path, float_precision="round_trip")
    report = validate_schema(frame, config)
    frame.insert(0, ROW_ID, np.arange(len(frame), dtype=np.int64))
    return frame, report, sha256
