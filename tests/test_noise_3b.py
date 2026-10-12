"""Phase 3B noise engine: construction, readout, exact engine, negative control, rules, sampler.

Synthetic inputs only (no transaction data); the frozen artifacts are committed files.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qiskit import QuantumCircuit
from qiskit.quantum_info import SuperOp
from qiskit_aer.noise import depolarizing_error, thermal_relaxation_error

from qtrace.config import load_component, load_experiment, repo_root
from qtrace.config.schemas import A13RulesConfig, NoiseProfile
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import stratified_weights
from qtrace.noise import diagnostics as D
from qtrace.noise import shots as S
from qtrace.noise.exact import exact_distributions
from qtrace.noise.frozen import load_frozen
from qtrace.noise.models import apply_readout, gate_noise_model, has_gate_noise
from qtrace.noise.study import CLEAN, g1_family, load_study

ROOT = repo_root()
BASIS = ("rz", "sx", "x", "cx")
RULES = A13RulesConfig()


@pytest.fixture(scope="module")
def setup():
    resolved, study, profiles = load_study()
    return resolved, study, {p.profile_id: p for p in profiles}


@pytest.fixture(scope="module")
def frozen(setup):
    resolved, study, _ = setup
    rng = np.random.default_rng(7)
    frame = pd.DataFrame(rng.normal(0, 3, size=(64, 4)), columns=["V17", "V14", "V12", "V10"])
    return {ref.model_id: (load_frozen(ROOT, ref, resolved.vqc), frame) for ref in study.models}


# ----------------------------------------------------------------------- noise matrix


def test_registered_matrix_has_15_conditions_and_labelled_synthetic_profiles(setup):
    _, study, profiles = setup
    assert len(profiles) == 15
    assert study.partition == "vqc_val"
    synth = [p for p in profiles.values() if p.role == "synthetic_stress"]
    assert [p.profile_id for p in synth] == ["ar-005", "ar-020", "ar-050"]
    assert all(not p.readout_symmetric for p in synth)
    assert {g1_family(p) for p in synth} == {"synthetic_asymmetric_readout"}
    nc = [p for p in profiles.values() if p.role == "negative_control"]
    assert all(p.readout_symmetric and not has_gate_noise(p) for p in nc) and len(nc) == 3
    desc = load_component("noise", "synthetic_asym_v1").description
    assert "synthetic asymmetric readout stress-test" in desc and "not device calibration" in desc


def test_gate_noise_only_on_sx_x_cx_and_readout_only_when_asked(setup):
    _, _, profiles = setup
    m = gate_noise_model(profiles["comb-high"], BASIS)
    assert set(m.noise_instructions) == {"sx", "x", "cx"}
    assert not m._default_readout_error
    full = gate_noise_model(profiles["comb-high"], BASIS, include_readout=True)
    assert full._default_readout_error is not None
    ro = gate_noise_model(profiles["ar-050"], BASIS, include_readout=True)
    assert set(ro.noise_instructions) == {"measure"}
    assert not gate_noise_model(profiles["ar-050"], BASIS).noise_instructions


def test_composition_is_depolarizing_then_thermal(setup):
    _, _, profiles = setup
    p = profiles["comb-high"]
    m = gate_noise_model(p, BASIS)
    t1, t2 = p.thermal.t1_us * 1e-6, p.thermal.t2_us * 1e-6
    want1 = depolarizing_error(p.p1, 1).compose(thermal_relaxation_error(t1, t2, 35e-9))
    got1 = m._default_quantum_errors["sx"]
    assert np.allclose(SuperOp(got1).data, SuperOp(want1).data, atol=1e-12)
    th = thermal_relaxation_error(t1, t2, 300e-9)
    want2 = depolarizing_error(p.p2, 2).compose(th.tensor(th))
    assert np.allclose(SuperOp(m._default_quantum_errors["cx"]).data, SuperOp(want2).data)


# ----------------------------------------------------------------------------- readout


def test_classical_readout_matches_kronecker_confusion():
    rng = np.random.default_rng(1)
    probs = rng.dirichlet(np.ones(16), size=5)
    p01, p10 = 0.025, 0.075
    c = np.array([[1 - p01, p10], [p01, 1 - p10]])  # [read, prepared]
    full = c
    for _ in range(3):
        full = np.kron(full, c)
    assert np.allclose(apply_readout(probs, p01, p10), probs @ full.T, atol=1e-15)
    assert np.allclose(apply_readout(probs, p01, p10).sum(axis=1), 1.0)


def test_readout_orientation_p01_is_read_one_given_zero():
    zero = np.zeros((1, 16))
    zero[0, 0] = 1.0
    out = apply_readout(zero, 0.1, 0.3)[0]
    assert out[0] == pytest.approx(0.9**4)
    assert out[1] == pytest.approx(0.1 * 0.9**3)  # one qubit read as 1
    one = np.zeros((1, 16))
    one[0, 15] = 1.0
    assert apply_readout(one, 0.1, 0.3)[0][0] == pytest.approx(0.3**4)


def test_classical_readout_equals_aer_readout_error_in_distribution(setup):
    """Aer ReadoutError shots agree with the classical confusion (chi-square, 200k shots)."""
    from qiskit_aer import AerSimulator

    _, _, profiles = setup
    p = profiles["ar-050"]
    qc = QuantumCircuit(4)
    qc.ry(1.1, 0)
    qc.ry(0.4, 1)
    qc.cx(0, 2)
    qc.ry(2.0, 3)
    qc = qc.decompose()
    from qiskit import transpile

    tc = transpile(qc, basis_gates=list(BASIS), optimization_level=1, seed_transpiler=3)
    exact = exact_distributions(tc, np.zeros((1, 0)), None)
    expected = apply_readout(exact, p.readout_p01, p.readout_p10)
    meas = tc.copy()
    meas.measure_all()
    sim = AerSimulator(
        method="density_matrix",
        noise_model=gate_noise_model(p, BASIS, include_readout=True),
        seed_simulator=11,
    )
    counts = sim.run(meas, shots=200_000).result().get_counts()
    obs = np.zeros(16)
    for k, v in counts.items():
        obs[int(k, 2)] = v
    _, _, pval = S.merged_chi2(obs[None, :], expected, 200_000, 5.0)
    assert pval > 1e-3


# ---------------------------------------------------------------------- exact engine


def test_frozen_models_verified_and_aer_clean_equals_exact_engine(frozen):
    for fc, frame in frozen.values():
        probs = exact_distributions(fc.transpiled, fc.values(frame), None)
        z_engine = 1 - 2 * fc.exact_engine_scores(frame)
        assert np.max(np.abs(D.parity_z(probs) - z_engine)) <= 1e-10
        assert np.allclose(probs.sum(axis=1), 1.0)
    assert frozen["p3a_r"][0].stats["operation_counts"] == {"cx": 18, "rz": 42, "sx": 28}


def test_wrong_registered_hash_is_refused(setup):
    resolved, study, _ = setup
    bad = study.models[0].model_copy(update={"artifact_sha256": "0" * 64})
    with pytest.raises(RuntimeError, match="registered"):
        load_frozen(ROOT, bad, resolved.vqc)


def test_gate_noise_contracts_parity_and_keeps_distributions_normalized(frozen, setup):
    _, _, profiles = setup
    fc, frame = frozen["p3a_r"]
    v = fc.values(frame)
    clean = D.parity_z(exact_distributions(fc.transpiled, v, None))
    noisy_p = exact_distributions(fc.transpiled, v, gate_noise_model(profiles["dep-high"], BASIS))
    assert np.allclose(noisy_p.sum(axis=1), 1.0)
    assert np.mean(np.abs(D.parity_z(noisy_p))) < np.mean(np.abs(clean))


# ------------------------------------------------------------------- negative control


def test_symmetric_readout_is_exact_affine_contraction(frozen):
    fc, frame = frozen["p3a_r"]
    probs = exact_distributions(fc.transpiled, fc.values(frame), None)
    y = np.zeros(len(frame), dtype=int)
    y[:6] = 1
    z = D.parity_z(probs)
    for p in (0.005, 0.02, 0.05):
        nc = D.negative_control(y, z, D.parity_z(apply_readout(probs, p, p)), p, 4)
        assert nc["passed"] and nc["max_abs_affine_residual"] <= 1e-12
    asym = D.negative_control(y, z, D.parity_z(apply_readout(probs, 0.025, 0.075)), 0.05, 4)
    assert not asym["passed"]


# ------------------------------------------------------------------------- statistics


def test_weighted_ece_equals_unweighted_on_materialized_resample():
    rng = np.random.default_rng(3)
    y = (rng.random(400) < 0.1).astype(int)
    s = np.clip(rng.random(400) * 0.6 + 0.2 * y, 0, 1)
    w = next(stratified_weights(y, 1, 5))
    idx = np.repeat(np.arange(len(y)), w.astype(int))
    assert M.expected_calibration_error_weighted(y, s, w) == pytest.approx(
        M.expected_calibration_error(y[idx], s[idx]), abs=1e-12
    )
    assert M.expected_calibration_error_weighted(y, s, np.ones(len(y))) == pytest.approx(
        M.expected_calibration_error(y, s), abs=1e-12
    )


def test_paired_bootstrap_identical_scores_gives_zero_deltas():
    rng = np.random.default_rng(4)
    y = np.zeros(300, dtype=int)
    y[:12] = 1
    s = rng.random(300)
    out = D.paired_bootstrap(y, s, {"same": s.copy(), "noisy": s * 0.5}, 50, 9, 10, n_jobs=1)
    for m in D.BOOT_METRICS:
        assert out["same"][f"delta_{m}"] == (0.0, 0.0)
    assert out["noisy"]["delta_auprc"] == (0.0, 0.0)  # monotone rescale keeps the ranking
    again = D.paired_bootstrap(y, s, {"noisy": s * 0.5}, 50, 9, 10, n_jobs=1)
    assert again["noisy"] == out["noisy"]


def _metrics(rho=1.0, kendall=1.0, top=1.0, d_brier=0.0, d_ece=0.0, cross=0.0, fcross=0.0):
    return {
        "spearman": rho,
        "kendall": kendall,
        "top47_overlap": top,
        "delta_brier": d_brier,
        "delta_ece": d_ece,
        "crossing_fraction": cross,
        "fraud_crossing_rate": fcross,
    }


def _ci(auprc=(-0.01, 0.01), auroc=(-0.01, 0.01), brier=(-0.01, 0.01), ece=(-0.01, 0.01)):
    return {"delta_auprc": auprc, "delta_auroc": auroc, "delta_brier": brier, "delta_ece": ece}


def test_a13_label_rules_follow_registration():
    lab = D.a13_labels(_metrics(), _ci(), 0.01, RULES)
    assert lab["ranking_preserving"] and not any(
        v for k, v in lab.items() if k != "ranking_preserving"
    )
    lab = D.a13_labels(_metrics(top=0.94), _ci(), 0.01, RULES)
    assert lab["ranking_distortion"] and lab["ranking_preserving"]  # multi-label by design
    lab = D.a13_labels(_metrics(rho=0.998), _ci(auprc=(-0.05, -0.001)), 0.01, RULES)
    assert lab["discrimination_degradation"] and lab["ranking_distortion"]
    lab = D.a13_labels(_metrics(rho=0.9995), _ci(auprc=(-0.05, -0.001)), 0.01, RULES)
    assert not lab["discrimination_degradation"]  # needs Spearman < 0.999
    lab = D.a13_labels(_metrics(d_brier=0.002), _ci(brier=(0.001, 0.003)), 0.01, RULES)
    assert lab["calibration_distortion"]
    lab = D.a13_labels(_metrics(d_brier=0.002), _ci(brier=(-0.001, 0.003)), 0.01, RULES)
    assert not lab["calibration_distortion"]  # CI contains 0
    lab = D.a13_labels(_metrics(d_ece=0.011), _ci(ece=(0.005, 0.02)), 0.01, RULES)
    assert lab["calibration_distortion"]
    lab = D.a13_labels(_metrics(rho=0.98, d_ece=0.05), _ci(ece=(0.01, 0.09)), 0.01, RULES)
    assert not lab["calibration_distortion"] and not lab["threshold_distortion"]
    assert D.a13_labels(_metrics(cross=0.01), _ci(), 0.01, RULES)["threshold_distortion"]
    assert D.a13_labels(_metrics(fcross=0.05), _ci(), 0.01, RULES)["threshold_distortion"]
    assert not D.a13_labels(_metrics(cross=0.009, fcross=0.04), _ci(), 0.01, RULES)[
        "threshold_distortion"
    ]


def _cond(cid, fam, sev, labels=(), top=1.0, d=0.0, rho=1.0, role="anchor"):
    lab = {k: k in labels for k in D.LABELS}
    return {
        "condition": cid,
        "g1_family": fam,
        "severity": sev,
        "role": role,
        "labels": lab,
        "top47_overlap": top,
        "delta_auprc": d,
        "spearman": rho,
    }


def _family(fam, labels_high=(), d=(0.0, -0.01, -0.02), rho=(1.0, 0.999, 0.99), top_high=1.0):
    return [
        _cond(f"{fam}-low", fam, "low", d=d[0], rho=rho[0]),
        _cond(f"{fam}-medium", fam, "medium", d=d[1], rho=rho[1]),
        _cond(f"{fam}-high", fam, "high", labels_high, top_high, d[2], rho[2]),
    ]


def test_g1_pass_conditional_fail():
    nc = _cond("ro-sym-high", "nc", "high", ("threshold_distortion",), role="negative_control")
    g = D.g1_verdict([*_family("dep", ("discrimination_degradation",)), nc], RULES)
    assert g["verdict"] == "PASS" and g["pass_qualifying_conditions"] == ["dep-high"]
    # ranking distortion qualifies for PASS only through the top-47 criterion
    g = D.g1_verdict(_family("th", ("ranking_distortion",), top_high=0.93), RULES)
    assert g["verdict"] == "PASS"
    g = D.g1_verdict(_family("th", ("ranking_distortion",), top_high=0.97), RULES)
    assert g["verdict"] == "CONDITIONAL PASS"
    # no severity trend in either measure: degradation alone cannot PASS
    rows = _family(
        "dep",
        ("discrimination_degradation", "ranking_distortion"),
        d=(-0.02, 0.0, -0.01),
        rho=(0.99, 1.0, 0.995),
    )
    assert D.g1_verdict(rows, RULES)["verdict"] == "CONDITIONAL PASS"
    # negative controls never count
    assert D.g1_verdict([*_family("dep"), nc], RULES)["verdict"] == "FAIL"
    assert D.g1_verdict(_family("dep"), RULES)["excluded_negative_controls"] == []


def test_severity_trend_tolerance():
    assert D.non_increasing([0.0, 0.0, -1e-10])
    assert D.non_increasing([0.0, 5e-10, 0.0])
    assert not D.non_increasing([0.0, -0.01, 0.0])


# ------------------------------------------------------------------- sampler and E08


def test_sampler_counts_and_scores():
    rng = np.random.default_rng(2)
    probs = rng.dirichlet(np.ones(16), size=200)
    probs[0, 0] -= 1e-17  # simulator round-off
    counts = S.sample_counts(probs, 1024, np.random.default_rng(5))
    assert counts.shape == (200, 16) and (counts.sum(axis=1) == 1024).all()
    again = S.sample_counts(probs, 1024, np.random.default_rng(5))
    assert (counts == again).all()
    odd = (D.parity_z(np.eye(16)) < 0).astype(float)
    assert np.allclose(S.counts_score(counts, 1024), counts @ odd / 1024)
    big = S.sample_counts(probs, 10**7, np.random.default_rng(6))
    assert np.allclose(S.counts_score(big, 10**7), D.fraud_score(probs), atol=2e-3)


def test_merged_chi2_hand_case():
    probs = np.array([[0.5, 0.49, 0.006, 0.004]])  # expected 512, 501.76, 6.14, 4.10
    counts = np.array([[512, 502, 6, 4]])
    stat, dof, p = S.merged_chi2(counts, probs, 1024, 5.0)
    assert dof == 2  # the 4.10 bin merges with the 6.14 bin: three groups
    assert p > 0.9


def _e08_cfg(setup):
    return setup[1].e08


def test_e08_passes_for_two_independent_multinomial_samplers(setup):
    rng = np.random.default_rng(8)
    probs = rng.dirichlet(np.ones(16) * 0.7, size=256)
    a = S.sample_counts(probs, 1024, np.random.default_rng(1))
    b = S.sample_counts(probs, 1024, np.random.default_rng(2))
    res = S.e08_tests(probs, a, b, 1024, _e08_cfg(setup))
    assert res["passed"], res


def test_e08_fails_for_a_biased_sampler(setup):
    rng = np.random.default_rng(8)
    probs = rng.dirichlet(np.ones(16) * 0.7, size=256)
    biased = apply_readout(probs, 0.03, 0.03)  # a sampler that ignores/doubles readout
    a = S.sample_counts(biased, 1024, np.random.default_rng(1))
    b = S.sample_counts(probs, 1024, np.random.default_rng(2))
    res = S.e08_tests(probs, a, b, 1024, _e08_cfg(setup))
    assert not res["passed"] and not res["pass_chi2"]


def test_direct_aer_shots_agree_with_cached_sampler_on_synthetic_rows(frozen, setup):
    _, study, profiles = setup
    fc, frame = frozen["p3a_r"]
    p = profiles["comb-high"]
    v = fc.values(frame)
    exact = apply_readout(
        exact_distributions(fc.transpiled, v, gate_noise_model(p, BASIS)),
        p.readout_p01,
        p.readout_p10,
    )
    aer = S.direct_aer_counts(
        fc.transpiled, v, gate_noise_model(p, BASIS, include_readout=True), 1024, 17
    )
    assert (aer.sum(axis=1) == 1024).all()
    _, _, pval = S.merged_chi2(aer, exact, 1024, 5.0)
    assert pval > 1e-3
    again = S.direct_aer_counts(
        fc.transpiled, v, gate_noise_model(p, BASIS, include_readout=True), 1024, 17
    )
    assert (aer == again).all()  # seeded direct execution is reproducible


def test_clean_profile_is_noise_free():
    assert CLEAN.profile_id == "clean" and not has_gate_noise(CLEAN) and not CLEAN.has_readout
    assert isinstance(CLEAN, NoiseProfile)


def test_experiment_hash_and_registered_models(setup):
    resolved, study, _ = setup
    assert load_experiment("phase3b_noise").spec.protocol_version == "0.8"
    roles = {m.model_id: m.role for m in study.models}
    assert roles == {"p3a_r": "primary", "p3a_original": "exploratory_contrast"}
    assert study.finite_shot.models == ("p3a_r",)
    assert resolved.config_hash()
