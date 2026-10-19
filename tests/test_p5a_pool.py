"""Phase 5A pool mechanics on synthetic inputs: registry and IDs, train-only representations and
encoders, circuits and readouts, deterministic training with Aer agreement, qualification and
duplicate detection, power formula and the G3A rule. No transaction data."""

from __future__ import annotations

import ast
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from qtrace.config import load_component, repo_root
from qtrace.config.schemas import PoolEncodingConfig, PoolFeatureSetConfig
from qtrace.noise.exact import exact_distributions
from qtrace.qml import pool as P
from qtrace.qml import pool_study as PS
from qtrace.qml.simulate import feature_states, parity_diagonal, z_qubit_diagonal

ROOT = repo_root()


@pytest.fixture(scope="module")
def study():
    return load_component("pool_study", "p5a_v1")


@pytest.fixture(scope="module")
def synth():
    rng = np.random.default_rng(3)
    n = 600
    y = (rng.random(n) < 0.2).astype(int)
    cols = [f"V{i}" for i in range(1, 9)]
    x = rng.normal(size=(n, 8))
    x[:, 2] += 2.0 * y  # V3 most informative
    x[:, 5] += 1.5 * y
    x[:, 0] += 1.0 * y
    x[:, 7] += 0.7 * y
    x[:, 3] += 0.4 * y
    frame = pd.DataFrame(x, columns=cols).assign(Class=y)
    return frame, y, tuple(cols)


def test_registry_ids_and_size(study):
    reg = PS.registry(study)
    cands = [c for c in reg if c.role == "candidate"]
    assert len(cands) == 64 and len({c.model_id for c in reg}) == len(reg)
    assert cands[0].model_id == "p5a-top4-e3-ra1-parity-s0"
    assert all(c.model_id.endswith(f"-s{c.seed_index}") for c in cands)
    assert [c.model_id for c in reg if c.role == "control"] == ["ctrl-shallow"]


def test_feature_sets_are_train_only_and_reproducible(synth):
    frame, _, cols = synth
    top = PoolFeatureSetConfig(feat_id="t", kind="anova_ranks", ranks=(1, 4))
    nxt = PoolFeatureSetConfig(feat_id="n", kind="anova_ranks", ranks=(5, 8))
    rep_t = P.fit_feature_set(top, frame, "Class", cols, "h")
    rep_n = P.fit_feature_set(nxt, frame, "Class", cols, "h")
    assert rep_t.output_columns[:2] == ("V3", "V6")
    assert set(rep_t.output_columns).isdisjoint(rep_n.output_columns)
    assert len(rep_n.output_columns) == 4
    wrong = top.model_copy(update={"expected_features": ("V1", "V2", "V4", "V5")})
    with pytest.raises(RuntimeError):
        P.fit_feature_set(wrong, frame, "Class", cols, "h")
    pca = P.fit_feature_set(
        PoolFeatureSetConfig(feat_id="p", kind="pca"), frame, "Class", cols, "h"
    )
    assert pca.transform(frame).shape == (len(frame), 4)


@pytest.mark.parametrize("kind,scale", [("clip_linear", 15), ("clip_linear", 5), ("tanh", 5)])
def test_encoders_are_alias_safe(kind, scale):
    rng = np.random.default_rng(4)
    x = rng.standard_cauchy(size=(2000, 4))
    enc = P.fit_encoder(
        PoolEncodingConfig(enc_id="e", kind=kind, scale=scale, half_width=np.pi / 4), x
    )
    a = enc.transform(x)
    assert np.abs(a).max() <= np.pi / 4 + 1e-15
    assert np.allclose(enc.median, np.median(x, axis=0))
    if kind == "tanh":
        assert np.unique(np.round(a, 12), axis=0).shape[0] == len(x)  # no clipping collisions


def test_shared_fraud_vector_fraction():
    a = np.array([[0.1, 0.2], [0.1, 0.2], [0.3, 0.4], [0.5, 0.6]])
    y = np.array([1, 1, 1, 0])
    assert P.shared_fraud_vector_fraction(a, y) == pytest.approx(2 / 3)


@pytest.mark.parametrize(
    "ans_id,params", [("ra0", 4), ("ra1", 8), ("ra2", 12), ("esu1", 16), ("esu2", 24)]
)
def test_ansatz_sizes(study, ans_id, params):
    cfg = next(a for a in study.ansatze if a.ans_id == ans_id)
    assert P.ansatz(cfg, 4).num_parameters == params


def test_readout_diagonals():
    mz = P.readout_diagonal("mean_z", 4)
    assert np.allclose(mz, np.mean([z_qubit_diagonal(4, q) for q in range(4)], axis=0))
    assert mz.min() == -1 and mz.max() == 1
    assert np.array_equal(P.readout_diagonal("parity", 4), parity_diagonal(4))
    with pytest.raises(ValueError):
        P.readout_diagonal("z_qubit0", 4)


