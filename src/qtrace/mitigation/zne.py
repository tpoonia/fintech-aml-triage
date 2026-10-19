"""Zero-noise extrapolation by global unitary folding of the transpiled circuit (E10; PREREG_P4 §8).

folded(lambda) = U (U^-1 U)^k with lambda = 2k + 1. U^-1 is ``U.inverse()`` translated
to the basis at optimization level 0; the composite is never re-transpiled, so no
fold can be cancelled. Extrapolation acts on per-transaction parity expectations.
"""

from __future__ import annotations

import hashlib

import numpy as np
from qiskit import QuantumCircuit, qasm3, transpile

NOISY_1Q = ("sx", "x")
TWO_Q = ("cx",)


def inverse_in_basis(circuit: QuantumCircuit, basis_gates, seed: int) -> QuantumCircuit:
    return transpile(
        circuit.inverse(),
        basis_gates=list(basis_gates),
        optimization_level=0,
        seed_transpiler=seed,
    )


def fold_global(circuit: QuantumCircuit, factor: int, basis_gates, seed: int) -> QuantumCircuit:
    if factor < 1 or factor % 2 == 0:
        raise ValueError("global folding needs an odd factor >= 1")
    folded = circuit.copy()
    if factor > 1:
        inverse = inverse_in_basis(circuit, basis_gates, seed)
        for _ in range((factor - 1) // 2):
            folded = folded.compose(inverse).compose(circuit)
    if set(folded.parameters) != set(circuit.parameters):
        raise RuntimeError("folding changed the circuit parameters")
    return folded


def circuit_statistics(circuit: QuantumCircuit) -> dict:
    ops = {k: int(v) for k, v in sorted(circuit.count_ops().items())}
    return {
        "operation_counts": ops,
        "cx": sum(ops.get(g, 0) for g in TWO_Q),
        "noisy_1q": sum(ops.get(g, 0) for g in NOISY_1Q),
        "rz": ops.get("rz", 0),
        "depth": circuit.depth(),
        "noisy_depth": circuit.depth(filter_function=lambda ci: ci.operation.name != "rz"),
        "qasm3_sha256": hashlib.sha256(qasm3.dumps(circuit).encode()).hexdigest(),
    }


def extrapolation_weights(factors, kind: str) -> np.ndarray:
    """Weights w with z(0) = sum_i w_i z(factor_i)."""
    x = np.asarray(factors, dtype=np.float64)
    if kind == "linear_least_squares":
        design = np.column_stack([np.ones_like(x), x])
        return np.linalg.solve(design.T @ design, design.T)[0]
    if kind == "richardson":  # Lagrange interpolation at 0
        return np.array(
            [
                np.prod([xj / (xj - xi) for j, xj in enumerate(x) if j != i])
                for i, xi in enumerate(x)
            ]
        )
    raise ValueError(f"unknown extrapolator {kind!r}")


def extrapolate(z_by_factor: np.ndarray, weights: np.ndarray, clip: bool = True):
    """Rows = factors, columns = transactions. Returns (z at zero noise, clipped fraction)."""
    z0 = np.asarray(weights) @ np.asarray(z_by_factor)
    if not clip:
        return z0, 0.0
    clipped = np.abs(z0) > 1.0
    return np.clip(z0, -1.0, 1.0), float(clipped.mean())
