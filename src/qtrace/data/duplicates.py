"""Duplicate audit and deterministic deduplication (PI policy, Phase 1).

Definitions (all on the parsed float64 values of the feature columns):

* **exact duplicates**: rows identical on every feature column *and* the label;
* **conflicting groups**: rows identical on every feature column but with
  different labels;
* **near duplicates ignoring Time**: rows identical on every feature except
  ``Time`` while their ``Time`` values differ. These are *not* duplicates under
  the policy; they are audited for information only.

Policy: conflicting groups are excluded entirely; among the remaining rows,
exact duplicates keep the occurrence with the lowest ``row_id``. Both steps
happen before any split.
"""

from __future__ import annotations

import hashlib
from collections import Counter

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from qtrace.config.schemas import DatasetConfig
from qtrace.data.ingest import ROW_ID
from qtrace.utils.hashing import sha256_hex

FEATURE_HASH = "feature_sha256"


class _Report(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


def row_hashes(frame: pd.DataFrame, columns: list[str] | tuple[str, ...]) -> np.ndarray:
    """SHA-256 of each row's float64 values (``-0.0`` normalized to ``0.0``)."""
    values = np.ascontiguousarray(frame[list(columns)].to_numpy(dtype=np.float64)) + 0.0
    return np.array([hashlib.sha256(row.tobytes()).hexdigest() for row in values], dtype=object)


def row_ids_sha256(row_ids: np.ndarray | pd.Series | list[int]) -> str:
    """Order-independent fingerprint of a set of row ids."""
    ids = np.sort(np.asarray(row_ids, dtype=np.int64)).astype("<i8")
    return sha256_hex(ids.tobytes())


def _size_counts(sizes: pd.Series) -> dict[str, int]:
    return {str(k): int(v) for k, v in sorted(Counter(sizes.tolist()).items())}


class ExactDuplicateStats(_Report):
    groups: int
    rows_in_groups: int
    redundant_rows: int
    fraud_groups: int
    legit_groups: int
    fraud_rows_in_groups: int
    legit_rows_in_groups: int
    redundant_fraud_rows: int
    redundant_legit_rows: int
    group_size_counts: dict[str, int]


class ConflictStats(_Report):
    groups: int
    rows: int
    fraud_rows: int
    legit_rows: int
    group_size_counts: dict[str, int]
    label_compositions: dict[str, int]  # "legit=a,fraud=b" -> number of groups


class NearDuplicateStats(_Report):
    groups: int
    rows: int
    fraud_rows: int
    groups_with_conflicting_labels: int
    group_size_counts: dict[str, int]


class DuplicateAudit(_Report):
    total_rows: int
    total_fraud: int
    duplicate_key: tuple[str, ...]
    exact: ExactDuplicateStats
    duplicate_fraud_transactions_exist: bool
    conflicting: ConflictStats
    near_duplicates_ignoring_time: NearDuplicateStats


class DedupReport(_Report):
    policy: dict[str, str | bool]
    rows_before: int
    fraud_before: int
    conflicting_groups_excluded: int
    rows_removed_conflicting: int
    fraud_removed_conflicting: int
    legit_removed_conflicting: int
    rows_removed_exact_duplicates: int
    fraud_removed_exact_duplicates: int
    legit_removed_exact_duplicates: int
    rows_after: int
    fraud_after: int
    legit_after: int
    prevalence_after: float
    removed_row_ids_sha256: str


def audit_duplicates(frame: pd.DataFrame, config: DatasetConfig) -> DuplicateAudit:
    target = config.target_column
    features = list(config.feature_columns)
    work = pd.DataFrame(
        {
            ROW_ID: frame[ROW_ID].to_numpy(),
            "label": frame[target].to_numpy(),
            "fh": row_hashes(frame, features),
            "nh": row_hashes(frame, [c for c in features if c != "Time"]),
            "time": frame["Time"].to_numpy(),
        }
    )

    # Exact duplicates: same features and same label.
    exact_sizes = work.groupby(["fh", "label"])[ROW_ID].transform("size")
    in_exact = work[exact_sizes > 1]
    exact_groups = in_exact.groupby(["fh", "label"]).size()
    redundant = in_exact[in_exact.duplicated(subset=["fh", "label"], keep="first")]
    exact = ExactDuplicateStats(
        groups=len(exact_groups),
        rows_in_groups=len(in_exact),
        redundant_rows=len(redundant),
        fraud_groups=int((exact_groups.index.get_level_values("label") == 1).sum()),
        legit_groups=int((exact_groups.index.get_level_values("label") == 0).sum()),
        fraud_rows_in_groups=int((in_exact["label"] == 1).sum()),
        legit_rows_in_groups=int((in_exact["label"] == 0).sum()),
        redundant_fraud_rows=int((redundant["label"] == 1).sum()),
        redundant_legit_rows=int((redundant["label"] == 0).sum()),
        group_size_counts=_size_counts(exact_groups),
    )

    # Conflicting groups: same features, more than one label.
    n_labels = work.groupby("fh")["label"].transform("nunique")
    conflict = work[n_labels > 1]
    compositions = conflict.groupby("fh")["label"].agg(
        lambda s: f"legit={int((s == 0).sum())},fraud={int((s == 1).sum())}"
    )
    conflicting = ConflictStats(
        groups=int(conflict["fh"].nunique()),
        rows=len(conflict),
        fraud_rows=int((conflict["label"] == 1).sum()),
        legit_rows=int((conflict["label"] == 0).sum()),
        group_size_counts=_size_counts(conflict.groupby("fh").size()),
        label_compositions={k: int(v) for k, v in sorted(Counter(compositions).items())},
    )

    # Near duplicates: identical except Time, with differing Time values.
    distinct_times = work.groupby("nh")["time"].transform("nunique")
    near = work[distinct_times > 1]
    near_labels = near.groupby("nh")["label"].nunique()
    near_dups = NearDuplicateStats(
        groups=int(near["nh"].nunique()),
        rows=len(near),
        fraud_rows=int((near["label"] == 1).sum()),
        groups_with_conflicting_labels=int((near_labels > 1).sum()),
        group_size_counts=_size_counts(near.groupby("nh").size()),
    )

    return DuplicateAudit(
        total_rows=len(frame),
        total_fraud=int(frame[target].sum()),
        duplicate_key=tuple(features),
        exact=exact,
        duplicate_fraud_transactions_exist=exact.fraud_groups > 0,
        conflicting=conflicting,
        near_duplicates_ignoring_time=near_dups,
    )


def deduplicate(frame: pd.DataFrame, config: DatasetConfig) -> tuple[pd.DataFrame, DedupReport]:
    """Apply the PI policy. Returns the deduplicated frame (with ``feature_sha256``)."""
    policy = config.deduplication
    target = config.target_column
    hashes = row_hashes(frame, list(config.feature_columns))
    work = frame.assign(**{FEATURE_HASH: hashes}).sort_values(ROW_ID, kind="stable")

    conflicting = work.groupby(FEATURE_HASH)[target].transform("nunique") > 1
    removed_conflict = work[conflicting]
    remaining = work[~conflicting]
    redundant = remaining.duplicated(subset=[FEATURE_HASH], keep="first")  # lowest row_id kept
    removed_exact = remaining[redundant]
    kept = remaining[~redundant].reset_index(drop=True)

    removed_ids = np.concatenate([removed_conflict[ROW_ID], removed_exact[ROW_ID]])
    fraud_after = int(kept[target].sum())
    report = DedupReport(
        policy=policy.model_dump(),
        rows_before=len(frame),
        fraud_before=int(frame[target].sum()),
        conflicting_groups_excluded=int(removed_conflict[FEATURE_HASH].nunique()),
        rows_removed_conflicting=len(removed_conflict),
        fraud_removed_conflicting=int(removed_conflict[target].sum()),
        legit_removed_conflicting=int((removed_conflict[target] == 0).sum()),
        rows_removed_exact_duplicates=len(removed_exact),
        fraud_removed_exact_duplicates=int(removed_exact[target].sum()),
        legit_removed_exact_duplicates=int((removed_exact[target] == 0).sum()),
        rows_after=len(kept),
        fraud_after=fraud_after,
        legit_after=len(kept) - fraud_after,
        prevalence_after=fraud_after / len(kept),
        removed_row_ids_sha256=row_ids_sha256(removed_ids),
    )
    return kept, report