@pytest.mark.parametrize(
    "ans_id,readout", [("ra2", "parity"), ("esu1", "mean_z"), ("esu2", "parity")]
)
def test_aer_replay_equals_exact_engine(study, ans_id, readout):
    fmap = P.feature_map(4, study)
    ans = P.ansatz(next(a for a in study.ansatze if a.ans_id == ans_id), 4)
    tc, stats_ = P.transpile_structure(fmap, ans, study, 11)
    assert stats_["layout_is_none"] and stats_["trainable_parameters"] == ans.num_parameters
    rng = np.random.default_rng(5)
    angles = rng.uniform(-np.pi / 4, np.pi / 4, size=(40, 4))
    theta = rng.uniform(-np.pi, np.pi, ans.num_parameters)
    diag = P.readout_diagonal(readout, 4)
    from qtrace.qml.model import predict

    p = predict(ans, feature_states(fmap, angles), theta, diag)
    probs = exact_distributions(tc, P.binding_values(tc, angles, theta), None)
    assert np.max(np.abs(probs @ diag - (1 - 2 * p))) <= 1e-10
    _, again = P.transpile_structure(fmap, ans, study, 11)
    assert again["qasm3_sha256"] == stats_["qasm3_sha256"]


def test_training_is_deterministic_with_retrain_and_aer_checks(study, synth):
    frame, y, cols = synth
    fmap = P.feature_map(4, study)
    ans_cfg = next(a for a in study.ansatze if a.ans_id == "ra1")
    angles = np.pi / 4 * np.tanh(frame[list(cols[:4])].to_numpy() / 3)
    states = feature_states(fmap, angles)
    tc, _ = P.transpile_structure(fmap, P.ansatz(ans_cfg, 4), study, 3)
    opt = study.optimizer.model_copy(update={"max_evaluations": 60})
    cand = PS.Candidate("m", "candidate", study.structures[0], 0)
    args = (
        cand,
        ans_cfg,
        states[:300],
        y[:300],
        states,
        P.readout_diagonal("parity", 4),
        opt,
        1e-7,
        [1, 2],
        tc,
        angles[:32],
    )
    a, b = PS._train_one(*args), PS._train_one(*args)
    assert np.array_equal(a["theta"], b["theta"]) and np.array_equal(a["p_val"], b["p_val"])
    assert a["retrain_identical"] and a["aer_max_abs_dz"] <= 1e-10
    assert a["kept_restart"] == int(np.argmin(a["restart_final_bce"]))


def _m(**kw):
    base = {
        "auroc_ci_low": 0.8,
        "auprc_ci_low": 0.1,
        "distinct_scores": 500,
        "finite_in_unit_interval": True,
        "prediction_sha256": "p1",
    }
    return base | kw


def _o(**kw):
    base = {
        "final_bce": 0.5,
        "initial_bce": 0.7,
        "aer_max_abs_dz": 1e-15,
        "retrain_identical": True,
    }
    return base | kw


ENC = {"alias_safe": True, "shared_fraud_vector_fraction": 0.1}


def test_qualification_criteria_and_duplicates(study):
    q, prev = study.qualification, 0.00166
    ok = PS.qualify(_m(), _o(), ENC, q, prev, "t1", set(), set())
    assert all(ok.values())
    assert not PS.qualify(_m(auroc_ci_low=0.49), _o(), ENC, q, prev, "t1", set(), set())[
        "Q1_auroc_ci_low"
    ]
    assert not PS.qualify(_m(auprc_ci_low=0.016), _o(), ENC, q, prev, "t1", set(), set())[
        "Q2_auprc_ci_low"
    ]
    assert not PS.qualify(_m(), _o(final_bce=0.69), ENC, q, prev, "t1", set(), set())[
        "Q3_loss_reduction"
    ]
    assert not PS.qualify(_m(distinct_scores=99), _o(), ENC, q, prev, "t1", set(), set())[
        "Q4_distinct_scores"
    ]
    bad_enc = {"alias_safe": True, "shared_fraud_vector_fraction": 0.58}
    assert not PS.qualify(_m(), _o(), bad_enc, q, prev, "t1", set(), set())["Q6_encoding"]
    assert not PS.qualify(_m(), _o(aer_max_abs_dz=1e-6), ENC, q, prev, "t1", set(), set())[
        "Q7_aer_crosscheck"
    ]
    assert not PS.qualify(_m(), _o(retrain_identical=False), ENC, q, prev, "t1", set(), set())[
        "Q8_bitwise_retrain"
    ]
    assert not PS.qualify(_m(), _o(), ENC, q, prev, "t1", {"t1"}, set())["Q9_not_duplicate"]
    assert not PS.qualify(_m(), _o(), ENC, q, prev, "t2", set(), {"p1"})["Q9_not_duplicate"]


