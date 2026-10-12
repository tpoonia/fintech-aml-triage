"""Exact (density-matrix, no shots) output distributions for many parameter bindings."""

from __future__ import annotations

import numpy as np
from qiskit import QuantumCircuit
from qiskit_aer import AerSimulator
from qiskit_aer.noise import NoiseModel


def exact_distributions(
    transpiled: QuantumCircuit,
    values: np.ndarray,
    noise_model: NoiseModel | None,
    chunk: int = 4096,
) -> np.ndarray:
    """Rows = parameter bindings; columns = 2^n exact computational-basis probabilities.

    Gate noise only: readout is applied classically afterwards (PREREG_P3B §4).
    """
    circuit = transpiled.copy()
    circuit.save_probabilities()
    sim = AerSimulator(method="density_matrix", noise_model=noise_model)
    params = list(circuit.parameters)
    out = np.empty((len(values), 2**circuit.num_qubits))
    for start in range(0, len(values), chunk):
        block = values[start : start + chunk]
        binds = [{p: block[:, j].tolist() for j, p in enumerate(params)}]
        result = sim.run(circuit, parameter_binds=binds).result()
        rows = [result.data(i)["probabilities"] for i in range(len(block))]
        out[start : start + len(block)] = rows
    return out
