"""Phase 3A: encoder, circuit, exact engine, readout/BCE, training, pipeline (synthetic data)."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qiskit.primitives import StatevectorEstimator
from qiskit_aer.primitives import EstimatorV2 as AerEstimator
from sklearn.metrics import log_loss

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import AngleEncodingConfig, VQCConfig
from qtrace.data import prepare_dataset
from qtrace.data.partition import PARTITION
from qtrace.qml import circuit as C
from qtrace.qml.encoding import fit_angle_encoder
from qtrace.qml.model import bce, fraud_probability, predict, theta_sha256, train
from qtrace.qml.phase3a import SelectionMismatch, run_phase3a
from qtrace.qml.phase3a_outputs import comparison_table, score_histogram, trace_table
from qtrace.qml.simulate import ansatz_unitary, feature_states, parity_diagonal, parity_expectations
from synthetic_ulb import make_synthetic_ulb, write_synthetic

CFG = load_component("vqc", "vqc3a_top4_ra1")
SEEDS = load_experiment("phase3a_vqc").spec.seeds
BASELINE = load_component("baseline", "classical_v1")
FAST_BASELINE = BASELINE.model_copy(
    update={"bootstrap": BASELINE.bootstrap.model_copy(update={"n_resamples": 50})}
)
SMALL_CFG = VQCConfig.model_validate(
    {
        **CFG.model_dump(),
        "optimizer": {**CFG.optimizer.model_dump(), "max_evaluations": 60},
        "subset": {"subset_id": "test-lpf4", "legit_per_fraud": 4, "expected_rows": None},
    }
)


# --------------------------------------------------------------------------- encoder


def test_encoder_formula_range_and_sign():
    train = pd.DataFrame({"a": [-2.0, -1.0, 0.0, 1.0, 2.0, 50.0], "b": [0.0, 1, 2, 3, 4, -40]})
    enc = fit_angle_encoder(AngleEncodingConfig(), train, ("a", "b"), "h")
    med = np.median(train[["a", "b"]], axis=0)
    q1, q3 = np.percentile(train[["a", "b"]], [25, 75], axis=0)
    r = (train[["a", "b"]].to_numpy() - med) / (q3 - q1)
    np.testing.assert_allclose(enc.transform(train), (np.pi / 3) * np.clip(r, -3, 3))
    theta = enc.transform(train)
    assert theta.min() >= -np.pi and theta.max() <= np.pi
    assert theta[-1, 0] == pytest.approx(np.pi) and theta[-1, 1] == pytest.approx(-np.pi)
    assert np.all(np.sign(theta) == np.sign(r))  # sign preserved
    assert enc.clip_fractions(train) == {"a": pytest.approx(1 / 6), "b": pytest.approx(1 / 6)}


def test_encoder_uses_only_the_rows_it_is_given():
    train = pd.DataFrame({"a": np.arange(10.0)})
    enc = fit_angle_encoder(AngleEncodingConfig(), train, ("a",), "h")
    other = pd.DataFrame({"a": [1e9, -1e9]})
    assert enc == fit_angle_encoder(AngleEncodingConfig(), train, ("a",), "h")
    assert np.abs(enc.transform(other)).max() == pytest.approx(np.pi)  # saturates, no refit
    with pytest.raises(ValueError, match="interquartile"):
        fit_angle_encoder(AngleEncodingConfig(), pd.DataFrame({"a": [1.0] * 5}), ("a",), "h")


# --------------------------------------------------------------------- circuit/engine


def test_circuit_structure_and_transpiled_statistics():
    fmap, ans, full = C.build(CFG)
    assert [p.name for p in fmap.parameters] == [f"x[{i}]" for i in range(4)]
    assert [p.name for p in ans.parameters] == [f"θ[{i}]" for i in range(8)]
    assert set(full.parameters) == set(fmap.parameters) | set(ans.parameters)
    tc, stats = C.transpiled_statistics(CFG, seed=7)
    assert set(tc.count_ops()) <= set(CFG.basis_gates)
    assert stats["qubits"] == 4 and stats["data_parameters"] == 4
    assert stats["trainable_parameters"] == 8 and stats["two_qubit_gates"] > 0
    assert str(C.parity_observable(4).paulis[0]) == "ZZZZ"


def test_exact_engine_matches_qiskit_and_aer():
    fmap, ans, full = C.build(CFG)
    rng = np.random.default_rng(3)
    x, th = rng.uniform(-np.pi, np.pi, (12, 4)), rng.uniform(-np.pi, np.pi, 8)
    z = parity_expectations(feature_states(fmap, x), ansatz_unitary(ans, th), parity_diagonal(4))

    def values(params):
        named = {f"x[{i}]": x[:, i] for i in range(4)}
        named |= {f"θ[{i}]": np.full(len(x), th[i]) for i in range(8)}
        return np.column_stack([named[p.name] for p in params])

    obs = C.parity_observable(4)
    ref = StatevectorEstimator().run([(full, obs, values(full.parameters))]).result()[0].data.evs
    tc, _ = C.transpiled_statistics(CFG, seed=7)
    aer = AerEstimator(options={"backend_options": {"method": "density_matrix"}})
    dm = aer.run([(tc, obs.apply_layout(tc.layout), values(tc.parameters))]).result()[0].data.evs
    np.testing.assert_allclose(z, ref, atol=1e-12)
    np.testing.assert_allclose(z, dm, atol=1e-10)


def test_parity_diagonal():
    assert parity_diagonal(2).tolist() == [1.0, -1.0, -1.0, 1.0]


# ------------------------------------------------------------------- readout and BCE


def test_readout_orientation_is_fixed():
    assert fraud_probability(np.array([1.0, 0.0, -1.0])).tolist() == [0.0, 0.5, 1.0]


def test_bce_matches_sklearn_and_is_clipped():
    y = np.array([0, 1, 1, 0])
    p = np.array([0.1, 0.8, 0.6, 0.3])
    assert bce(y, p, 1e-7) == pytest.approx(log_loss(y, p))
    assert np.isfinite(bce(np.array([1]), np.array([0.0]), 1e-7))
    assert bce(np.array([1]), np.array([0.0]), 1e-7) == pytest.approx(-np.log(1e-7))


def test_training_reduces_loss_and_is_deterministic():
    fmap, ans, _ = C.build(CFG)
    rng = np.random.default_rng(0)
    x = rng.uniform(-np.pi, np.pi, (80, 4))
    y = (x[:, 0] > 0).astype(int)
    states = feature_states(fmap, x)
    opt = CFG.optimizer.model_copy(update={"max_evaluations": 80})
    a = train(ans, states, y, opt, 1e-7, seed=11)
    b = train(ans, states, y, opt, 1e-7, seed=11)
    assert a.final_loss < a.initial_loss
    assert a.nfev <= 80 and len(a.trace) == a.nfev
    np.testing.assert_array_equal(a.theta, b.theta)
    assert theta_sha256(a.theta) == theta_sha256(b.theta)
    np.testing.assert_allclose(predict(ans, states, a.theta), predict(ans, states, b.theta))


# --------------------------------------------------------------------------- pipeline


@pytest.fixture(scope="module")
def prepared(tmp_path_factory):
    frame = make_synthetic_ulb()
    fraud = frame["Class"] == 1
    for col, shift in (("V17", -6.0), ("V14", -5.0), ("V12", -4.0), ("V10", -3.0)):
        frame.loc[fraud, col] += shift  # selection must reproduce V17, V14, V12, V10
    path, config = write_synthetic(tmp_path_factory.mktemp("ulb"), frame)
    return prepare_dataset(path, config, SEEDS)


def _run(prepared, cfg=SMALL_CFG, train_df=None):
    f = prepared.features
    return run_phase3a(
        f[f[PARTITION] == "vqc_train"] if train_df is None else train_df,
        f[f[PARTITION] == "vqc_val"],
        cfg,
        FAST_BASELINE,
        SEEDS,
        dataset_id="synthetic",
        target="Class",
        feature_columns=prepared.fitted.output_columns,
        provenance={"dataset_sha256": "0" * 64, "preprocessing_sha256": "p", "software": {}},
    )


@pytest.fixture(scope="module")
def results(prepared):
    return _run(prepared)


def test_pipeline_reproduces_selection_and_is_reproducible(results):
    assert results.features == ("V17", "V14", "V12", "V10")
    assert results.retrain_max_abs_param_diff == 0.0
    assert results.replay_max_abs_score_diff == 0.0
    assert results.subset.n_legit == 4 * results.subset.n_fraud
    assert np.unique(results.vqc.scores).size > 10  # non-constant predictions
    assert results.training.final_loss < results.training.initial_loss


def test_selection_mismatch_is_fatal(prepared):
    bad = SMALL_CFG.model_copy(update={"expected_features": ("V1", "V2", "V3", "V4")})
    with pytest.raises(SelectionMismatch):
        _run(prepared, bad)


def test_pipeline_refuses_controller_rows(prepared):
    ctrl = prepared.features[prepared.features[PARTITION] == "ctrl_train"]
    with pytest.raises(ValueError, match="vqc_train"):
        _run(prepared, train_df=ctrl)


def test_tables_are_aggregate_only(results):
    forbidden = {"row_id", "Time", "Amount", "Class", "score", "y_true", "y_score"}
    for table in (comparison_table(results, 0.95), trace_table(results), score_histogram(results)):
        assert not forbidden & set(table.columns) and len(table) < 2000
    cmp_ = comparison_table(results, 0.95)
    assert cmp_["model"].tolist() == ["vqc", "logreg", "rf", "hgb"]
    assert cmp_["input_dim"].eq(4).all() and cmp_["n_train"].nunique() == 1
