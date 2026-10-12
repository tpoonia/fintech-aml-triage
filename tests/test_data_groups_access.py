"""O23 group-aware split and phase-scoped partition access (synthetic data)."""

from __future__ import annotations

import ast
from pathlib import Path

import pandas as pd
import pytest

from qtrace.config import load_experiment
from qtrace.config.schemas import PARTITION_NAMES
from qtrace.data import assign_partitions, prepare_dataset
from qtrace.data.access import PartitionAccessError, check_access, load_partitions
from qtrace.data.duplicates import FEATURE_HASH, row_hashes
from qtrace.data.partition import GROUP_KEY, PARTITION, partition_ids
from qtrace.data.preprocess import fit_partition_hash
from synthetic_ulb import EXPECTED, write_synthetic

SEEDS = load_experiment("prepare_ulb_v1").spec.seeds
ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"))
    return prepare_dataset(path, config, SEEDS)


def test_zero_exact_row_overlap(prepared):  # 1
    ids = [set(partition_ids(prepared.assignment, n)) for n in PARTITION_NAMES]
    for i in range(len(ids)):
        for j in range(i + 1, len(ids)):
            assert not ids[i] & ids[j]


def test_zero_exact_duplicate_groups_crossing(prepared):  # 2
    rows = prepared.frame[["row_id", FEATURE_HASH]].merge(prepared.assignment, on="row_id")
    assert (rows.groupby(FEATURE_HASH)[PARTITION].nunique() == 1).all()


def test_zero_near_duplicate_groups_crossing(prepared):  # 3
    columns = [f"V{i}" for i in range(1, 29)] + ["Amount"]
    keys = row_hashes(prepared.frame, columns)  # independent recomputation of the group key
    rows = pd.DataFrame({"row_id": prepared.frame["row_id"], "k": keys}).merge(
        prepared.assignment, on="row_id"
    )
    spans = rows.groupby("k")[PARTITION].nunique()
    assert (spans == 1).all()
    multi = rows.groupby("k").size()
    assert (multi > 1).sum() == EXPECTED["near_groups"]  # the injected groups exist and are intact
    assert prepared.near_duplicate_groups_across_partitions == 0
    assert prepared.checks["zero_group_crossing_partitions"]


def test_group_assignment_reproducible_and_order_independent(prepared):  # 4
    again = assign_partitions(prepared.frame, prepared.config, SEEDS.split)
    pd.testing.assert_frame_equal(again, prepared.assignment)
    shuffled = assign_partitions(
        prepared.frame.sample(frac=1.0, random_state=5), prepared.config, SEEDS.split
    )
    pd.testing.assert_frame_equal(shuffled, prepared.assignment)


def test_stratification_reasonable(prepared):  # 5
    assert prepared.checks["stratification_within_group_size_bound"]
    by_stratum = {a.stratum: a for a in prepared.allocations}
    assert by_stratum[1].max_abs_deviation == 0  # fraud rows are singletons: exact
    assert by_stratum[0].max_group_size == EXPECTED["max_group_size"]
    overall = EXPECTED["final_fraud"] / EXPECTED["final_rows"]
    for stats in prepared.partitions:
        assert stats.fraud > 0
        assert abs(stats.prevalence - overall) / overall < 0.25


def test_preprocessing_fitted_on_corrected_vqc_train(prepared):  # 6
    train_ids = partition_ids(prepared.assignment, "vqc_train")
    assert prepared.fitted.fit_partition_rows == len(train_ids)
    assert prepared.fitted.fit_partition_hash == fit_partition_hash(
        prepared.dataset_sha256, "vqc_train", train_ids
    )
    assert prepared.checks["preprocessing_fit_on_vqc_train_only"]


def test_group_keys_recorded_in_assignment(prepared):
    assert prepared.assignment[GROUP_KEY].notna().all()
    assert prepared.grouping["multi_row_groups"] == EXPECTED["near_groups"]
    assert prepared.grouping["mixed_label_groups"] == 0


# ------------------------------------------------------ 7: controller partitions are off-limits


@pytest.mark.parametrize("partition", ["ctrl_train", "ctrl_val", "ctrl_test"])
def test_phase2_cannot_request_controller_partitions(partition):
    with pytest.raises(PartitionAccessError):
        check_access("phase2", ["vqc_train", partition])


@pytest.mark.parametrize("partition", ["vqc_train", "ctrl_train", "ctrl_val", "ctrl_test"])
def test_phase3b_reads_vqc_val_only(partition):
    assert check_access("phase3b", ["vqc_val"]) == ("vqc_val",)
    with pytest.raises(PartitionAccessError):
        check_access("phase3b", [partition])
    with pytest.raises(PartitionAccessError):
        check_access("phase3b", ["vqc_val", partition])


def test_unknown_phase_and_empty_request_refused():
    with pytest.raises(PartitionAccessError):
        check_access("phase99", ["vqc_train"])
    with pytest.raises(PartitionAccessError):
        check_access("phase2", [])


def test_load_partitions_never_returns_controller_rows(prepared, tmp_path):
    prepared.features.to_parquet(tmp_path / "features_preprocessed.parquet", index=False)
    loaded = load_partitions(tmp_path, "phase2", ["vqc_train", "vqc_val"])
    assert set(loaded[PARTITION]) == {"vqc_train", "vqc_val"}
    expected = sum(p.rows for p in prepared.partitions if p.partition in {"vqc_train", "vqc_val"})
    assert len(loaded) == expected
    with pytest.raises(PartitionAccessError):
        load_partitions(tmp_path, "phase2", ["ctrl_test"])


def _string_constants(path: Path) -> set[str]:
    return {
        node.value
        for node in ast.walk(ast.parse(path.read_text()))
        if isinstance(node, ast.Constant) and isinstance(node.value, str)
    }


def test_phase2_to_5a_code_never_names_controller_partitions():
    """Static guard: classical, VQC, noise, mitigation and pool code (2-5A): no ctrl_* literals."""
    sources = sorted((ROOT / "src" / "qtrace" / "classical").rglob("*.py"))
    sources += sorted((ROOT / "src" / "qtrace" / "qml").rglob("*.py"))
    sources += sorted((ROOT / "src" / "qtrace" / "noise").rglob("*.py"))
    sources += sorted((ROOT / "src" / "qtrace" / "mitigation").rglob("*.py"))
    sources += sorted((ROOT / "scripts").glob("*classical*.py"))
    sources += sorted((ROOT / "scripts").glob("*vqc*.py"))
    sources += sorted((ROOT / "scripts").glob("*noise*.py"))
    sources += sorted((ROOT / "scripts").glob("*p3b*.py"))
    sources += sorted((ROOT / "scripts").glob("*mitigation*.py"))
    sources += sorted((ROOT / "scripts").glob("*p4*.py"))
    sources += sorted((ROOT / "scripts").glob("*pool*.py"))
    sources += sorted((ROOT / "scripts").glob("*p5a*.py"))
    assert len(sources) >= 26  # the guard must actually inspect the Phase 2-5A code
    for path in sources:
        assert not any("ctrl_" in s for s in _string_constants(path)), path
