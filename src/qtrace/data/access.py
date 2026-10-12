"""Phase-scoped access to the prepared partitions.

Later phases must load data through :func:`load_partitions`, which refuses any
partition outside the phase's allow-list *before* reading, and filters at read
time so disallowed rows never enter memory. Phase 2 (classical baselines) may
touch only the VQC partitions; the controller partitions stay untouched until
the Q-TRACE phases.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

import pandas as pd

from qtrace.data.partition import PARTITION

PHASE_ALLOWED_PARTITIONS: dict[str, tuple[str, ...]] = {
    "phase2": ("vqc_train", "vqc_val"),
    "phase3a": ("vqc_train", "vqc_val"),
    "phase3ar_select": ("vqc_train",),  # candidate selection: training CV only
    "phase3ar_eval": ("vqc_train", "vqc_val"),  # one-time evaluation of the frozen selection
    "phase3b": ("vqc_val",),  # controlled-noise characterization of frozen models
    "phase4": ("vqc_val",),  # mitigation characterization of the frozen P3A-R model
    "phase5a": ("vqc_train", "vqc_val"),  # independent VQC pool: fit on train, qualify on val
    # Phase 5B counterfactuals: each model reads ONLY its structure's partition (A04)
    "phase5b": ("ctrl_train", "ctrl_val", "ctrl_test"),
    "phase5c": ("ctrl_train", "ctrl_val", "ctrl_test"),
}
FEATURES_FILE = "features_preprocessed.parquet"
PARTITIONS_FILE = "partitions.parquet"


class PartitionAccessError(PermissionError):
    """A phase requested a partition it is not allowed to read."""


def check_access(phase: str, partitions: Iterable[str]) -> tuple[str, ...]:
    if phase not in PHASE_ALLOWED_PARTITIONS:
        raise PartitionAccessError(f"no partition allow-list defined for phase {phase!r}")
    requested = tuple(partitions)
    illegal = sorted(set(requested) - set(PHASE_ALLOWED_PARTITIONS[phase]))
    if illegal or not requested:
        raise PartitionAccessError(f"{phase} may not read partitions {illegal or requested}")
    return requested


def load_partitions(
    processed_dir: str | Path, phase: str, partitions: Iterable[str]
) -> pd.DataFrame:
    """Read only the requested, allowed partitions of the preprocessed features."""
    requested = check_access(phase, partitions)
    frame = pd.read_parquet(
        Path(processed_dir) / FEATURES_FILE, filters=[(PARTITION, "in", list(requested))]
    )
    seen = set(frame[PARTITION].unique())
    if not seen <= set(requested):  # defensive: the read filter must have held
        raise PartitionAccessError(f"read returned unexpected partitions {sorted(seen)}")
    return frame.reset_index(drop=True)


def load_partition_table(
    processed_dir: str | Path, phase: str, partitions: Iterable[str]
) -> pd.DataFrame:
    """Read ``[row_id, partition, group_sha256, label]`` for allowed partitions only."""
    requested = check_access(phase, partitions)
    frame = pd.read_parquet(
        Path(processed_dir) / PARTITIONS_FILE, filters=[(PARTITION, "in", list(requested))]
    )
    if not set(frame[PARTITION].unique()) <= set(requested):
        raise PartitionAccessError("read returned unexpected partitions")
    return frame.reset_index(drop=True)
