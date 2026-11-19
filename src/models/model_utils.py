"""Leakage controls and customer-disjoint split helpers for model training."""

import os
import numpy as np
import pandas as pd
from sklearn.model_selection import GroupShuffleSplit

SEED = int(os.environ.get("AML_SEED", "42"))
EXCLUDED_FEATURES = {
    "alert_id",
    "customer_id",
    "transaction_id",
    "alert_timestamp",
    "investigation_outcome",
    "is_suspicious",
    "target",
}


def prepare_training_data(dataset: pd.DataFrame):
    """Return features, target, and customer groups with labels removed from X."""
    required = {"target", "customer_id"}
    missing = required - set(dataset.columns)
    if missing:
        raise ValueError(f"training data missing columns: {sorted(missing)}")
    target = pd.to_numeric(dataset["target"], errors="coerce")
    if target.isna().any():
        raise ValueError("target contains missing or nonnumeric values")
    groups = dataset["customer_id"].astype(str)
    features = dataset.drop(columns=[c for c in EXCLUDED_FEATURES if c in dataset.columns]).copy()
    return features, target.astype(int), groups


def grouped_train_test_indices(groups, test_size: float = 0.2, random_state: int = SEED):
    """Split rows while keeping each customer entirely within one partition."""
    group_values = np.asarray(groups)
    splitter = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_indices, test_indices = next(
        splitter.split(np.zeros(len(group_values)), groups=group_values)
    )
    return train_indices, test_indices
