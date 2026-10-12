"""Phase 3A-R: folds, repair encoder, observables, diagnostics, CV, selection (synthetic)."""

from __future__ import annotations

import ast
import inspect

import numpy as np
import pandas as pd
import pytest
from qiskit.primitives import StatevectorEstimator
from qiskit.quantum_info import SparsePauliOp

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import AngleEncodingConfig, RepairStudyConfig
from qtrace.data import prepare_dataset
from qtrace.data.access import PartitionAccessError, check_access
from qtrace.data.folds import FOLD, assign_group_folds, equal_allocation
from qtrace.data.partition import GROUP_KEY, PARTITION
from qtrace.qml import circuit as C
from qtrace.qml import repair as R
from qtrace.qml import repair_outputs
from qtrace.qml.encoding import fit_angle_encoder
from qtrace.qml.model import predict
from qtrace.qml.simulate import feature_states, parity_diagonal, z_qubit_diagonal
from synthetic_ulb import EXPECTED, make_synthetic_ulb, write_synthetic

STUDY = load_component("repair", "p3ar_v1")
BASE = load_component("vqc", "vqc3a_top4_ra1")
SEEDS = load_experiment("phase3ar_vqc").spec.seeds


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    frame = make_synthetic_ulb()
    fraud = frame["Class"] == 1
    for col, shift in (("V17", -6.0), ("V14", -5.0), ("V12", -4.0), ("V10", -3.0)):
        frame.loc[fraud, col] += shift
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"), frame)
    return prepare_dataset(path, config, SEEDS)


@pytest.fixture(scope="module")
def train(prepared):
    f = prepared.features
    return f[f[PARTITION] == "vqc_train"].sort_values("row_id").reset_index(drop=True)


# ----------------------------------------------------------------------------- folds


def test_folds_group_aware_stratified_deterministic(prepared, train):
    rows = prepared.frame[prepared.frame["row_id"].isin(train["row_id"])].sort_values("row_id")
    folds = assign_group_folds(rows, prepared.config, 5, SEEDS.split, "p3ar-folds")
    assert folds["row_id"].tolist() == rows["row_id"].tolist()  # every row exactly once
    assert (folds.groupby(GROUP_KEY)[FOLD].nunique() == 1).all()  # groups never split
    labels = rows.set_index("row_id")["Class"]
    fraud_per_fold = folds.assign(y=labels.loc[folds["row_id"]].to_numpy()).groupby(FOLD)["y"].sum()
    assert sorted(fraud_per_fold.tolist()) == sorted(equal_allocation(int(labels.sum()), 5))
    again = assign_group_folds(
        rows.sample(frac=1.0, random_state=2), prepared.config, 5, SEEDS.split, "p3ar-folds"
    )
    pd.testing.assert_frame_equal(again, folds)
    other = assign_group_folds(rows, prepared.config, 5, SEEDS.split, "other-key")
    assert not other.equals(folds)


def test_equal_allocation():
    assert equal_allocation(213, 5) == [43, 43, 43, 42, 42]
    assert sum(equal_allocation(127_677, 5)) == 127_677


# ----------------------------------------------------------------- encoder/observable


def test_e0_encoder_equals_p3a_original_encoder(train):
    feats = ("V17", "V14", "V12", "V10")
    base = fit_angle_encoder(AngleEncodingConfig(), train, feats, "h")
    e0 = R.make_encoder(STUDY.encodings[0], base)
    np.testing.assert_array_equal(e0.transform(train), base.transform(train))
    e3 = R.make_encoder(STUDY.encodings[3], base)
    theta = e3.transform(train)
    assert np.abs(theta).max() <= np.pi / 4 + 1e-12


def test_first_qubit_z_matches_qiskit():
    fmap, ans, full = C.build(BASE)
    rng = np.random.default_rng(5)
    x, th = rng.uniform(-1, 1, (6, 4)), rng.uniform(-np.pi, np.pi, 8)
    p = predict(ans, feature_states(fmap, x), th, z_qubit_diagonal(4, 0))
    named = {f"x[{i}]": x[:, i] for i in range(4)} | {
        f"θ[{i}]": np.full(6, th[i]) for i in range(8)
    }
    values = np.column_stack([named[q.name] for q in full.parameters])
    z = StatevectorEstimator().run([(full, SparsePauliOp("IIIZ"), values)]).result()[0].data.evs
    np.testing.assert_allclose(p, (1 - z) / 2, atol=1e-12)
    # default observable is unchanged (P3A-original path)
    states = feature_states(fmap, x)
    np.testing.assert_array_equal(
        predict(ans, states, th), predict(ans, states, th, parity_diagonal(4))
    )


