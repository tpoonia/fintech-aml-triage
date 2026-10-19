"""Phase 5A pool models: train-only representations and encoders, circuits, readouts, artifacts.

Every learned quantity (feature ranking, PCA, median/IQR) is fitted on ``vqc_train``
only and stored explicitly. A pool model is fully described by its structure
(features, encoding, ansatz, readout), seed index, training subset and frozen θ.
"""

from __future__ import annotations

import hashlib

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict
from qiskit import QuantumCircuit, qasm3, transpile
from qiskit.circuit.library import efficient_su2, real_amplitudes, zz_feature_map

from qtrace.config.schemas import (
    PoolAnsatzConfig,
    PoolEncodingConfig,
    PoolFeatureSetConfig,
    PoolStudyConfig,
    RepresentationConfig,
)
from qtrace.data.representation import FittedRepresentation, fit_representation
from qtrace.qml.simulate import parity_diagonal, z_qubit_diagonal
from qtrace.utils.hashing import stable_hash

TWO_QUBIT = {"cx"}
NOISY_1Q = {"sx", "x"}


def fit_feature_set(
    cfg: PoolFeatureSetConfig, train: pd.DataFrame, target: str, columns, rows_sha256: str
) -> FittedRepresentation:
    """ANOVA-F ranked slice or PCA-4, fitted on vqc_train only."""
    if cfg.kind == "pca":
        rep = RepresentationConfig(
            rep_id=cfg.feat_id, kind="pca", n_components=4, standardize=cfg.standardize
        )
        return fit_representation(rep, train, target, tuple(columns), rows_sha256)
    lo, hi = cfg.ranks
    ranked = fit_representation(
        RepresentationConfig(
            rep_id=cfg.feat_id, kind="select_k_best", n_components=hi, score_func="f_classif"
        ),
        train,
        target,
        tuple(columns),
        rows_sha256,
    )
    chosen = ranked.output_columns[lo - 1 : hi]
    if cfg.expected_features is not None and tuple(chosen) != tuple(cfg.expected_features):
        raise RuntimeError(f"{cfg.feat_id}: ranking {chosen} differs from the registration")
    return ranked.model_copy(update={"output_columns": tuple(chosen)})


class PoolEncoder(BaseModel):
    """theta = hw/scale * clip(r, -scale, scale) (clip_linear) or hw * tanh(r/scale) (tanh)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enc_id: str
    kind: str
    scale: float
    half_width: float
    median: tuple[float, ...]
    iqr: tuple[float, ...]
    fit_partition: str = "vqc_train"

    def artifact_sha256(self) -> str:
        return stable_hash(self)

    def robust(self, x: np.ndarray) -> np.ndarray:
        return (x - np.array(self.median)) / np.array(self.iqr)

    def transform(self, x: np.ndarray) -> np.ndarray:
        r = self.robust(x)
        if self.kind == "clip_linear":
            return (self.half_width / self.scale) * np.clip(r, -self.scale, self.scale)
        return self.half_width * np.tanh(r / self.scale)


def fit_encoder(cfg: PoolEncodingConfig, x_train: np.ndarray) -> PoolEncoder:
    q25, q50, q75 = np.percentile(x_train, [25.0, 50.0, 75.0], axis=0)
    iqr = q75 - q25
    if (iqr <= 0).any():
        raise RuntimeError(f"{cfg.enc_id}: zero IQR")
    return PoolEncoder(
        enc_id=cfg.enc_id,
        kind=cfg.kind,
        scale=cfg.scale,
        half_width=cfg.half_width,
        median=tuple(float(v) for v in q50),
        iqr=tuple(float(v) for v in iqr),
    )


def shared_fraud_vector_fraction(angles: np.ndarray, y: np.ndarray) -> float:
    """Fraction of frauds whose encoded vector (12 decimals) is shared with another fraud."""
    keys, counts = np.unique(np.round(angles[y == 1], 12), axis=0, return_counts=True)
    return float(counts[counts > 1].sum() / max(int((y == 1).sum()), 1))


def feature_map(n_qubits: int, study: PoolStudyConfig) -> QuantumCircuit:
    fm = study.feature_map
    return zz_feature_map(
        n_qubits, reps=fm.reps, entanglement=fm.entanglement, parameter_prefix="x"
    )


def ansatz(cfg: PoolAnsatzConfig, n_qubits: int) -> QuantumCircuit:
    fn = real_amplitudes if cfg.family == "real_amplitudes" else efficient_su2
    return fn(n_qubits, reps=cfg.reps, entanglement=cfg.entanglement, parameter_prefix="θ")


def readout_diagonal(readout: str, n_qubits: int) -> np.ndarray:
    if readout == "parity":
        return parity_diagonal(n_qubits)
    if readout == "mean_z":
        return np.mean([z_qubit_diagonal(n_qubits, q) for q in range(n_qubits)], axis=0)
    raise ValueError(f"unknown readout {readout!r}")


def transpile_structure(
    fmap: QuantumCircuit, ans: QuantumCircuit, study: PoolStudyConfig, seed: int
) -> tuple[QuantumCircuit, dict]:
    tc = transpile(
        fmap.compose(ans),
        basis_gates=list(study.basis_gates),
        optimization_level=study.optimization_level,
        seed_transpiler=seed,
    )
    ops = {k: int(v) for k, v in sorted(tc.count_ops().items())}
    stats = {
        "depth": tc.depth(),
        "noisy_depth": tc.depth(filter_function=lambda ci: ci.operation.name != "rz"),
        "cx": sum(v for k, v in ops.items() if k in TWO_QUBIT),
        "noisy_1q": sum(v for k, v in ops.items() if k in NOISY_1Q),
        "rz": ops.get("rz", 0),
        "trainable_parameters": ans.num_parameters,
        "data_parameters": fmap.num_parameters,
        "transpile_seed": seed,
        "layout_is_none": tc.layout is None,
        "qasm3_sha256": hashlib.sha256(qasm3.dumps(tc).encode()).hexdigest(),
    }
    return tc, stats


def binding_values(circuit: QuantumCircuit, angles: np.ndarray, theta: np.ndarray) -> np.ndarray:
    """Parameter matrix for ``circuit.parameters`` (x[i] per row, θ[j] constant)."""
    named = {f"x[{i}]": angles[:, i] for i in range(angles.shape[1])}
    named |= {f"θ[{j}]": np.full(len(angles), v) for j, v in enumerate(theta)}
    return np.column_stack([named[p.name] for p in circuit.parameters])


class FrozenPoolVQC(BaseModel):
    """One frozen Phase 5A pool model (no timings: byte-stable)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    model_id: str
    study_id: str
    role: str  # candidate | control
    struct_id: str
    structure: dict
    seed_index: int
    model_config_sha256: str
    subset_id: str
    subset_rows_sha256: str
    restart_seeds: tuple[int, ...]
    restart_final_bce: tuple[float, ...]
    kept_restart: int
    initial_bce: float
    final_bce: float
    nfev: int
    optimizer_status: int
    theta: tuple[float, ...]
    theta_sha256: str
    representation: dict
    representation_sha256: str
    encoder: dict
    encoder_sha256: str
    readout: str
    transpile_seed: int
    circuit: dict
    dataset_sha256: str
    split_vqc_train_sha256: str
    preprocessing_sha256: str
    software: dict[str, str]

    def artifact_sha256(self) -> str:
        return stable_hash(self)
