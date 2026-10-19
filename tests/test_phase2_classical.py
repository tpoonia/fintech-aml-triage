"""Phase 2 representations, runner, tables and partition boundary (synthetic data only)."""

from __future__ import annotations

import json

import numpy as np
import pandas as pd
import pytest
from pydantic import ValidationError
from sklearn.decomposition import PCA
from sklearn.feature_selection import f_classif

from qtrace.classical import tables
from qtrace.classical.runner import run_phase2
from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import ClassicalBaselineConfig, RegimeConfig, RepresentationConfig
from qtrace.data import prepare_dataset
from qtrace.data.partition import PARTITION, partition_ids
from qtrace.data.representation import fit_representation
from synthetic_ulb import make_synthetic_ulb, write_synthetic

SEEDS = load_experiment("phase2_classical").spec.seeds
TRANSACTION_COLUMNS = {"row_id", "Time", "Amount", "Class", "score", "scores", "y_true", "y_score"}

SMALL = ClassicalBaselineConfig.model_validate(
    {
        "baseline_id": "test",
        "representations": [
            {"rep_id": "full", "kind": "full"},
            {"rep_id": "pca2", "kind": "pca", "n_components": 2},
            {"rep_id": "pca2-std", "kind": "pca", "n_components": 2, "standardize": True},
            {
                "rep_id": "top2",
                "kind": "select_k_best",
                "n_components": 2,
                "score_func": "f_classif",
            },
        ],
        "models": [
            {"model_id": "logreg", "kind": "logistic_regression", "params": {"max_iter": 500}},
            {"model_id": "rf", "kind": "random_forest", "params": {"n_estimators": 15}},
            {"model_id": "hgb", "kind": "hist_gradient_boosting", "params": {"max_iter": 20}},
        ],
        "regimes": [
            {"regime_id": "a-full", "kind": "full_partition", "class_weight": "balanced"},
            {"regime_id": "b-lpf2", "kind": "subset", "legit_per_fraud": 2, "draws": 2},
        ],
        "threshold": {},
        "bootstrap": {"n_resamples": 50},
        "calibration": {},
        "top_k": [10],
    }
)


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    frame = make_synthetic_ulb()
    frame.loc[frame["Class"] == 1, "V14"] -= 3.0  # inject learnable signal
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"), frame)
    return prepare_dataset(path, config, SEEDS)


def _split(prepared):
    f = prepared.features
    return f[f[PARTITION] == "vqc_train"], f[f[PARTITION] == "vqc_val"]


@pytest.fixture(scope="module")
def results(prepared):
    train, val = _split(prepared)
    return run_phase2(
        train,
        val,
        SMALL,
        SEEDS,
        dataset_id="synthetic",
        target="Class",
        feature_columns=prepared.fitted.output_columns,
        n_jobs=1,
    )


# ------------------------------------------------------------------- representations


def test_pca_matches_sklearn(prepared):
    train, val = _split(prepared)
    cols = prepared.fitted.output_columns
    rep = fit_representation(SMALL.representations[1], train, "Class", cols, "h")
    expected = (
        PCA(n_components=2, svd_solver="full").fit(train[list(cols)]).transform(val[list(cols)])
    )
    np.testing.assert_allclose(rep.transform(val), expected, atol=1e-10)
    assert (
        rep.artifact_sha256()
        == fit_representation(SMALL.representations[1], train, "Class", cols, "h").artifact_sha256()
    )


def test_select_k_best_uses_f_classif_ranking(prepared):
    train, _ = _split(prepared)
    cols = prepared.fitted.output_columns
    rep = fit_representation(SMALL.representations[3], train, "Class", cols, "h")
    scores, _ = f_classif(train[list(cols)], train["Class"])
    expected = [cols[i] for i in np.argsort(-scores, kind="stable")[:2]]
    assert list(rep.output_columns) == expected
    assert rep.output_columns[0] == "V14"  # the injected signal is found


def test_representation_config_validation():
    for bad in (
        {"rep_id": "x", "kind": "full", "n_components": 2},
        {"rep_id": "x", "kind": "pca"},
        {"rep_id": "x", "kind": "select_k_best", "n_components": 2},
        {"rep_id": "x", "kind": "full", "standardize": True},
    ):
        with pytest.raises(ValidationError):
            RepresentationConfig.model_validate(bad)
    with pytest.raises(ValidationError):
        RegimeConfig(regime_id="x", kind="subset")


def test_phase2_config_cannot_name_controller_partitions():
    base = load_component("baseline", "classical_v1").model_dump()
    for key, value in (("fit_partition", "ctrl_train"), ("eval_partition", "ctrl_test")):
        with pytest.raises(ValidationError):
            ClassicalBaselineConfig.model_validate({**base, key: value})


# ---------------------------------------------------------------------------- runner


def test_runner_covers_every_configuration(results):
    expected = len(SMALL.models) * len(SMALL.representations) * (1 + 2)
    assert len(results.results) == expected
    assert all(r.intervals for r in results.results if r.draw == 0)
    assert not any(r.intervals for r in results.results if r.draw > 0)


def test_learnable_signal_detected(results):
    full = {
        r.model_id: r.metrics
        for r in results.results
        if r.rep_id == "full" and r.regime_id == "a-full"
    }
    prevalence = results.y_val.mean()
    for m in full.values():  # every model finds the injected signal
        assert m["auprc"] > 5 * prevalence and m["auroc"] > 0.75
    assert full["logreg"]["auroc"] > 0.95  # the injected signal is linear


def test_subsets_drawn_from_vqc_train_only(prepared, results):
    train_ids = set(partition_ids(prepared.assignment, "vqc_train"))
    for ts in results.training_sets:
        assert set(ts.frame["row_id"]) <= train_ids
        if ts.subset is not None:
            assert ts.subset.n_legit == 2 * ts.subset.n_fraud


def test_runner_refuses_other_partitions(prepared):
    train, val = _split(prepared)
    ctrl = prepared.features[prepared.features[PARTITION] != "vqc_train"]
    with pytest.raises(ValueError, match="vqc_train"):
        run_phase2(
            ctrl,
            val,
            SMALL,
            SEEDS,
            dataset_id="s",
            target="Class",
            feature_columns=prepared.fitted.output_columns,
            n_jobs=1,
        )


def test_runner_is_deterministic(prepared, results):
    train, val = _split(prepared)
    again = run_phase2(
        train,
        val,
        SMALL,
        SEEDS,
        dataset_id="synthetic",
        target="Class",
        feature_columns=prepared.fitted.output_columns,
        n_jobs=1,
    )
    pd.testing.assert_frame_equal(tables.metrics_table(again), tables.metrics_table(results))
    pd.testing.assert_frame_equal(
        tables.representation_comparison(again, 0.95),
        tables.representation_comparison(results, 0.95),
    )


def test_tables_are_aggregate_only(results):
    for table in (
        tables.metrics_table(results),
        tables.regime_summary(results),
        tables.representation_comparison(results, 0.95),
        tables.calibration_table(results, SMALL),
        tables.pr_curve_table(results, SMALL),
    ):
        assert not TRANSACTION_COLUMNS & set(table.columns)
        assert len(table) < 2000
    meta = tables.metadata(results, SMALL, {"note": "test"})
    json.dumps(meta)
    assert all(len(s["row_ids_sha256"]) == 64 for s in meta["regime_b_subsets"])
