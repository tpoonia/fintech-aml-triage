"""Load a frozen VQC (verified artifact) as a transpiled parametrized circuit + per-row values."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit

from qtrace.config.schemas import FrozenModelRef, VQCConfig
from qtrace.qml import circuit as C
from qtrace.qml import repair as R
from qtrace.qml.encoding import AngleEncoder
from qtrace.qml.model import FrozenVQC, predict
from qtrace.qml.simulate import feature_states, parity_diagonal
from qtrace.utils.hashing import file_sha256


@dataclass
class FrozenCircuit:
    ref: FrozenModelRef
    transpiled: QuantumCircuit
    stats: dict
    theta: np.ndarray
    encoder: object  # AngleEncoder or RepairEncoder: .transform(frame) -> angles
    fmap: QuantumCircuit
    ansatz: QuantumCircuit
    artifact_file_sha256: str

    def values(self, frame: pd.DataFrame) -> np.ndarray:
        """Parameter matrix (rows x transpiled.parameters) for the given transactions."""
        angles = self.encoder.transform(frame)
        named = {f"x[{i}]": angles[:, i] for i in range(angles.shape[1])}
        named |= {f"θ[{i}]": np.full(len(frame), v) for i, v in enumerate(self.theta)}
        return np.column_stack([named[p.name] for p in self.transpiled.parameters])

    def exact_engine_scores(self, frame: pd.DataFrame) -> np.ndarray:
        """Reference scores from the exact statevector engine used to train/freeze the model."""
        states = feature_states(self.fmap, self.encoder.transform(frame))
        return predict(self.ansatz, states, self.theta, parity_diagonal(self.ansatz.num_qubits))


def load_frozen(root: Path, ref: FrozenModelRef, base: VQCConfig) -> FrozenCircuit:
    path = root / ref.artifact
    data = json.loads(path.read_text())
    stored = data.pop("artifact_sha256")
    if stored != ref.artifact_sha256:
        raise RuntimeError(f"{ref.model_id}: artifact hash {stored} is not the registered one")
    if ref.kind == "p3a_r":
        frozen = R.FrozenRepairVQC.model_validate(data)
        encoder = R.RepairEncoder.model_validate(frozen.encoder)
        cfg = R.candidate_vqc(base, frozen.candidate["ansatz_reps"])
        if frozen.candidate["observable"] != "parity":
            raise RuntimeError("Phase 3B assumes the parity readout")
    else:
        frozen = FrozenVQC.model_validate(data)
        encoder = AngleEncoder.model_validate(frozen.encoder)
        cfg = base
    if frozen.artifact_sha256() != stored:
        raise RuntimeError(f"{ref.model_id}: artifact content does not match its hash")
    fmap, ans, _ = C.build(cfg)
    transpiled, stats = C.transpiled_statistics(cfg, ref.transpile_seed)
    return FrozenCircuit(
        ref, transpiled, stats, np.array(frozen.theta), encoder, fmap, ans, file_sha256(path)
    )
