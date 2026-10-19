"""Phase 4 mitigation primitives on synthetic inputs: readout calibration/inversion/projection,
global folding (ideal unitary, gate growth, noise exposure, independent engine), extrapolation,
clean ZNE and resource accounting. No transaction data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
from qiskit.quantum_info import DensityMatrix, Operator, SuperOp
from qiskit_aer.noise import depolarizing_error, thermal_relaxation_error
from scipy.optimize import minimize

from qtrace.config import repo_root
from qtrace.mitigation import readout as RO
from qtrace.mitigation import zne as Z
from qtrace.mitigation.costs import action_costs, resource_matched_comparator
from qtrace.noise.diagnostics import parity_z
from qtrace.noise.exact import exact_distributions
from qtrace.noise.frozen import load_frozen
from qtrace.noise.models import apply_readout, gate_noise_model
from qtrace.noise.shots import sample_counts
from qtrace.noise.study import load_study

ROOT = repo_root()
BASIS = ("rz", "sx", "x", "cx")
SEED = 1154577741


@pytest.fixture(scope="module")
def setup():
    resolved, study, profiles = load_study()
    fc = load_frozen(ROOT, study.models[0], resolved.vqc)
    rng = np.random.default_rng(11)
    frame = pd.DataFrame(rng.normal(0, 3, size=(48, 4)), columns=["V17", "V14", "V12", "V10"])
    return fc, fc.values(frame), {p.profile_id: p for p in profiles}


# ------------------------------------------------------------------------ readout


def _kron(mats):
    out = np.ones((1, 1))
    for m in mats[::-1]:  # qubit n-1 is the most significant factor
        out = np.kron(out, m)
    return out


def test_per_qubit_application_matches_kronecker_and_identical_case():
    rng = np.random.default_rng(1)
    probs = rng.dirichlet(np.ones(16), size=7)
    cal = RO.ReadoutCalibration(
        np.array([0.01, 0.02, 0.03, 0.04]), np.array([0.05, 0.0, 0.1, 0.07])
    )
    mats = cal.matrices()
    assert np.allclose(RO.apply_per_qubit(probs, mats), probs @ _kron(mats).T, atol=1e-15)
    same = RO.ReadoutCalibration(np.full(4, 0.025), np.full(4, 0.075))
    assert np.allclose(
        RO.apply_per_qubit(probs, same.matrices()), apply_readout(probs, 0.025, 0.075)
    )


def test_bit_order_qubit0_is_least_significant_bit():
    dist = np.zeros(16)
    dist[0b0001] = 1.0
    assert list(RO.bit_one_marginals(dist)) == [1.0, 0.0, 0.0, 0.0]


def test_calibration_estimates_and_exact_inversion():
    zeros, ones = RO.calibration_circuits(4)
    assert zeros.size() == 0 and dict(ones.count_ops()) == {"x": 4}
    truth = RO.ReadoutCalibration(
        np.array([0.01, 0.02, 0.03, 0.04]), np.array([0.05, 0.06, 0.1, 0.07])
    )
    e0, e1 = np.zeros((1, 16)), np.zeros((1, 16))
    e0[0, 0], e1[0, 15] = 1.0, 1.0
    cal0 = RO.apply_per_qubit(e0, truth.matrices())[0]
    cal1 = RO.apply_per_qubit(e1, truth.matrices())[0]
    est = RO.estimate_calibration(cal0, cal1)
    assert np.allclose(est.p01, truth.p01) and np.allclose(est.p10, truth.p10)
    probs = np.random.default_rng(2).dirichlet(np.ones(16), size=9)
    noisy = RO.apply_per_qubit(probs, truth.matrices())
    rec, diag = RO.mitigate(noisy, est)
    assert np.allclose(rec, probs, atol=1e-13) and diag.rows_projected == 0 and not diag.unstable


def test_calibration_estimates_converge_with_shots():
    truth = RO.ReadoutCalibration(np.full(4, 0.025), np.full(4, 0.075))
    e0, e1 = np.zeros((1, 16)), np.zeros((1, 16))
    e0[0, 0], e1[0, 15] = 1.0, 1.0
    p0 = RO.apply_per_qubit(e0, truth.matrices())
    p1 = RO.apply_per_qubit(e1, truth.matrices())
    rng = np.random.default_rng(3)
    est = RO.estimate_calibration(
        sample_counts(p0, 10**7, rng)[0], sample_counts(p1, 10**7, rng)[0]
    )
    assert np.allclose(est.p01, 0.025, atol=3e-4) and np.allclose(est.p10, 0.075, atol=3e-4)


def test_simplex_projection_valid_idempotent_and_optimal():
    rng = np.random.default_rng(4)
    valid = rng.dirichlet(np.ones(16), size=5)
    assert np.array_equal(
        RO.project_simplex(valid)[valid > 0] > 0, np.ones((valid > 0).sum(), bool)
    )
    assert np.allclose(RO.project_simplex(valid), valid, atol=1e-15)
    quasi = valid + rng.normal(0, 0.05, size=valid.shape)
    quasi -= (quasi.sum(axis=1, keepdims=True) - 1) / 16
    proj = RO.project_simplex(quasi)
    assert (proj >= 0).all() and np.allclose(proj.sum(axis=1), 1.0)
    for q, p in zip(quasi, proj, strict=True):
        res = minimize(
            lambda v, q=q: np.sum((v - q) ** 2),
            np.full(16, 1 / 16),
            constraints=[{"type": "eq", "fun": lambda v: v.sum() - 1}],
            bounds=[(0, 1)] * 16,
            method="SLSQP",
            options={"ftol": 1e-14, "maxiter": 500},
        )
        assert np.allclose(res.x, p, atol=1e-5)


def test_mitigation_projects_negative_rows_and_flags_instability():
    est = RO.ReadoutCalibration(np.full(4, 0.05), np.full(4, 0.05))
    counts = np.zeros((1, 16))
    counts[0, 0] = 1.0  # a pure outcome: inversion overshoots -> negative entries
    out, diag = RO.mitigate(counts, est)
    assert diag.rows_projected == 1 and (out >= 0).all() and np.isclose(out.sum(), 1.0)
    bad = RO.ReadoutCalibration(np.full(4, 0.3), np.full(4, 0.3))
    assert RO.mitigate(counts, bad, 0.5)[1].unstable


# ------------------------------------------------------------------------ folding


def test_factor_one_is_the_original_circuit(setup):
    fc, _, _ = setup
    assert Z.fold_global(fc.transpiled, 1, BASIS, SEED) == fc.transpiled


def test_folding_preserves_the_ideal_unitary_and_scales_noisy_gates(setup):
    fc, _, _ = setup
    tc = fc.transpiled
    base = Z.circuit_statistics(tc)
    rng = np.random.default_rng(5)
    for factor in (3, 5):
        folded = Z.fold_global(tc, factor, BASIS, SEED)
        st = Z.circuit_statistics(folded)
        assert st["cx"] == factor * base["cx"] and st["noisy_1q"] == factor * base["noisy_1q"]
        assert st["depth"] > base["depth"] and st["noisy_depth"] > base["noisy_depth"]
        for _ in range(3):
            bind = dict(
                zip(tc.parameters, rng.uniform(-np.pi, np.pi, len(tc.parameters)), strict=True)
            )
            assert Operator(folded.assign_parameters(bind)).equiv(
                Operator(tc.assign_parameters(bind))
            )
    assert (base["cx"], base["noisy_1q"]) == (18, 28)


def test_noiseless_folded_distributions_equal_unfolded(setup):
    fc, values, _ = setup
    ref = exact_distributions(fc.transpiled, values, None)
    for factor in (3, 5):
        got = exact_distributions(Z.fold_global(fc.transpiled, factor, BASIS, SEED), values, None)
        assert np.max(np.abs(got - ref)) <= 1e-10


def test_noise_exposure_increases_with_scale(setup):
    fc, values, profiles = setup
    for pid in ("dep-high", "th-high", "comb-high"):
        model = gate_noise_model(profiles[pid], BASIS)
        mean_abs = [
            np.abs(
                parity_z(
                    exact_distributions(Z.fold_global(fc.transpiled, f, BASIS, SEED), values, model)
                )
            ).mean()
            for f in (1, 3, 5)
        ]
        assert mean_abs[0] > mean_abs[1] > mean_abs[2], pid


def test_independent_channel_engine_equals_aer_for_noisy_folded_circuit(setup):
    fc, values, profiles = setup
    p = profiles["comb-high"]
    folded = Z.fold_global(fc.transpiled, 3, BASIS, SEED)
    aer = exact_distributions(folded, values[:2], gate_noise_model(p, BASIS))
    t1, t2 = p.thermal.t1_us * 1e-6, p.thermal.t2_us * 1e-6
    th1 = thermal_relaxation_error(t1, t2, 35e-9)
    th2 = thermal_relaxation_error(t1, t2, 300e-9)
    e1 = SuperOp(depolarizing_error(p.p1, 1).compose(th1))
    e2 = SuperOp(depolarizing_error(p.p2, 2).compose(th2.tensor(th2)))
    params = list(folded.parameters)
    for row, want in zip(values[:2], aer, strict=True):
        bound = folded.assign_parameters(dict(zip(params, row, strict=True)))
        rho = DensityMatrix.from_label("0000")
        for inst in bound.data:
            qargs = [bound.find_bit(q).index for q in inst.qubits]
            rho = rho.evolve(Operator(inst.operation), qargs)
            if inst.operation.name in ("sx", "x"):
                rho = rho.evolve(e1, qargs)
            elif inst.operation.name == "cx":
                rho = rho.evolve(e2, qargs)
        assert np.max(np.abs(rho.probabilities() - want)) <= 1e-10


# --------------------------------------------------------------------- extrapolation


def test_extrapolation_weights_and_exactness():
    f = (1, 3, 5)
    lin = Z.extrapolation_weights(f, "linear_least_squares")
    ric = Z.extrapolation_weights(f, "richardson")
    assert np.allclose(lin, [13 / 12, 1 / 3, -5 / 12]) and np.allclose(ric, [15 / 8, -5 / 4, 3 / 8])
    assert np.isclose(lin.sum(), 1) and np.isclose(ric.sum(), 1)
    x = np.array(f, float)[:, None]
    assert np.allclose(Z.extrapolate(0.4 - 0.05 * x * np.ones((3, 6)), lin, clip=False)[0], 0.4)
    assert np.allclose(
        Z.extrapolate(0.3 - 0.04 * x + 0.003 * x**2 + 0 * np.ones((3, 6)), ric, clip=False)[0], 0.3
    )
    const = np.tile(np.linspace(-0.9, 0.9, 5), (3, 1))
    assert np.allclose(Z.extrapolate(const, lin)[0], const[0]) and np.allclose(
        Z.extrapolate(const, ric)[0], const[0]
    )
    z0, frac = Z.extrapolate(np.array([[0.99], [0.5], [0.1]]), ric)
    assert z0[0] == 1.0 and frac == 1.0


def test_clean_zne_finite_shot_has_no_systematic_gain():
    rng = np.random.default_rng(6)
    probs = rng.dirichlet(np.ones(16), size=4000)
    z_true = parity_z(probs)
    w = Z.extrapolation_weights((1, 3, 5), "linear_least_squares")
    zs = np.array([parity_z(sample_counts(probs, 1024, rng) / 1024) for _ in range(3)])
    z0, _ = Z.extrapolate(zs, w)
    assert abs(np.mean(z0 - z_true)) < 3 * np.sqrt(1.458 / 1024 / 4000) * 1.5
    assert np.var(z0 - z_true) > np.var(zs[0] - z_true)  # more variance, no free lunch


# --------------------------------------------------------------------------- costs


def test_resource_accounting_by_hand(setup):
    fc, _, _ = setup
    folded = {
        f: Z.circuit_statistics(Z.fold_global(fc.transpiled, f, BASIS, SEED)) for f in (1, 3, 5)
    }
    cal = tuple(Z.circuit_statistics(c) for c in RO.calibration_circuits(4))
    s, n = 1024, 10
    a0 = action_costs("A0", s, n, folded, cal)
    a1 = action_costs("A1", s, n, folded, cal)
    a2 = action_costs("A2", s, n, folded, cal)
    a3 = action_costs("A3", s, n, folded, cal)
    rm3, rm9 = action_costs("RM3", s, n, folded, cal), action_costs("RM9", s, n, folded, cal)
    assert (a0["total_shots"], a0["total_circuit_executions"], a0["cx_shots"]) == (
        10240,
        10,
        18 * 10240,
    )
    assert a1["calibration_circuit_executions"] == 2 and a1["total_shots"] == 10240 + 2048
    assert (
        a1["cx_shots"] == a0["cx_shots"] and a1["noisy_1q_shots"] == a0["noisy_1q_shots"] + 4 * 1024
    )
    assert a2["total_shots"] == 3 * 10240 and a2["total_circuit_executions"] == 30
    assert a2["cx_shots"] == (18 + 54 + 90) * 10240
    assert a3["total_shots"] == a2["total_shots"] + 2048
    assert rm3["total_shots"] == a2["total_shots"] and rm3["total_circuit_executions"] == 10
    assert rm9["cx_shots"] == a2["cx_shots"]  # RM9 is two-qubit-exposure matched
    big = action_costs("A1", s, 28372, folded, cal)
    assert big["total_shots"] // 28372 == s  # A1's shot-matched comparator is A0 (PREREG §5)
    assert {resource_matched_comparator(a) for a in ("A1", "A2", "A3")} == {"A0", "RM3"}
