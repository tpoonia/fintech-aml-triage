"""Deterministic, group-aware, stratified K-fold assignment inside one partition.

Same grouping and assignment rule as the five-way split (E25): groups of rows
sharing V1-V28 + Amount are never divided; a group's stratum is fraud if it
contains any fraud row; within each stratum, groups are sorted by key, permuted
with the ``split`` seed stream (key: dataset id, fold key, stratum), and each
whole group goes to the fold whose cumulative equal-size target interval
contains the group's midpoint.
"""

from __future__ import annotations

import numpy as np
import pandas as pd

from qtrace.config.schemas import DatasetConfig
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import GROUP_KEY, _groups
from qtrace.utils.seeds import make_rng

FOLD = "fold"


def equal_allocation(n: int, k: int) -> list[int]:
    base, extra = divmod(n, k)
    return [base + (1 if i < extra else 0) for i in range(k)]


def _groups_from_keys(frame: pd.DataFrame, target: str) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Groups from a precomputed Phase 1 ``group_sha256`` column (the authoritative key)."""
    work = pd.DataFrame(
        {
            ROW_ID: frame[ROW_ID].to_numpy(dtype=np.int64),
            GROUP_KEY: frame[GROUP_KEY].to_numpy(),
            "label": frame[target].to_numpy(),
        }
    )
    groups = (
        work.groupby(GROUP_KEY, sort=True)
        .agg(size=(ROW_ID, "size"), stratum=("label", "max"), n_labels=("label", "nunique"))
        .reset_index()
    )
    return work, groups


def assign_group_folds(
    frame: pd.DataFrame, config: DatasetConfig, n_folds: int, split_seed: int, fold_key: str
) -> pd.DataFrame:
    """Return ``[row_id, fold, group_sha256]`` for every row of ``frame``.

    Uses the frame's ``group_sha256`` column when present (Phase 1 keys on raw
    V1-V28 + Amount); otherwise computes the same key from raw columns.
    """
    if GROUP_KEY in frame.columns:
        work, groups = _groups_from_keys(frame, config.target_column)
    else:
        work, groups = _groups(frame, config)
    pieces = []
    for stratum in sorted(int(s) for s in groups["stratum"].unique()):
        g = groups[groups["stratum"] == stratum].sort_values(GROUP_KEY).reset_index(drop=True)
        rng = make_rng(split_seed, "split", config.dataset_id, fold_key, stratum)
        g = g.iloc[rng.permutation(len(g))].reset_index(drop=True)
        sizes = g["size"].to_numpy(dtype=np.int64)
        bounds = np.cumsum(equal_allocation(int(sizes.sum()), n_folds))
        midpoints = np.cumsum(sizes) - sizes / 2.0
        g[FOLD] = np.searchsorted(bounds, midpoints, side="right")
        pieces.append(g[[GROUP_KEY, FOLD]])
    mapping = pd.concat(pieces, ignore_index=True)
    out = work[[ROW_ID, GROUP_KEY]].merge(mapping, on=GROUP_KEY, how="left", validate="m:1")
    return out[[ROW_ID, FOLD, GROUP_KEY]].sort_values(ROW_ID, kind="stable").reset_index(drop=True)


def fold_summary(folds: pd.DataFrame, labels: pd.Series) -> list[dict]:
    """Per fold: rows, frauds, prevalence, groups, row-id hash (labels indexed by row_id)."""
    out = []
    for f in sorted(folds[FOLD].unique()):
        ids = folds.loc[folds[FOLD] == f, ROW_ID].to_numpy()
        fraud = int(labels.loc[ids].sum())
        out.append(
            {
                "fold": int(f),
                "rows": len(ids),
                "fraud": fraud,
                "legit": len(ids) - fraud,
                "prevalence": fraud / len(ids),
                "groups": int(folds.loc[folds[FOLD] == f, GROUP_KEY].nunique()),
                "row_ids_sha256": row_ids_sha256(ids),
            }
        )
    return out