# ----------------------------------------------------------------------- diagnostics


def test_encoding_diagnostics_counts_collisions():
    frame = pd.DataFrame(
        {
            "V17": [-50.0, -60.0, 0.1, 0.2, -0.3, 0.0],
            "V14": [-50.0, -60.0, 0.1, 0.2, 0.3, 0.0],
            "V12": [-50.0, -60.0, 0.1, 0.2, 0.3, 0.0],
            "V10": [-50.0, -60.0, 0.1, 0.2, 0.3, 0.0],
            "Class": [1, 1, 0, 0, 0, 1],
        }
    )
    enc = R.RepairEncoder(
        enc_id="t",
        features=("V17", "V14", "V12", "V10"),
        median=(0.0,) * 4,
        iqr=(1.0,) * 4,
        clip=3.0,
        half_width=np.pi / 4,
    )
    fmap = C.feature_map(BASE)
    d = R.encoding_diagnostics(enc, frame, "Class", fmap, np.arange(6), STUDY)
    assert d["frauds_sharing_vector"] == 2  # the two saturated frauds collapse
    assert d["distinct_fraud_vectors"] == 2
    assert d["frauds_all_features_clipped"] == 2
    assert d["single_qubit_phase_injective"] and d["alias_probe_3a_fidelity"] is None
    assert d["probe_material_exact_collisions"] >= 1  # 50 vs 60 IQR: identical states
    wide = enc.model_copy(update={"clip": 100.0})
    assert (
        R.encoding_diagnostics(wide, frame, "Class", fmap, np.arange(6), STUDY)[
            "frauds_sharing_vector"
        ]
        == 0
    )


def test_eligibility_rules():
    control = {"frauds_sharing_vector": 10, "single_qubit_phase_injective": False}
    rules = STUDY.selection.eligibility
    assert not all(R.eligibility(control, control, rules).values())
    same_clip = {"frauds_sharing_vector": 10, "single_qubit_phase_injective": True}
    assert R.eligibility(same_clip, control, rules) == {
        "single_qubit_phase_injective": True,
        "fewer_shared_fraud_vectors_than_control": False,
    }
    repaired = {"frauds_sharing_vector": 3, "single_qubit_phase_injective": True}
    assert all(R.eligibility(repaired, control, rules).values())


# ------------------------------------------------------------------------- selection


def _summary(rows):
    cols = [
        "matrix_order",
        "cand_id",
        "ansatz_reps",
        "trainable_parameters",
        "eligible",
        "cv_auprc_mean",
        "cv_auprc_std",
    ]
    return pd.DataFrame(rows, columns=cols)


def test_selection_rule_and_tie_breakers():
    s = _summary(
        [
            (1, "ctrl", 1, 8, False, 0.90, 0.01),  # ineligible control can never win
            (2, "a", 2, 12, True, 0.500, 0.05),
            (3, "b", 1, 8, True, 0.497, 0.05),  # tied with a (within 0.005), same std, shallower
            (4, "c", 1, 8, True, 0.300, 0.01),
        ]
    )
    chosen, why = R.select(s, STUDY)
    assert chosen == "b" and why["decided_by"] == "tie-breakers"
    assert why["tied_candidates"] == ["a", "b"]
    s2 = _summary([(1, "a", 2, 12, True, 0.50, 0.08), (2, "b", 1, 8, True, 0.499, 0.02)])
    assert R.select(s2, STUDY)[0] == "b"  # lower CV std wins first
    s3 = _summary([(1, "a", 2, 12, True, 0.60, 0.08), (2, "b", 1, 8, True, 0.50, 0.01)])
    assert R.select(s3, STUDY)[0] == "a"  # outside tolerance: primary metric decides
    with pytest.raises(RuntimeError):
        R.select(_summary([(1, "x", 1, 8, False, 0.9, 0.0)]), STUDY)


