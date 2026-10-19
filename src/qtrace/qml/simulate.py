"""Exact (noiseless, infinite-shot) parity expectations for the VQC.

Because the data enter only through the feature map, each transaction's
feature-map state |phi(x)> is computed once (Qiskit ``Statevector``). For a
parameter vector theta the ansatz unitary U(theta) (2^n x 2^n, Qiskit
``Operator``) is applied to all states at once, and parity is read from the
computational-basis probabilities:

    z(x, theta) = sum_b |(U phi(x))_b|^2 * (-1)^popcount(b)

This equals <phi(x)| U^dag Z^n U |phi(x)>; tests check it against Qiskit's
``StatevectorEstimator`` and Aer's density-matrix estimator.
"""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit.quantum_info import Operator, Statevector


def parity_diagonal(n_qubits: int) -> np.ndarray:
    basis = np.arange(2**n_qubits)
    popcount = np.array([bin(b).count("1") for b in basis])
    return (-1.0) ** popcount


def z_qubit_diagonal(n_qubits: int, qubit: int) -> np.ndarray:
    """Eigenvalues of Z on one qubit (Qiskit little-endian: bit ``qubit`` of the basis index)."""
    basis = np.arange(2**n_qubits)
    return (-1.0) ** ((basis >> qubit) & 1)


def feature_states(fmap: QuantumCircuit, angles: np.ndarray) -> np.ndarray:
    """Rows = transactions, columns = 2^n amplitudes of |phi(x)>."""
    params = list(fmap.parameters)  # x[0..n-1], sorted by index
    states = np.empty((len(angles), 2**fmap.num_qubits), dtype=np.complex128)
    for i, row in enumerate(angles):
        bound = fmap.assign_parameters(dict(zip(params, row, strict=True)))
        states[i] = Statevector(bound).data
    return states


def ansatz_unitary(ans: QuantumCircuit, theta: np.ndarray) -> np.ndarray:
    return Operator(ans.assign_parameters(dict(zip(ans.parameters, theta, strict=True)))).data


def parity_expectations(states: np.ndarray, unitary: np.ndarray, parity: np.ndarray) -> np.ndarray:
    amplitudes = states @ unitary.T
    return (np.abs(amplitudes) ** 2) @ parity
