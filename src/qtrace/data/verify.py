"""Verify that loaded partitions and preprocessing match the committed Phase 1 metadata."""

from __future__ import annotations

import json
from pathlib import Path

import pandas as pd

from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.partition import PARTITION


class Phase1Mismatch(RuntimeError):
    pass


def verify_phase1(
    root: Path, dataset_id: str, frame: pd.DataFrame, fitted, partitions: tuple[str, ...]
) -> dict:
    path = root / "results" / "tables" / f"{dataset_id}_phase1_metadata.json"
    meta = json.loads(path.read_text())
    expected = {p["partition"]: p["row_ids_sha256"] for p in meta["partitions"]}
    observed = {
        name: row_ids_sha256(frame.loc[frame[PARTITION] == name, "row_id"]) for name in partitions
    }
    if any(observed[n] != expected[n] for n in observed):
        raise Phase1Mismatch(f"partition hashes differ from Phase 1 metadata: {observed}")
    if fitted.artifact_sha256() != meta["preprocessing"]["artifact_sha256"]:
        raise Phase1Mismatch("preprocessing artifact differs from Phase 1 metadata")
    return {
        "phase1_partition_row_ids_sha256": observed,
        "phase1_preprocessing_artifact_sha256": fitted.artifact_sha256(),
        "split_method": meta["split"]["method"],
        "partitions_read": list(partitions),
    }