def test_candidate_matrix_is_capped_and_preregistered():
    assert len(STUDY.candidates) == 10
    with pytest.raises(ValueError):
        RepairStudyConfig.model_validate(
            {**STUDY.model_dump(), "candidates": [STUDY.candidates[0].model_dump()] * 13}
        )


# ----------------------------------------------------------------------------- CV run


def test_cv_uses_fold_train_only_and_identical_restart_seeds(prepared, train):
    small = RepairStudyConfig.model_validate(
        {
            **STUDY.model_dump(),
            "candidates": [c.model_dump() for c in STUDY.candidates[4:6]],
            "cv": {**STUDY.cv.model_dump(), "n_folds": 2},
            "restarts": {**STUDY.restarts.model_dump(), "n_restarts": 2},
            "optimizer": {**STUDY.optimizer.model_dump(), "max_evaluations": 30},
        }
    )
    feats = ("V17", "V14", "V12", "V10")
    rows = prepared.frame[prepared.frame["row_id"].isin(train["row_id"])].sort_values("row_id")
    folds = assign_group_folds(rows, prepared.config, 2, SEEDS.split, "p3ar-folds")
    base_enc = fit_angle_encoder(AngleEncodingConfig(), train, feats, "h")
    fmap = C.feature_map(BASE)
    states = {
        e.enc_id: feature_states(fmap, R.make_encoder(e, base_enc).transform(train))
        for e in small.encodings
        if e.enc_id == "e2"
    }
    records, train_pos = R.run_cv(
        train, folds, small, BASE, SEEDS, states, target="Class", dataset_id="synthetic"
    )
    assert len(records) == 2 * 2 * 2
    seeds_by_cand = {}
    for r in records:
        seeds_by_cand.setdefault(r.cand_id, set()).add(r.init_seed)
    assert len({frozenset(v) for v in seeds_by_cand.values()}) == 1  # same seeds everywhere
    fold_of = folds[FOLD].to_numpy()
    for f, pos in train_pos.items():
        assert (fold_of[pos] != f).all()  # training rows never from the held-out fold
    summary = R.summarize(records, small, {"e2": True}, 4)
    assert summary["cv_auprc_mean"].notna().all() and len(summary) == 2
    assert EXPECTED["final_fraud"] > 0


# -------------------------------------------------------------------- access boundary


def test_selection_stage_cannot_read_vqc_val():
    with pytest.raises(PartitionAccessError):
        check_access("phase3ar_select", ["vqc_train", "vqc_val"])
    for phase in ("phase3ar_select", "phase3ar_eval"):
        for part in ("ctrl_train", "ctrl_val", "ctrl_test"):
            with pytest.raises(PartitionAccessError):
                check_access(phase, [part])
    source = inspect.getsource(repair_outputs.run_selection)
    literals = {
        n.value
        for n in ast.walk(ast.parse(source))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }
    assert "vqc_val" not in literals and "phase3ar_eval" not in literals
    assert "vqc_val" not in {
        n.value
        for n in ast.walk(ast.parse(inspect.getsource(R)))
        if isinstance(n, ast.Constant) and isinstance(n.value, str)
    }


def test_folds_from_stored_group_keys_match_recomputed(prepared, train):
    rows = prepared.frame[prepared.frame["row_id"].isin(train["row_id"])].sort_values("row_id")
    recomputed = assign_group_folds(rows, prepared.config, 5, SEEDS.split, "p3ar-folds")
    keyed = train[["row_id", "Class"]].merge(
        prepared.assignment[["row_id", GROUP_KEY]], on="row_id", validate="1:1"
    )
    stored = assign_group_folds(keyed, prepared.config, 5, SEEDS.split, "p3ar-folds")
    pd.testing.assert_frame_equal(stored, recomputed)


def test_partition_table_loader_respects_phase(prepared, tmp_path):
    from qtrace.data.access import load_partition_table

    table = prepared.assignment.merge(prepared.frame[["row_id", "Class"]], on="row_id")
    table.to_parquet(tmp_path / "partitions.parquet", index=False)
    loaded = load_partition_table(tmp_path, "phase3ar_select", ["vqc_train"])
    assert set(loaded[PARTITION]) == {"vqc_train"}
    with pytest.raises(PartitionAccessError):
        load_partition_table(tmp_path, "phase3ar_select", ["vqc_val"])
