"""Checksum, schema validation, duplicate audit and deduplication (synthetic data only)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtrace.data import DataValidationError, audit_duplicates, deduplicate, load_raw
from qtrace.data.duplicates import FEATURE_HASH, row_hashes, row_ids_sha256
from qtrace.data.ingest import validate_schema, verify_checksum
from synthetic_ulb import EXPECTED, make_synthetic_ulb, write_synthetic


@pytest.fixture(scope="module")
def synthetic(tmp_path_factory):
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"))
    raw, schema, sha = load_raw(path, config)
    return path, config, raw, schema, sha


def test_load_adds_row_id_and_reports_schema(synthetic):
    _, _, raw, schema, _ = synthetic
    assert raw["row_id"].tolist() == list(range(EXPECTED["rows"]))
    assert schema.rows == EXPECTED["rows"] and schema.fraud == EXPECTED["fraud"]
    assert schema.legit == schema.rows - schema.fraud
    assert schema.prevalence == pytest.approx(EXPECTED["fraud"] / EXPECTED["rows"])


def test_checksum_mismatch_rejected(synthetic):
    path, config, *_ = synthetic
    with pytest.raises(DataValidationError, match="checksum mismatch"):
        verify_checksum(path, "0" * 64)
    with pytest.raises(DataValidationError, match="no expected_sha256"):
        verify_checksum(path, None)
    bad = config.model_copy(update={"expected_sha256": "f" * 64})
    with pytest.raises(DataValidationError):
        load_raw(path, bad)


@pytest.mark.parametrize(
    "mutate, message",
    [
        (lambda f: f.drop(columns=["V7"]), "columns"),
        (lambda f: f.assign(extra=1.0), "columns"),
        (lambda f: f[["Class", *[c for c in f.columns if c != "Class"]]], "columns"),
        (lambda f: f.assign(V3=f["V3"].where(f.index != 4, np.nan)), "NaN"),
        (lambda f: f.assign(Class=f["Class"].where(f.index != 4, 2)), "target"),
        (lambda f: f.assign(Amount=f["Amount"].where(f.index != 4, -1.0)), "negative Amount"),
        (lambda f: f.iloc[:-1], "expected"),
    ],
)
def test_schema_violations_rejected(synthetic, mutate, message):
    _, config, raw, _, _ = synthetic
    frame = mutate(raw.drop(columns=["row_id"]).copy())
    with pytest.raises(DataValidationError, match=message):
        validate_schema(frame, config)


def test_duplicate_audit_counts(synthetic):
    _, config, raw, _, _ = synthetic
    audit = audit_duplicates(raw, config)
    assert audit.exact.groups == EXPECTED["exact_groups"]
    assert audit.exact.rows_in_groups == EXPECTED["exact_rows_in_groups"]
    assert audit.exact.redundant_rows == EXPECTED["exact_redundant"]
    assert audit.exact.redundant_fraud_rows == EXPECTED["exact_redundant_fraud"]
    assert audit.exact.fraud_groups == EXPECTED["exact_fraud_groups"]
    assert audit.exact.group_size_counts == {"2": 7, "3": 1}
    assert audit.duplicate_fraud_transactions_exist
    assert audit.conflicting.groups == EXPECTED["conflicting_groups"]
    assert audit.conflicting.rows == EXPECTED["conflicting_rows"]
    assert audit.conflicting.label_compositions == {"legit=1,fraud=1": 2}
    assert audit.near_duplicates_ignoring_time.groups == EXPECTED["near_groups"]
    assert audit.near_duplicates_ignoring_time.rows == EXPECTED["near_rows"]
    assert audit.near_duplicates_ignoring_time.group_size_counts == {"2": 3, "6": 1}


def test_dedup_policy(synthetic):
    _, config, raw, _, _ = synthetic
    kept, report = deduplicate(raw, config)
    assert report.rows_after == len(kept) == EXPECTED["final_rows"]
    assert report.fraud_after == EXPECTED["final_fraud"]
    assert report.rows_removed_conflicting == EXPECTED["conflicting_rows"]
    assert report.conflicting_groups_excluded == EXPECTED["conflicting_groups"]
    assert report.rows_removed_exact_duplicates == EXPECTED["exact_redundant"]
    assert (
        report.rows_before - report.rows_removed_conflicting - report.rows_removed_exact_duplicates
        == report.rows_after
    )
    assert kept[FEATURE_HASH].is_unique
    # Conflicting groups are excluded entirely: none of their feature vectors survive.
    hashes = row_hashes(raw, list(config.feature_columns))
    labels_per_hash = pd.Series(raw["Class"].to_numpy()).groupby(hashes).nunique()
    conflicting = set(labels_per_hash[labels_per_hash > 1].index)
    assert conflicting and not conflicting & set(kept[FEATURE_HASH])
    # Canonical occurrence = lowest row_id of each exact group.
    groups = pd.DataFrame({"h": hashes, "row_id": raw["row_id"]})
    lowest = groups[~groups["h"].isin(conflicting)].groupby("h")["row_id"].min()
    assert set(kept["row_id"]) == set(lowest)


def test_dedup_deterministic(synthetic):
    _, config, raw, _, _ = synthetic
    a, report_a = deduplicate(raw, config)
    b, report_b = deduplicate(
        raw.sample(frac=1.0, random_state=3), config
    )  # input order irrelevant
    assert report_a == report_b
    assert a["row_id"].tolist() == b["row_id"].tolist()


def test_negative_zero_treated_as_zero():
    frame = pd.DataFrame({"a": [0.0, -0.0, 1.0]})
    hashes = row_hashes(frame, ["a"])
    assert hashes[0] == hashes[1] != hashes[2]


def test_row_ids_hash_order_independent():
    assert row_ids_sha256([3, 1, 2]) == row_ids_sha256(np.array([1, 2, 3]))
    assert row_ids_sha256([1, 2]) != row_ids_sha256([1, 3])


def test_synthetic_generator_is_deterministic():
    pd.testing.assert_frame_equal(make_synthetic_ulb(0), make_synthetic_ulb(0))
