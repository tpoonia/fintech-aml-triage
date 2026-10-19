"""Phase 0 environment smoke test: a 4-qubit density-matrix simulation with noise.

This only proves the pinned Qiskit/Aer stack works on the current machine and
that the configured noise has a measurable, reproducible effect. The minimal
noise-model builder below is NOT the Phase 4 noise engine. No dataset is read
and no model is trained: the VQC-shaped circuit uses fixed, untrained angles
only to confirm the circuit-library functions exist and transpile.
"""

from __future__ import annotations

import time
from typing import Any

import numpy as np
from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import real_amplitudes, zz_feature_map
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, thermal_relaxation_error

from qtrace.config.schemas import NoiseProfile

N_QUBITS = 4


def build_smoke_noise_model(profile: NoiseProfile, basis_gates: tuple[str, ...]) -> NoiseModel:
    """Depolarizing + thermal gate noise and (possibly asymmetric) readout error."""
    model = NoiseModel(basis_gates=list(basis_gates))
    one_q = [g for g in ("sx", "x") if g in basis_gates]  # rz is virtual and noiseless (E09)
    error_1q = error_2q = None
    if profile.p1 > 0:
        error_1q = depolarizing_error(profile.p1, 1)
    if profile.p2 > 0:
        error_2q = depolarizing_error(profile.p2, 2)
    if profile.thermal is not None:
        t1 = profile.thermal.t1_us * 1e-6
        t2 = profile.thermal.t2_us * 1e-6
        relax_1q = thermal_relaxation_error(t1, t2, profile.gate_time_1q_ns * 1e-9)
        relax_2q_single = thermal_relaxation_error(t1, t2, profile.gate_time_2q_ns * 1e-9)
        relax_2q = relax_2q_single.tensor(relax_2q_single)
        error_1q = relax_1q if error_1q is None else error_1q.compose(relax_1q)
        error_2q = relax_2q if error_2q is None else error_2q.compose(relax_2q)
    if error_1q is not None:
        model.add_all_qubit_quantum_error(error_1q, one_q)
    if error_2q is not None:
        model.add_all_qubit_quantum_error(error_2q, ["cx"])
    if profile.has_readout:
        p01, p10 = profile.readout_p01, profile.readout_p10
        model.add_all_qubit_readout_error(ReadoutError([[1 - p01, p01], [p10, 1 - p10]]))
    return model


def ghz_circuit(n: int = N_QUBITS) -> QuantumCircuit:
    qc = QuantumCircuit(n)
    qc.h(0)
    for q in range(n - 1):
        qc.cx(q, q + 1)
    return qc


def vqc_shaped_circuit(n: int = N_QUBITS) -> QuantumCircuit:
    """Feature map + ansatz with fixed untrained angles (library availability check only)."""
    circuit = zz_feature_map(n, reps=1).compose(real_amplitudes(n, reps=1))
    values = np.linspace(0.1, 1.0, circuit.num_parameters)
    return circuit.assign_parameters(values)


def apply_readout_confusion(probs: np.ndarray, p01: float, p10: float) -> np.ndarray:
    """Apply an identical per-qubit confusion matrix to a 2^n probability vector."""
    n = int(np.log2(probs.size))
    confusion = np.array([[1 - p01, p10], [p01, 1 - p10]])  # [measured, prepared]
    tensor = probs.reshape((2,) * n)
    for axis in range(n):
        tensor = np.moveaxis(np.tensordot(confusion, tensor, axes=([1], [axis])), 0, axis)
    return tensor.reshape(-1)


def _counts_vector(counts: dict[str, int], n: int) -> np.ndarray:
    vec = np.zeros(2**n)
    for bitstring, count in counts.items():
        vec[int(bitstring.replace(" ", ""), 2)] += count
    return vec


