"""Partitioning, preprocessing, seed isolation and the end-to-end pipeline (synthetic data)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from sklearn.preprocessing import RobustScaler

from qtrace.config import load_experiment
from qtrace.config.schemas import PARTITION_NAMES
from qtrace.data import (
    allocate_counts,
    assign_partitions,
    fit_preprocessor,
    prepare_dataset,
    transform,
)
from qtrace.data.duplicates import FEATURE_HASH
from qtrace.data.partition import PARTITION, partition_ids
from qtrace.data.pipeline import committed_metadata, summary_table
from qtrace.data.preprocess import PreprocessingError
from synthetic_ulb import EXPECTED, make_synthetic_ulb, write_synthetic

SEEDS = load_experiment("prepare_ulb_v1").spec.seeds
FRACTIONS = {
    "vqc_train": 0.45,
    "vqc_val": 0.10,
    "ctrl_train": 0.15,
    "ctrl_val": 0.10,
    "ctrl_test": 0.20,
}


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"))
    return prepare_dataset(path, config, SEEDS)


# ------------------------------------------------------------------ allocation / split


def test_allocate_counts_largest_remainder():
    assert allocate_counts(473, FRACTIONS) == {
        "vqc_train": 213,
        "vqc_val": 47,
        "ctrl_train": 71,
        "ctrl_val": 47,
        "ctrl_test": 95,
    }
    for n in (0, 1, 7, 100, 1901, 283_253):
        assert sum(allocate_counts(n, FRACTIONS).values()) == n


def test_all_sanity_checks_pass(prepared):
    assert prepared.passed, prepared.checks


def test_partitions_disjoint_exhaustive_and_stratified(prepared):
    ids = {n: set(partition_ids(prepared.assignment, n)) for n in PARTITION_NAMES}
    union = set().union(*ids.values())
    assert sum(len(s) for s in ids.values()) == len(union) == EXPECTED["final_rows"]
    assert union == set(prepared.frame["row_id"])
    stats = {p.partition: p for p in prepared.partitions}
    # Fraud rows are all singleton groups here, so fraud allocation is exact.
    fraud_allocation = allocate_counts(EXPECTED["final_fraud"], FRACTIONS)
    assert {n: stats[n].fraud for n in PARTITION_NAMES} == fraud_allocation
    # Legitimate rows contain multi-row groups: deviation bounded by the largest group.
    legit_allocation = allocate_counts(EXPECTED["final_rows"] - EXPECTED["final_fraud"], FRACTIONS)
    for name in PARTITION_NAMES:
        assert abs(stats[name].legit - legit_allocation[name]) <= EXPECTED["max_group_size"]


def test_dedup_happens_before_split(prepared, tmp_path):
    raw = make_synthetic_ulb()
    removed = set(raw.index) - set(prepared.frame["row_id"])
    assert len(removed) == EXPECTED["rows"] - EXPECTED["final_rows"]
    assert not removed & set(prepared.assignment["row_id"])
    by_hash = prepared.frame[["row_id", FEATURE_HASH]].merge(prepared.assignment, on="row_id")
    assert (by_hash.groupby(FEATURE_HASH)[PARTITION].nunique() == 1).all()


def test_split_is_deterministic(tmp_path):
    path, config = write_synthetic(tmp_path)
    a = prepare_dataset(path, config, SEEDS)
    b = prepare_dataset(path, config, SEEDS)
    pd.testing.assert_frame_equal(a.assignment, b.assignment)
    assert committed_metadata(a) == committed_metadata(b)
    pd.testing.assert_frame_equal(summary_table(a), summary_table(b))


@pytest.mark.parametrize(
    "stream", ["model", "undersample", "noise", "shots", "policy", "bootstrap"]
)
def test_unrelated_seed_streams_do_not_change_outputs(tmp_path, prepared, stream):
    path, config = write_synthetic(tmp_path)
    changed = SEEDS.model_copy(update={stream: getattr(SEEDS, stream) + 1})
    other = prepare_dataset(path, config, changed)
    pd.testing.assert_frame_equal(other.assignment, prepared.assignment)
    assert other.fitted.artifact_sha256() == prepared.fitted.artifact_sha256()


def test_split_seed_changes_assignment(tmp_path, prepared):
    path, config = write_synthetic(tmp_path)
    other = prepare_dataset(path, config, SEEDS.model_copy(update={"split": SEEDS.split + 1}))
    assert not other.assignment.equals(prepared.assignment)
    assert other.passed  # still a valid split


def test_split_independent_of_row_order(prepared):
    shuffled = prepared.frame.sample(frac=1.0, random_state=11)
    again = assign_partitions(shuffled, prepared.config, SEEDS.split)
    pd.testing.assert_frame_equal(again, prepared.assignment)


# ---------------------------------------------------------------------- preprocessing


def _with_partition_values(prepared, partitions, **values):
    ids = np.concatenate([partition_ids(prepared.assignment, p) for p in partitions])
    frame = prepared.frame.copy()
    for column, value in values.items():
        frame.loc[frame["row_id"].isin(ids), column] = value
    return frame


def test_changing_non_training_partitions_cannot_alter_fit(prepared):
    others = [p for p in PARTITION_NAMES if p != "vqc_train"]
    frame = _with_partition_values(prepared, others, Time=1e9, Amount=1e9)
    refit = fit_preprocessor(frame, prepared.assignment, prepared.config, prepared.dataset_sha256)
    assert refit == prepared.fitted
    assert refit.artifact_sha256() == prepared.fitted.artifact_sha256()


def test_changing_training_partition_alters_fit(prepared):
    frame = prepared.frame.copy()
    train = frame["row_id"].isin(partition_ids(prepared.assignment, "vqc_train"))
    frame.loc[train, "Amount"] = frame.loc[train, "Amount"] * 2.0
    refit = fit_preprocessor(frame, prepared.assignment, prepared.config, prepared.dataset_sha256)
    assert refit.artifact_sha256() != prepared.fitted.artifact_sha256()


def test_fit_records_training_partition(prepared):
    train_ids = partition_ids(prepared.assignment, "vqc_train")
    assert prepared.fitted.fit_partition == "vqc_train"
    assert prepared.fitted.fit_partition_rows == len(train_ids)


def test_transform_matches_sklearn_robust_scaler(prepared):
    train = prepared.frame[
        prepared.frame["row_id"].isin(partition_ids(prepared.assignment, "vqc_train"))
    ]
    reference = RobustScaler().fit(np.column_stack([train["Time"], np.log1p(train["Amount"])]))
    expected = reference.transform(
        np.column_stack([prepared.frame["Time"], np.log1p(prepared.frame["Amount"])])
    )
    out = transform(prepared.frame, prepared.fitted, "Class")
    np.testing.assert_allclose(out[["time_robust", "amount_log1p_robust"]].to_numpy(), expected)
    np.testing.assert_array_equal(out["V1"].to_numpy(), prepared.frame["V1"].to_numpy())


def test_transform_is_row_local(prepared):
    full = transform(prepared.frame, prepared.fitted, "Class").set_index("row_id")
    part = transform(prepared.frame.iloc[:50], prepared.fitted, "Class").set_index("row_id")
    pd.testing.assert_frame_equal(part, full.loc[part.index])


def test_degenerate_or_invalid_inputs_rejected(prepared):
    frame = _with_partition_values(prepared, ["vqc_train"], Time=7.0)
    with pytest.raises(PreprocessingError, match="interquantile"):
        fit_preprocessor(frame, prepared.assignment, prepared.config, prepared.dataset_sha256)
    frame = _with_partition_values(prepared, ["vqc_train"], Amount=-2.0)
    with pytest.raises(PreprocessingError, match="log1p"):
        fit_preprocessor(frame, prepared.assignment, prepared.config, prepared.dataset_sha256)


# --------------------------------------------------------------------------- outputs

FORBIDDEN_COLUMNS = {"row_id", "Time", "Amount", "Class", *(f"V{i}" for i in range(1, 29))}


def _longest_list(obj) -> int:
    if isinstance(obj, dict):
        return max((_longest_list(v) for v in obj.values()), default=0)
    if isinstance(obj, list):
        return max([len(obj), *(_longest_list(v) for v in obj)])
    return 0


def test_summary_and_metadata_are_aggregate_only(prepared):
    table = summary_table(prepared)
    assert list(table["scope"]) == [
        "original",
        "removed_conflicting_label_groups",
        "removed_exact_duplicates",
        "final",
        *PARTITION_NAMES,
    ]
    assert not FORBIDDEN_COLUMNS & set(table.columns)
    final = table.set_index("scope").loc["final"]
    assert final["rows"] == EXPECTED["final_rows"] and final["fraud"] == EXPECTED["final_fraud"]
    meta = json.loads(json.dumps(committed_metadata(prepared)))  # JSON-serializable
    # Only short lists (the 31 column names at most); never per-row data.
    assert _longest_list(meta) <= len(prepared.config.feature_columns) + 1
