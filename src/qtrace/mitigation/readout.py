"""Tensored readout mitigation from observable calibration counts (E11; PREREG_P4 §7).

The estimator sees only calibration outcomes (|0...0> and |1...1> prepared and
measured), never the simulator's readout parameters. Each qubit's 2x2 response
[[1 - p01, p10], [p01, 1 - p10]] (rows = read, columns = prepared) is inverted and
applied to the measured distribution; the resulting quasi-distribution is projected
onto the probability simplex (Euclidean nearest point) when it has negative entries.

Bit order is Qiskit little-endian: bit q of a basis index is qubit q.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
from qiskit import QuantumCircuit


def calibration_circuits(n_qubits: int) -> tuple[QuantumCircuit, QuantumCircuit]:
    """|0...0> (no gates) and |1...1> (one x per qubit); measurement is added by the caller."""
    zeros = QuantumCircuit(n_qubits, name="cal_all_zeros")
    ones = QuantumCircuit(n_qubits, name="cal_all_ones")
    ones.x(range(n_qubits))
    return zeros, ones


def bit_one_marginals(dist: np.ndarray) -> np.ndarray:
    """P(bit q reads 1) for each qubit q, from one 2^n distribution (or normalized counts)."""
    dist = np.asarray(dist, dtype=np.float64)
    n = int(np.log2(dist.size))
    basis = np.arange(dist.size)
    return np.array([dist[(basis >> q) & 1 == 1].sum() for q in range(n)])


@dataclass(frozen=True)
class ReadoutCalibration:
    p01: np.ndarray  # per qubit: P(read 1 | prepared 0)
    p10: np.ndarray  # per qubit: P(read 0 | prepared 1)

    @property
    def determinants(self) -> np.ndarray:
        return 1.0 - self.p01 - self.p10

    def matrices(self) -> list[np.ndarray]:
        return [np.array([[1 - a, b], [a, 1 - b]]) for a, b in zip(self.p01, self.p10, strict=True)]


def estimate_calibration(all_zeros: np.ndarray, all_ones: np.ndarray) -> ReadoutCalibration:
    """Per-qubit response from the |0...0> and |1...1> calibration outcome distributions."""
    zeros = np.asarray(all_zeros, dtype=np.float64)
    ones = np.asarray(all_ones, dtype=np.float64)
    return ReadoutCalibration(
        p01=bit_one_marginals(zeros / zeros.sum()),
        p10=1.0 - bit_one_marginals(ones / ones.sum()),
    )


def apply_per_qubit(probs: np.ndarray, mats: list[np.ndarray]) -> np.ndarray:
    """Apply one 2x2 matrix per qubit (mats[q] acts on bit q) to rows of 2^n vectors."""
    probs = np.atleast_2d(probs)
    n = len(mats)
    tensor = probs.reshape((len(probs),) + (2,) * n)
    for q, mat in enumerate(mats):
        axis = n - q  # C-order reshape: axis 1 is the most significant bit
        tensor = np.moveaxis(np.tensordot(mat, tensor, axes=([1], [axis])), 0, axis)
    return tensor.reshape(len(probs), -1)


def project_simplex(q: np.ndarray) -> np.ndarray:
    """Euclidean projection of each row onto {p >= 0, sum p = 1} (sort-based, exact)."""
    q = np.atleast_2d(np.asarray(q, dtype=np.float64))
    n = q.shape[1]
    u = -np.sort(-q, axis=1)
    css = np.cumsum(u, axis=1) - 1.0
    ok = u - css / np.arange(1, n + 1) > 0
    rho = n - 1 - np.argmax(ok[:, ::-1], axis=1)
    theta = css[np.arange(len(q)), rho] / (rho + 1)
    return np.maximum(q - theta[:, None], 0.0)


@dataclass(frozen=True)
class MitigationDiagnostics:
    rows_projected: int
    mean_l1_moved: float  # mean over rows of |projected - quasi|_1
    min_determinant: float
    unstable: bool


def mitigate(
    probs: np.ndarray, calibration: ReadoutCalibration, min_determinant: float = 0.5
) -> tuple[np.ndarray, MitigationDiagnostics]:
    """Tensored inversion, then simplex projection of rows with negative entries."""
    dets = calibration.determinants
    inverses = [np.linalg.inv(m) for m in calibration.matrices()]
    quasi = apply_per_qubit(np.atleast_2d(probs), inverses)
    out = quasi.copy()
    bad = quasi.min(axis=1) < 0
    if bad.any():
        out[bad] = project_simplex(quasi[bad])
    diag = MitigationDiagnostics(
        rows_projected=int(bad.sum()),
        mean_l1_moved=float(np.abs(out - quasi).sum(axis=1).mean()),
        min_determinant=float(dets.min()),
        unstable=bool(dets.min() < min_determinant),
    )
    return out, diag
