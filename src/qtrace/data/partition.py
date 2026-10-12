"""Deterministic, seeded, stratified, group-aware five-way partitioning (F28, O23).

Procedure (runs after exact deduplication):

1. **Group key.** SHA-256 of each row's float64 values of every feature except
   ``Time`` (``V1``-``V28`` + ``Amount``; -0.0 normalized to 0.0). Rows that
   differ only in ``Time`` share a key; every other row is a singleton group.
2. **Stratum.** A group is in the fraud stratum if it contains any fraud row.
3. **Order.** Within each stratum, groups are sorted by key (content-defined,
   so input order is irrelevant), then permuted with a generator from the
   ``split`` seed stream only (key: dataset id, ``"group_partition"``, stratum).
4. **Assignment.** Target row counts per partition come from a largest-remainder
   allocation of the stratum's rows. Walking the permuted groups, each whole
   group goes to the partition whose cumulative target interval contains the
   group's midpoint. With only singletons this is exact; otherwise each
   partition deviates from its target by at most the largest group size.
"""

from __future__ import annotations

import math

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from qtrace.config.schemas import PARTITION_NAMES, DatasetConfig
from qtrace.data.duplicates import row_hashes, row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.utils.seeds import make_rng

PARTITION = "partition"
GROUP_KEY = "group_sha256"


class PartitionStats(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    partition: str
    target_fraction: float
    rows: int
    fraud: int
    legit: int
    prevalence: float
    fraction_of_final: float
    groups: int
    row_ids_sha256: str


class StratumAllocation(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    stratum: int
    rows: int
    groups: int
    max_group_size: int
    target: dict[str, int]
    observed: dict[str, int]
    max_abs_deviation: int

    @property
    def within_bound(self) -> bool:
        return self.max_abs_deviation <= self.max_group_size


def allocate_counts(n: int, fractions: dict[str, float]) -> dict[str, int]:
    """Largest-remainder allocation of ``n`` items; ties broken by partition order."""
    raw = {name: n * fractions[name] for name in PARTITION_NAMES}
    counts = {name: math.floor(value) for name, value in raw.items()}
    leftover = n - sum(counts.values())
    order = sorted(
        PARTITION_NAMES, key=lambda name: (-(raw[name] - counts[name]), PARTITION_NAMES.index(name))
    )
    for name in order[:leftover]:
        counts[name] += 1
    return counts


def group_key_columns(config: DatasetConfig) -> list[str]:
    return [c for c in config.feature_columns if c != "Time"]


def _groups(frame: pd.DataFrame, config: DatasetConfig) -> tuple[pd.DataFrame, pd.DataFrame]:
    work = pd.DataFrame(
        {
            ROW_ID: frame[ROW_ID].to_numpy(dtype=np.int64),
            GROUP_KEY: row_hashes(frame, group_key_columns(config)),
            "label": frame[config.target_column].to_numpy(),
        }
    )
    groups = (
        work.groupby(GROUP_KEY, sort=True)
        .agg(size=(ROW_ID, "size"), stratum=("label", "max"), n_labels=("label", "nunique"))
        .reset_index()
    )
    return work, groups


def assign_partitions(frame: pd.DataFrame, config: DatasetConfig, split_seed: int) -> pd.DataFrame:
    """Return ``[row_id, partition, group_sha256]`` for every deduplicated row."""
    work, groups = _groups(frame, config)
    fractions = config.partitions.fractions
    names = np.array(PARTITION_NAMES)
    pieces = []
    for stratum in sorted(int(s) for s in groups["stratum"].unique()):
        g = groups[groups["stratum"] == stratum].sort_values(GROUP_KEY).reset_index(drop=True)
        rng = make_rng(split_seed, "split", config.dataset_id, "group_partition", stratum)
        g = g.iloc[rng.permutation(len(g))].reset_index(drop=True)
        sizes = g["size"].to_numpy(dtype=np.int64)
        targets = allocate_counts(int(sizes.sum()), fractions)
        bounds = np.cumsum([targets[name] for name in PARTITION_NAMES])
        midpoints = np.cumsum(sizes) - sizes / 2.0
        g[PARTITION] = names[np.searchsorted(bounds, midpoints, side="right")]
        pieces.append(g[[GROUP_KEY, PARTITION]])
    mapping = pd.concat(pieces, ignore_index=True)
    out = work[[ROW_ID, GROUP_KEY]].merge(mapping, on=GROUP_KEY, how="left", validate="m:1")
    return (
        out[[ROW_ID, PARTITION, GROUP_KEY]]
        .sort_values(ROW_ID, kind="stable")
        .reset_index(drop=True)
    )


def partition_ids(assignment: pd.DataFrame, name: str) -> np.ndarray:
    return assignment.loc[assignment[PARTITION] == name, ROW_ID].to_numpy(dtype=np.int64)


def stratum_allocations(
    frame: pd.DataFrame, assignment: pd.DataFrame, config: DatasetConfig
) -> list[StratumAllocation]:
    """Target vs observed rows per stratum and partition (the O23 stratification check)."""
    work, groups = _groups(frame, config)
    stratum_of = groups.set_index(GROUP_KEY)["stratum"]
    rows = assignment.assign(stratum=stratum_of.loc[assignment[GROUP_KEY]].to_numpy())
    out = []
    for stratum in sorted(int(s) for s in groups["stratum"].unique()):
        g = groups[groups["stratum"] == stratum]
        r = rows[rows["stratum"] == stratum]
        target = allocate_counts(int(g["size"].sum()), config.partitions.fractions)
        observed = {name: int((r[PARTITION] == name).sum()) for name in PARTITION_NAMES}
        out.append(
            StratumAllocation(
                stratum=stratum,
                rows=int(g["size"].sum()),
                groups=len(g),
                max_group_size=int(g["size"].max()),
                target=target,
                observed=observed,
                max_abs_deviation=max(abs(observed[n] - target[n]) for n in PARTITION_NAMES),
            )
        )
    return out


def grouping_summary(frame: pd.DataFrame, config: DatasetConfig) -> dict[str, int | list[str]]:
    _, groups = _groups(frame, config)
    multi = groups[groups["size"] > 1]
    return {
        "group_key_columns": group_key_columns(config),
        "groups": len(groups),
        "singleton_groups": int((groups["size"] == 1).sum()),
        "multi_row_groups": len(multi),
        "rows_in_multi_row_groups": int(multi["size"].sum()),
        "max_group_size": int(groups["size"].max()),
        "mixed_label_groups": int((groups["n_labels"] > 1).sum()),
    }


def summarize_partitions(
    frame: pd.DataFrame, assignment: pd.DataFrame, config: DatasetConfig
) -> list[PartitionStats]:
    labels = frame.set_index(ROW_ID)[config.target_column]
    total = len(frame)
    stats = []
    for name in PARTITION_NAMES:
        ids = partition_ids(assignment, name)
        fraud = int(labels.loc[ids].sum())
        stats.append(
            PartitionStats(
                partition=name,
                target_fraction=config.partitions.fractions[name],
                rows=len(ids),
                fraud=fraud,
                legit=len(ids) - fraud,
                prevalence=fraud / len(ids) if len(ids) else float("nan"),
                fraction_of_final=len(ids) / total,
                groups=int(assignment.loc[assignment[PARTITION] == name, GROUP_KEY].nunique()),
                row_ids_sha256=row_ids_sha256(ids),
            )
        )
    return stats
