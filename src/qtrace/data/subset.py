"""Configurable VQC-training-subset utility (size and class ratio not frozen: O04, O17).

The subset is drawn **only** from the ``vqc_train`` partition with seeds from the
``undersample`` stream, and the selected row ids are recorded with a hash.
"""

from __future__ import annotations

from typing import Literal

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import PARTITION, partition_ids
from qtrace.utils.seeds import derive_seed, make_rng


class SubsetError(ValueError):
    pass


class SubsetSpec(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    subset_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_\-]*$")
    source_partition: Literal["vqc_train"] = "vqc_train"  # never controller or test rows
    include_all_fraud: bool = True
    n_fraud: int | None = Field(None, ge=1)
    legit_per_fraud: float | None = Field(None, gt=0)
    n_legit: int | None = Field(None, ge=0)
    max_samples: int | None = Field(None, ge=1)

    @model_validator(mode="after")
    def _check(self) -> SubsetSpec:
        if self.include_all_fraud == (self.n_fraud is not None):
            raise ValueError("set exactly one of include_all_fraud=true or n_fraud")
        if (self.legit_per_fraud is None) == (self.n_legit is None):
            raise ValueError("set exactly one of legit_per_fraud or n_legit")
        return self


class SubsetRecord(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    spec: SubsetSpec
    dataset_id: str
    undersample_master_seed: int
    derived_seed: int
    source_partition_rows: int
    n_fraud: int
    n_legit: int
    row_ids: tuple[int, ...]
    row_ids_sha256: str


def build_vqc_training_subset(
    frame: pd.DataFrame,
    assignment: pd.DataFrame,
    spec: SubsetSpec,
    *,
    target: str,
    dataset_id: str,
    undersample_seed: int,
) -> SubsetRecord:
    source_ids = partition_ids(assignment, spec.source_partition)
    source = frame.loc[frame[ROW_ID].isin(source_ids), [ROW_ID, target]].sort_values(ROW_ID)
    fraud_ids = source.loc[source[target] == 1, ROW_ID].to_numpy(dtype=np.int64)
    legit_ids = source.loc[source[target] == 0, ROW_ID].to_numpy(dtype=np.int64)

    if spec.include_all_fraud:
        chosen_fraud = fraud_ids
    else:
        if spec.n_fraud > len(fraud_ids):
            raise SubsetError(f"requested {spec.n_fraud} frauds, only {len(fraud_ids)} available")
        rng = make_rng(undersample_seed, "undersample", dataset_id, spec.subset_id, "fraud")
        chosen_fraud = np.sort(rng.choice(fraud_ids, size=spec.n_fraud, replace=False))

    if spec.n_legit is not None:
        n_legit = spec.n_legit
    else:
        n_legit = int(round(spec.legit_per_fraud * len(chosen_fraud)))
    if n_legit > len(legit_ids):
        raise SubsetError(f"requested {n_legit} legitimate rows, only {len(legit_ids)} available")
    total = len(chosen_fraud) + n_legit
    if spec.max_samples is not None and total > spec.max_samples:
        raise SubsetError(f"subset of {total} rows exceeds max_samples={spec.max_samples}")
    rng = make_rng(undersample_seed, "undersample", dataset_id, spec.subset_id, "legit")
    chosen_legit = np.sort(rng.choice(legit_ids, size=n_legit, replace=False))

    row_ids = np.sort(np.concatenate([chosen_fraud, chosen_legit]))
    assigned = assignment.set_index(ROW_ID).loc[row_ids, PARTITION]
    if not (assigned == spec.source_partition).all():  # defensive: must never trigger
        raise SubsetError("subset contains rows outside the source partition")
    return SubsetRecord(
        spec=spec,
        dataset_id=dataset_id,
        undersample_master_seed=undersample_seed,
        derived_seed=derive_seed(undersample_seed, "undersample", dataset_id, spec.subset_id),
        source_partition_rows=len(source),
        n_fraud=len(chosen_fraud),
        n_legit=n_legit,
        row_ids=tuple(int(i) for i in row_ids),
        row_ids_sha256=row_ids_sha256(row_ids),
    )
