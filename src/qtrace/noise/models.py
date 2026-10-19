"""Pre-registered noise construction on transpiled circuits (Phase 3B; PREREG_P3B §4).

One-qubit gates (sx, x): depolarizing_error(p1, 1) then thermal_relaxation(T1, T2, t_1q).
Two-qubit gates (cx): depolarizing_error(p2, 2) then thermal(t_2q) (x) thermal(t_2q).
rz is virtual and noiseless. Readout: an identical per-qubit confusion matrix
[[1-p01, p01], [p10, 1-p10]] (rows = prepared, columns = read), applied classically
to exact distributions, or as Aer ReadoutError for direct shot execution.
"""

from __future__ import annotations

import numpy as np
from qiskit_aer.noise import NoiseModel, ReadoutError, depolarizing_error, thermal_relaxation_error

from qtrace.config.schemas import NoiseProfile


def has_gate_noise(profile: NoiseProfile) -> bool:
    return profile.has_depolarizing or profile.thermal is not None


def gate_noise_model(
    profile: NoiseProfile,
    basis_gates: tuple[str, ...],
    one_qubit: tuple[str, ...] = ("sx", "x"),
    two_qubit: tuple[str, ...] = ("cx",),
    include_readout: bool = False,
) -> NoiseModel:
    model = NoiseModel(basis_gates=list(basis_gates))
    e1 = e2 = None
    if profile.p1 > 0:
        e1 = depolarizing_error(profile.p1, 1)
    if profile.p2 > 0:
        e2 = depolarizing_error(profile.p2, 2)
    if profile.thermal is not None:
        t1, t2 = profile.thermal.t1_us * 1e-6, profile.thermal.t2_us * 1e-6
        r1 = thermal_relaxation_error(t1, t2, profile.gate_time_1q_ns * 1e-9)
        r2_single = thermal_relaxation_error(t1, t2, profile.gate_time_2q_ns * 1e-9)
        r2 = r2_single.tensor(r2_single)
        e1 = r1 if e1 is None else e1.compose(r1)
        e2 = r2 if e2 is None else e2.compose(r2)
    if e1 is not None:
        model.add_all_qubit_quantum_error(e1, [g for g in one_qubit if g in basis_gates])
    if e2 is not None:
        model.add_all_qubit_quantum_error(e2, [g for g in two_qubit if g in basis_gates])
    if include_readout and profile.has_readout:
        p01, p10 = profile.readout_p01, profile.readout_p10
        model.add_all_qubit_readout_error(ReadoutError([[1 - p01, p01], [p10, 1 - p10]]))
    return model


def apply_readout(probs: np.ndarray, p01: float, p10: float) -> np.ndarray:
    """Apply the per-qubit confusion to rows of 2^n probability vectors (any row count)."""
    probs = np.atleast_2d(probs)
    n = int(np.log2(probs.shape[1]))
    confusion = np.array([[1 - p01, p10], [p01, 1 - p10]])  # [read, prepared]
    tensor = probs.reshape((len(probs),) + (2,) * n)
    for axis in range(1, n + 1):
        tensor = np.moveaxis(np.tensordot(confusion, tensor, axes=([1], [axis])), 0, axis)
    return tensor.reshape(len(probs), -1)


def effective_configuration(profile: NoiseProfile, cfg) -> dict:
    """Complete effective noise configuration persisted for every condition."""
    return {
        "profile_id": profile.profile_id,
        "family": profile.family,
        "severity": profile.severity,
        "role": profile.role,
        "synthetic": profile.role == "synthetic_stress",
        "p1_depolarizing_param": profile.p1,
        "p2_depolarizing_param": profile.p2,
        "readout_p01": profile.readout_p01,
        "readout_p10": profile.readout_p10,
        "t1_us": profile.thermal.t1_us if profile.thermal else None,
        "t2_us": profile.thermal.t2_us if profile.thermal else None,
        "gate_time_1q_ns": profile.gate_time_1q_ns,
        "gate_time_2q_ns": profile.gate_time_2q_ns,
        "one_qubit_noisy_gates": "|".join(cfg.one_qubit_noisy_gates),
        "two_qubit_noisy_gates": "|".join(cfg.two_qubit_noisy_gates),
        "composition": cfg.gate_error_composition,
        "readout_application": cfg.readout_application,
        "rz_noise": "none (virtual)",
        "idle_noise": "not modelled",
    }
