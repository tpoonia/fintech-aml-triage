"""VQC circuit construction: ZZ feature map (data, ``x``) + RealAmplitudes (trainable, ``θ``).

Feature-map and ansatz parameters live in separate parameter vectors so they can
never be confused. The readout is four-qubit parity ``Z⊗Z⊗Z⊗Z``.
"""

from __future__ import annotations

from qiskit import QuantumCircuit, transpile
from qiskit.circuit.library import real_amplitudes, zz_feature_map
from qiskit.quantum_info import SparsePauliOp

from qtrace.config.schemas import VQCConfig

TWO_QUBIT_GATES = {"cx", "cz", "ecr", "swap"}


def feature_map(cfg: VQCConfig) -> QuantumCircuit:
    return zz_feature_map(
        cfg.n_qubits,
        reps=cfg.feature_map.reps,
        entanglement=cfg.feature_map.entanglement,
        parameter_prefix="x",
    )


def ansatz(cfg: VQCConfig) -> QuantumCircuit:
    if cfg.ansatz.ansatz != "real_amplitudes":
        raise ValueError("Phase 3A uses RealAmplitudes only")
    return real_amplitudes(
        cfg.n_qubits,
        reps=cfg.ansatz.reps,
        entanglement=cfg.ansatz.entanglement,
        parameter_prefix="θ",
    )


def build(cfg: VQCConfig) -> tuple[QuantumCircuit, QuantumCircuit, QuantumCircuit]:
    """(feature map, ansatz, composed circuit) sharing the same parameter objects."""
    fmap, ans = feature_map(cfg), ansatz(cfg)
    return fmap, ans, fmap.compose(ans)


def full_circuit(cfg: VQCConfig) -> QuantumCircuit:
    return build(cfg)[2]


def parity_observable(n_qubits: int) -> SparsePauliOp:
    return SparsePauliOp("Z" * n_qubits)


def transpiled_statistics(cfg: VQCConfig, seed: int) -> tuple[QuantumCircuit, dict]:
    """Transpile the *parametrized* circuit once (E09) and report its size."""
    circuit = transpile(
        full_circuit(cfg),
        basis_gates=list(cfg.basis_gates),
        optimization_level=cfg.optimization_level,
        seed_transpiler=seed,
    )
    ops = {k: int(v) for k, v in sorted(circuit.count_ops().items())}
    two_q = sum(v for k, v in ops.items() if k in TWO_QUBIT_GATES)
    one_q = sum(v for k, v in ops.items() if k not in TWO_QUBIT_GATES | {"barrier", "measure"})
    stats = {
        "qubits": circuit.num_qubits,
        "depth": circuit.depth(),
        "one_qubit_gates": one_q,
        "one_qubit_gates_physical": sum(v for k, v in ops.items() if k in {"sx", "x"}),
        "two_qubit_gates": two_q,
        "total_operations": sum(ops.values()),
        "operation_counts": ops,
        "data_parameters": len(feature_map(cfg).parameters),
        "trainable_parameters": len(ansatz(cfg).parameters),
        "basis_gates": list(cfg.basis_gates),
        "optimization_level": cfg.optimization_level,
        "transpile_seed": seed,
        "note": "rz is virtual (noiseless) on the target basis",
    }
    return circuit, stats
