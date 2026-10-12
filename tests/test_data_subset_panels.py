"""VQC-training-subset utility and evaluation-panel interface (synthetic data)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qtrace.config import load_experiment
from qtrace.data import (
    Panel,
    PanelSampler,
    SubsetSpec,
    build_vqc_training_subset,
    prepare_dataset,
    validate_panel_membership,
)
from qtrace.data.panels import PanelError
from qtrace.data.partition import partition_ids
from qtrace.data.subset import SubsetError
from synthetic_ulb import write_synthetic

SEEDS = load_experiment("prepare_ulb_v1").spec.seeds


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"))
    return prepare_dataset(path, config, SEEDS)


def build(prepared, spec, seed=SEEDS.undersample):
    return build_vqc_training_subset(
        prepared.frame,
        prepared.assignment,
        spec,
        target="Class",
        dataset_id="synthetic",
        undersample_seed=seed,
    )


# --------------------------------------------------------------------------- subset


def test_subset_draws_only_from_vqc_train(prepared):
    record = build(prepared, SubsetSpec(subset_id="s1", legit_per_fraud=4))
    train = set(partition_ids(prepared.assignment, "vqc_train"))
    assert set(record.row_ids) <= train
    labels = prepared.frame.set_index("row_id")["Class"]
    train_frauds = int(labels.loc[list(train)].sum())
    assert record.n_fraud == train_frauds == int(labels.loc[list(record.row_ids)].sum())
    assert record.n_legit == 4 * train_frauds
    assert record.source_partition_rows == len(train)


def test_subset_deterministic_and_seed_sensitive(prepared):
    spec = SubsetSpec(subset_id="s1", legit_per_fraud=3)
    a, b = build(prepared, spec), build(prepared, spec)
    assert a == b and a.row_ids_sha256 == b.row_ids_sha256
    assert build(prepared, spec, seed=SEEDS.undersample + 1).row_ids != a.row_ids
    other_id = SubsetSpec(subset_id="s2", legit_per_fraud=3)
    assert build(prepared, other_id).row_ids != a.row_ids


def test_subset_explicit_counts_and_limits(prepared):
    record = build(
        prepared, SubsetSpec(subset_id="s3", include_all_fraud=False, n_fraud=5, n_legit=7)
    )
    assert (record.n_fraud, record.n_legit, len(record.row_ids)) == (5, 7, 12)
    with pytest.raises(SubsetError, match="exceeds max_samples"):
        build(prepared, SubsetSpec(subset_id="s4", legit_per_fraud=4, max_samples=10))
    with pytest.raises(SubsetError, match="legitimate rows"):
        build(prepared, SubsetSpec(subset_id="s5", n_legit=10**7))
    with pytest.raises(SubsetError, match="frauds"):
        build(
            prepared, SubsetSpec(subset_id="s6", include_all_fraud=False, n_fraud=10**6, n_legit=1)
        )


@pytest.mark.parametrize(
    "kwargs",
    [
        {"subset_id": "x"},  # neither legit_per_fraud nor n_legit
        {"subset_id": "x", "legit_per_fraud": 2, "n_legit": 3},
        {"subset_id": "x", "legit_per_fraud": 2, "n_fraud": 4},  # with include_all_fraud=True
        {"subset_id": "x", "legit_per_fraud": 2, "source_partition": "ctrl_train"},
        {"subset_id": "x", "legit_per_fraud": 2, "source_partition": "ctrl_test"},
    ],
)
def test_subset_spec_validation(kwargs):
    with pytest.raises(ValidationError):
        SubsetSpec(**kwargs)


# --------------------------------------------------------------------------- panels


def test_panel_cannot_come_from_vqc_train():
    with pytest.raises(ValidationError):
        Panel(panel_id="p", source_partition="vqc_train", row_ids=(1,), sampling={})


@pytest.mark.parametrize(
    "kwargs",
    [
        {"row_ids": (1, 1)},
        {"row_ids": (1, 2), "weights": (1.0,)},
        {"row_ids": (1, 2), "weights": (1.0, 0.0)},
        {"row_ids": ()},
    ],
)
def test_panel_validation(kwargs):
    with pytest.raises(ValidationError):
        Panel(panel_id="p", source_partition="ctrl_val", sampling={}, **kwargs)


def test_panel_membership_and_hash(prepared):
    ids = tuple(int(i) for i in partition_ids(prepared.assignment, "ctrl_test")[:20])
    panel = Panel(
        panel_id="p", source_partition="ctrl_test", row_ids=ids, sampling={"note": "test"}
    )
    validate_panel_membership(panel, prepared.assignment)
    assert panel.panel_hash() == Panel(**panel.model_dump()).panel_hash()
    assert panel.panel_hash() != panel.model_copy(update={"row_ids": ids[:-1]}).panel_hash()
    mislabeled = panel.model_copy(update={"source_partition": "ctrl_val"})
    with pytest.raises(PanelError, match="outside"):
        validate_panel_membership(mislabeled, prepared.assignment)
    with pytest.raises(PanelError, match="not in the partition table"):
        validate_panel_membership(
            panel.model_copy(update={"row_ids": (10**9,)}), prepared.assignment
        )


def test_panel_sampler_is_an_interface_only(prepared):
    with pytest.raises(TypeError):
        PanelSampler()  # abstract: no strategy is frozen (O06)

    class FirstRows(PanelSampler):
        def sample(self, frame, assignment, *, source_partition, seed):
            ids = tuple(int(i) for i in partition_ids(assignment, source_partition)[:5])
            return Panel(
                panel_id="first",
                source_partition=source_partition,
                row_ids=ids,
                sampling={"strategy": "first_rows"},
                seed=seed,
            )

    panel = FirstRows().sample(
        prepared.frame, prepared.assignment, source_partition="ctrl_val", seed=1
    )
    validate_panel_membership(panel, prepared.assignment)
