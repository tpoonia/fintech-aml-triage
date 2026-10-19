"""Load the frozen Phase 5A pool for Phase 5B: verified hashes, rebuilt circuits, split, statics.

Nothing here retrains or modifies a model. Every artifact hash is checked against the
frozen manifest (whose own file hash is registered), and every rebuilt transpiled
circuit must reproduce the frozen circuit hash.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from pathlib import Path

import numpy as np
import pandas as pd
from qiskit import QuantumCircuit

from qtrace.config.schemas import CounterfactualStudyConfig, PoolStudyConfig
from qtrace.data.representation import FittedRepresentation
from qtrace.mitigation import zne as Z
from qtrace.qml import pool as P
from qtrace.utils.hashing import file_sha256

BASIS = ("rz", "sx", "x", "cx")


@dataclass
class PoolModel:
    model_id: str
    struct_id: str
    seed_index: int
    split: str  # train | val | test (structure split)
    partition: str  # ctrl_train | ctrl_val | ctrl_test (A04)
    structure: dict
    representation: FittedRepresentation
    encoder: P.PoolEncoder
    theta: np.ndarray
    tau: float
    readout: str
    transpiled: QuantumCircuit
    fmap: QuantumCircuit
    ansatz: QuantumCircuit
    circuit: dict
    folded_stats: dict[int, dict]
    clean_metrics: dict
    artifact_sha256: str
    static: dict = field(default_factory=dict)

    @property
    def diagonal(self) -> np.ndarray:
        return P.readout_diagonal(self.readout, self.transpiled.num_qubits)

    def angles(self, frame: pd.DataFrame) -> np.ndarray:
        return self.encoder.transform(self.representation.transform(frame))

    def values(self, angles: np.ndarray) -> np.ndarray:
        return P.binding_values(self.transpiled, angles, self.theta)


def split_of(study: CounterfactualStudyConfig) -> dict[str, str]:
    out = {}
    for name in ("train", "val", "test"):
        for sid in getattr(study.structure_split, name):
            out[sid] = name
    return out


def load_pool(
    root: Path, study: CounterfactualStudyConfig, pool_study: PoolStudyConfig
) -> list[PoolModel]:
    path = root / study.pool_manifest
    if file_sha256(path) != study.pool_manifest_sha256:
        raise RuntimeError("the frozen pool manifest differs from the registered hash")
    manifest = json.loads(path.read_text())
    split = split_of(study)
    structs = {s.struct_id for s in pool_study.structures}
    if set(split) != structs:
        raise RuntimeError("the structure split must cover every pool structure exactly once")
    ans_cfg = {a.ans_id: a for a in pool_study.ansatze}
    fmap = P.feature_map(4, pool_study)
    models = []
    for entry in manifest["primary_pool"]:
        art = json.loads((root / entry["artifact"]).read_text())
        stored = art.pop("artifact_sha256")
        frozen = P.FrozenPoolVQC.model_validate(art)
        if stored != entry["artifact_sha256"] or frozen.artifact_sha256() != stored:
            raise RuntimeError(f"{entry['model_id']}: artifact hash mismatch")
        st = frozen.structure
        a = ans_cfg[st["ansatz"]]
        ans = P.ansatz(a, 4)
        tc, stats = P.transpile_structure(fmap, ans, pool_study, frozen.transpile_seed)
        if stats["qasm3_sha256"] != frozen.circuit["qasm3_sha256"]:
            raise RuntimeError(f"{frozen.model_id}: rebuilt circuit differs from the frozen one")
        folded = {
            f: Z.circuit_statistics(Z.fold_global(tc, f, BASIS, frozen.transpile_seed))
            for f in (1, 3, 5)
        }
        part = study.partition_of[split[frozen.struct_id]]
        m = PoolModel(
            model_id=frozen.model_id,
            struct_id=frozen.struct_id,
            seed_index=frozen.seed_index,
            split=split[frozen.struct_id],
            partition=part,
            structure=st,
            representation=FittedRepresentation.model_validate(frozen.representation),
            encoder=P.PoolEncoder.model_validate(frozen.encoder),
            theta=np.array(frozen.theta),
            tau=float(entry["tau"]),
            readout=frozen.readout,
            transpiled=tc,
            fmap=fmap,
            ansatz=ans,
            circuit=stats,
            folded_stats=folded,
            clean_metrics=entry["clean"],
            artifact_sha256=stored,
        )
        m.static = static_features(m, a.family, a.reps)
        models.append(m)
    return models


def static_features(m: PoolModel, family: str, reps: int) -> dict:
    """Pre-execution descriptors (registry names; A15). Shot budget is added per arm."""
    return {
        "circuit_depth": m.circuit["depth"],
        "noisy_depth": m.circuit["noisy_depth"],
        "n_1q_gates": m.circuit["noisy_1q"],
        "n_2q_gates": m.circuit["cx"],
        "trainable_parameters": m.circuit["trainable_parameters"],
        "ansatz": family,
        "ansatz_reps": reps,
        "readout_observable": m.readout,
        "encoding_family": m.structure["encoding"],
        "feature_set": m.structure["features"],
        "clean_val_auprc_at_freeze": m.clean_metrics["auprc"],
        "clean_val_auroc_at_freeze": m.clean_metrics["auroc"],
        "clean_val_brier_at_freeze": m.clean_metrics["brier"],
        "clean_val_ece_at_freeze": m.clean_metrics["ece"],
        "frozen_tau": m.tau,
    }