def test_prediction_hash_is_rounding_stable():
    p = np.linspace(0, 1, 50)
    assert PS.prediction_sha256(p) == PS.prediction_sha256(p + 1e-15)
    assert PS.prediction_sha256(p) != PS.prediction_sha256(p[::-1])


def test_mde_ratio_matches_noncentral_simulation():
    n, r = 40, 20
    ratio = PS.mde_ratio(n, r, 0.05, 0.8)
    crit = stats.f.ppf(0.95, n - 1, n * (r - 1))
    power = stats.f.sf(crit / (1 + r * ratio**2), n - 1, n * (r - 1))
    assert power == pytest.approx(0.8, abs=1e-6)
    assert PS.mde_ratio(60, 20, 0.05, 0.8) < ratio < PS.mde_ratio(20, 20, 0.05, 0.8)
    assert PS.mde_ratio(40, 5, 0.05, 0.8) > ratio


def _records(n_struct=16, seeds=4, readouts=("parity", "mean_z")):
    feats = ["top4", "next4", "pca4"]
    encs = ["e3", "e2", "s5"]
    fams = ["real_amplitudes", "efficient_su2"]
    out = []
    for s in range(n_struct):
        for k in range(seeds):
            out.append(
                {
                    "struct_id": f"s{s}",
                    "seed_index": k,
                    "features": feats[s % 3],
                    "encoding": encs[s % 3],
                    "family": fams[s % 2],
                    "reps": 1 + (s // 2) % 2,
                    "readout": readouts[s % len(readouts)],
                    "auprc": 0.4,
                }
            )
    return out


def _pairs(rho, n=100, ident=0.0):
    k = int(n * ident)
    return pd.DataFrame(
        {"pair_type": ["two_plus_axes"] * n, "spearman": [0.9995] * k + [rho] * (n - k)}
    )


def test_g3a_rule(study):
    g = study.g3a
    q = _records()
    assert PS.g3a_rule(q, _pairs(0.8), 3.0, g, 0.00166, 4, 64)["verdict"] == "PASS"
    assert PS.g3a_rule(q, _pairs(0.97), 3.0, g, 0.00166, 4, 64)["verdict"] == "CONDITIONAL PASS"
    assert PS.g3a_rule(q, _pairs(0.995), 3.0, g, 0.00166, 4, 64)["verdict"] == "FAIL"
    assert PS.g3a_rule(q, _pairs(0.8), 100.0, g, 0.00166, 4, 64)["verdict"] == "CONDITIONAL PASS"
    assert PS.g3a_rule(q, _pairs(0.8), 200.0, g, 0.00166, 4, 64)["verdict"] == "FAIL"
    assert PS.g3a_rule(q[:39], _pairs(0.8), 3.0, g, 0.00166, 4, 64)["verdict"] == "FAIL"
    one_readout = _records(readouts=("parity",))
    out = PS.g3a_rule(one_readout, _pairs(0.8), 3.0, g, 0.00166, 4, 64)
    assert out["verdict"] == "CONDITIONAL PASS" and not out["criteria"]["b_coverage"]
    assert PS.g3a_rule(q, _pairs(0.8, ident=0.6), 3.0, g, 0.00166, 4, 64)["verdict"] == "FAIL"


def test_diversity_summary_groups():
    pairs = pd.DataFrame(
        {
            "pair_type": ["same_structure", "one_axis", "two_plus_axes", "with_anchor"],
            "spearman": [0.99, 0.9, 0.7, 0.8],
            "kendall": [0.9, 0.8, 0.6, 0.7],
            "mean_abs_diff": [0.01, 0.02, 0.05, 0.03],
            "flag_disagreement": [0.0, 0.001, 0.002, 0.001],
        }
    )
    s = PS.diversity_summary(pairs).set_index("pair_type")
    assert s.loc["all_pool_pairs", "n_pairs"] == 3 and s.loc["between_structure", "n_pairs"] == 2


def test_pool_code_never_names_controller_partitions():
    sources = [
        ROOT / "src" / "qtrace" / "qml" / "pool.py",
        ROOT / "src" / "qtrace" / "qml" / "pool_study.py",
    ]
    sources += sorted((ROOT / "scripts").glob("*pool*.py")) + sorted(
        (ROOT / "scripts").glob("*p5a*.py")
    )
    for path in sources:
        consts = {
            n.value
            for n in ast.walk(ast.parse(Path(path).read_text()))
            if isinstance(n, ast.Constant) and isinstance(n.value, str)
        }
        assert not any("ctrl_" in c for c in consts), path
