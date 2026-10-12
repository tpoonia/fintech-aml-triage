"""Synthetic ULB-shaped data with a known duplicate structure (never real transactions).

Base: 1,900 legitimate + 100 fraud rows. Injected, each from a distinct base row:
  * 5 legit rows copied once            -> 5 exact groups of size 2
  * 1 legit row copied twice            -> 1 exact group of size 3
  * 2 fraud rows copied once            -> 2 exact fraud groups of size 2
  * 2 legit rows copied with label 1    -> 2 conflicting groups (1 legit + 1 fraud)
  * 3 legit rows copied with Time + 10  -> 3 near-duplicate groups (not duplicates)
  * 1 legit row copied 5x, Time shifted -> 1 near-duplicate group of size 6
Totals: 2,019 rows, 104 frauds. After the policy: 2,006 rows, 100 frauds.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np
import pandas as pd

from qtrace.config import load_component
from qtrace.config.schemas import DatasetConfig
from qtrace.utils.hashing import file_sha256

N_LEGIT, N_FRAUD = 1900, 100
EXPECTED = {
    "rows": 2019,
    "fraud": 104,
    "exact_groups": 8,
    "exact_rows_in_groups": 17,
    "exact_redundant": 9,
    "exact_redundant_fraud": 2,
    "exact_fraud_groups": 2,
    "conflicting_groups": 2,
    "conflicting_rows": 4,
    "near_groups": 4,
    "near_rows": 12,
    "max_group_size": 6,
    "final_rows": 2006,
    "final_fraud": 100,
}


def make_synthetic_ulb(seed: int = 0) -> pd.DataFrame:
    rng = np.random.default_rng(seed)
    n = N_LEGIT + N_FRAUD
    frame = pd.DataFrame({"Time": np.sort(rng.integers(0, 172_800, n)).astype(float)})
    for i in range(1, 29):
        frame[f"V{i}"] = rng.normal(size=n)
    frame["Amount"] = np.round(rng.lognormal(3.0, 1.2, n), 2)
    labels = np.zeros(n, dtype=np.int64)
    labels[rng.choice(n, N_FRAUD, replace=False)] = 1
    frame["Class"] = labels

    legit = frame.index[frame["Class"] == 0].to_numpy()
    fraud = frame.index[frame["Class"] == 1].to_numpy()
    extra = [
        frame.loc[legit[0:5]],  # exact legit pairs
        frame.loc[[legit[5]]],
        frame.loc[[legit[5]]],  # exact legit triple
        frame.loc[fraud[0:2]],  # exact fraud pairs
        frame.loc[legit[6:8]].assign(Class=1),  # conflicting labels
        frame.loc[legit[8:11]].assign(Time=lambda d: d["Time"] + 10.0),  # near duplicates
        *(
            frame.loc[[legit[11]]].assign(Time=lambda d, k=k: d["Time"] + 1000.0 * k)
            for k in range(1, 6)
        ),  # one near-duplicate group of size 6
    ]
    return pd.concat([frame, *extra], ignore_index=True)


def write_synthetic(
    tmp_path: Path, frame: pd.DataFrame | None = None
) -> tuple[Path, DatasetConfig]:
    frame = make_synthetic_ulb() if frame is None else frame
    path = tmp_path / "synthetic_creditcard.csv"
    frame.to_csv(path, index=False)
    base = load_component("dataset", "ulb_v1")
    config = DatasetConfig.model_validate(
        {
            **base.model_dump(),
            "dataset_id": "synthetic",
            "raw_path": str(path),
            "expected_sha256": file_sha256(path),
            "expected_rows": len(frame),
            "expected_frauds": int(frame["Class"].sum()),
            "provenance": None,
        }
    )
    return path, config