def run_smoke_test(
    profile: NoiseProfile,
    *,
    shots: int,
    seed: int,
    basis_gates: tuple[str, ...] = ("rz", "sx", "x", "cx"),
    optimization_level: int = 1,
) -> dict[str, Any]:
    start = time.perf_counter()
    n = N_QUBITS
    noise_model = build_smoke_noise_model(profile, basis_gates)
    ideal_sim = AerSimulator(method="density_matrix")
    noisy_sim = AerSimulator(method="density_matrix", noise_model=noise_model)

    ghz = transpile(
        ghz_circuit(n),
        basis_gates=list(basis_gates),
        optimization_level=optimization_level,
        seed_transpiler=seed % (2**31),
    )

    exact = ghz.copy()
    exact.save_probabilities()
    ideal_probs = np.asarray(ideal_sim.run(exact).result().data(0)["probabilities"])
    noisy_probs = np.asarray(noisy_sim.run(exact).result().data(0)["probabilities"])

    measured = ghz.copy()
    measured.measure_all()
    sim_seed = seed % (2**31)
    counts_a = noisy_sim.run(measured, shots=shots, seed_simulator=sim_seed).result().get_counts()
    counts_b = noisy_sim.run(measured, shots=shots, seed_simulator=sim_seed).result().get_counts()
    counts_c = (
        noisy_sim.run(measured, shots=shots, seed_simulator=sim_seed + 1).result().get_counts()
    )

    # Readout-only check: measuring |0000> exposes only P(read 1 | prepared 0) = p01.
    blank = QuantumCircuit(n)
    blank.measure_all()
    blank_counts = noisy_sim.run(blank, shots=shots, seed_simulator=sim_seed).result().get_counts()
    ones_per_qubit = np.zeros(n)
    for bitstring, count in blank_counts.items():
        bits = bitstring.replace(" ", "")[::-1]  # qubit 0 first
        ones_per_qubit += count * np.array([int(b) for b in bits])
    p01_hat = ones_per_qubit.sum() / (shots * n)
    p01_sigma = np.sqrt(max(profile.readout_p01 * (1 - profile.readout_p01), 1e-12) / (shots * n))

    expected_sampled = apply_readout_confusion(
        noisy_probs, profile.readout_p01, profile.readout_p10
    )
    empirical = _counts_vector(counts_a, n) / shots
    tvd = 0.5 * float(np.abs(empirical - expected_sampled).sum())

    vqc = transpile(
        vqc_shaped_circuit(n),
        basis_gates=list(basis_gates),
        optimization_level=optimization_level,
        seed_transpiler=seed % (2**31),
    )
    vqc_ops = dict(vqc.count_ops())
    allowed = set(basis_gates) | {"barrier", "measure"}

    ghz_index = [0, 2**n - 1]
    checks = {
        "noiseless_ghz_exact": bool(
            np.allclose(ideal_probs[ghz_index], 0.5, atol=1e-9)
            and np.isclose(ideal_probs.sum(), 1.0, atol=1e-9)
        ),
        "noisy_distribution_normalized": bool(
            np.isclose(noisy_probs.sum(), 1.0, atol=1e-9) and noisy_probs.min() > -1e-12
        ),
        "noise_has_measurable_effect": bool(noisy_probs[ghz_index].sum() < 1 - 1e-4),
        "seeded_counts_reproducible": counts_a == counts_b,
        "different_seed_changes_counts": counts_a != counts_c,
        "asymmetric_readout_p01_recovered": bool(
            abs(p01_hat - profile.readout_p01) < 5 * p01_sigma
        ),
        "sampled_matches_exact_with_classical_readout": tvd < 0.05,
        "vqc_shaped_circuit_in_basis": set(vqc_ops) <= allowed,
    }
    return {
        "n_qubits": n,
        "shots": shots,
        "seed_simulator": sim_seed,
        "noise_profile_id": profile.profile_id,
        "ghz_ops": dict(ghz.count_ops()),
        "vqc_shaped_ops": vqc_ops,
        "vqc_shaped_depth": vqc.depth(),
        "ideal_ghz_population": float(ideal_probs[ghz_index].sum()),
        "noisy_ghz_population_exact": float(noisy_probs[ghz_index].sum()),
        "readout_p01_configured": profile.readout_p01,
        "readout_p01_estimated": float(p01_hat),
        "tvd_sampled_vs_exact": tvd,
        "checks": checks,
        "passed": all(checks.values()),
        "wall_seconds": time.perf_counter() - start,
    }
