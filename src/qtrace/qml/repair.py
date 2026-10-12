"""Phase 3A-R: pre-registered VQC encoding/architecture repair (docs/PREREG_P3AR.md).

Everything here runs on vqc_train only. The one-time vqc_val evaluation lives in
``repair_outputs.run_evaluation`` and is only reachable after selection and freezing.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from pydantic import BaseModel, ConfigDict

from qtrace.config.schemas import (
    EncodingCandidateConfig,
    RepairCandidateConfig,
    RepairStudyConfig,
    SeedConfig,
    VQCConfig,
)
from qtrace.data.folds import FOLD
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import PARTITION
from qtrace.data.subset import SubsetSpec, build_vqc_training_subset
from qtrace.evaluation import metrics as M
from qtrace.qml import circuit as C
from qtrace.qml.encoding import AngleEncoder
from qtrace.qml.model import TrainingResult, bce, predict, train
from qtrace.qml.simulate import feature_states, parity_diagonal, z_qubit_diagonal
from qtrace.utils.hashing import stable_hash
from qtrace.utils.seeds import derive_seed

EXACT_FIDELITY = 1 - 1e-9


class RepairEncoder(BaseModel):
    """theta = (half_width / clip) * clip((x - median) / IQR, -clip, clip)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    enc_id: str
    features: tuple[str, ...]
    median: tuple[float, ...]
    iqr: tuple[float, ...]
    clip: float
    half_width: float
    fit_partition: str = "vqc_train"

    def artifact_sha256(self) -> str:
        return stable_hash(self)

    def robust(self, frame: pd.DataFrame) -> np.ndarray:
        x = frame[list(self.features)].to_numpy(dtype=np.float64)
        return (x - np.array(self.median)) / np.array(self.iqr)

    def transform(self, frame: pd.DataFrame) -> np.ndarray:
        r = np.clip(self.robust(frame), -self.clip, self.clip)
        return (self.half_width / self.clip) * r


def make_encoder(cfg: EncodingCandidateConfig, base: AngleEncoder) -> RepairEncoder:
    """Reuse the P3A-original median/IQR (fitted on vqc_train); change only clip and range."""
    return RepairEncoder(
        enc_id=cfg.enc_id,
        features=base.features,
        median=base.median,
        iqr=base.iqr,
        clip=cfg.clip,
        half_width=cfg.half_width,
    )


def candidate_vqc(base: VQCConfig, reps: int) -> VQCConfig:
    return base.model_copy(update={"ansatz": base.ansatz.model_copy(update={"reps": reps})})


def observable_diagonal(name: str, n_qubits: int) -> np.ndarray:
    return parity_diagonal(n_qubits) if name == "parity" else z_qubit_diagonal(n_qubits, 0)


# --------------------------------------------------------------------------- diagnostics


def encoding_diagnostics(
    enc: RepairEncoder,
    frame: pd.DataFrame,
    target: str,
    fmap,
    probe_rows: np.ndarray,
    study: RepairStudyConfig,
) -> dict:
    """Clipping, input-collision and state-collision diagnostics on vqc_train rows."""
    y = frame[target].to_numpy()
    r = enc.robust(frame)
    theta = enc.transform(frame)
    clipped = np.abs(r) > enc.clip
    keys = [tuple(v) for v in np.round(theta, 12)]
    fraud_keys = [k for k, lab in zip(keys, y, strict=True) if lab == 1]
    legit_keys = {k for k, lab in zip(keys, y, strict=True) if lab == 0}
    fraud_counts = Counter(fraud_keys)
    all_counts = Counter(keys)

    # State-collision probe: materially different inputs (>= min_sep IQR apart in some feature,
    # unclipped) whose feature-map states are near-identical (clipping collapse OR aliasing).
    states = feature_states(fmap, theta[probe_rows])
    fid = np.abs(states.conj() @ states.T) ** 2
    rp = r[probe_rows]
    sep = np.max(np.abs(rp[:, None, :] - rp[None, :, :]), axis=2)
    upper = np.triu(np.ones_like(fid, dtype=bool), k=1)
    material = upper & (sep >= study.collision_probe_min_input_separation_iqr)
    near = material & (fid >= study.collision_probe_fidelity)
    exact = material & (fid >= EXACT_FIDELITY)
    yp = y[probe_rows]
    ff = np.outer(yp == 1, yp == 1)
    fl = np.outer(yp == 1, yp == 0) | np.outer(yp == 0, yp == 1)
    alias_probe = None
    if -0.4 + np.pi <= enc.half_width:  # the Phase 3A constructed probe is representable
        base = np.array([-0.4, np.pi, np.pi, np.pi])
        a, b = feature_states(fmap, np.vstack([base, base + np.array([np.pi, 0, 0, 0])]))
        alias_probe = float(abs(np.vdot(a, b)) ** 2)
    return {
        "enc_id": enc.enc_id,
        "clip": enc.clip,
        "half_width": enc.half_width,
        "pct_values_clipped_all": float(clipped.mean()),
        "pct_values_clipped_fraud": float(clipped[y == 1].mean()),
        "frauds_all_features_clipped": int(clipped[y == 1].all(axis=1).sum()),
        "frauds": int((y == 1).sum()),
        "distinct_fraud_vectors": len(fraud_counts),
        "frauds_sharing_vector": int(sum(n for n in fraud_counts.values() if n > 1)),
        "frauds_colliding_with_legit_vector": int(sum(1 for k in fraud_keys if k in legit_keys)),
        "rows_sharing_vector_fraction": float(
            sum(n for n in all_counts.values() if n > 1) / len(keys)
        ),
        "single_qubit_phase_injective": bool(enc.half_width < np.pi / 2),
        "alias_probe_3a_fidelity": alias_probe,
        "probe_rows": len(probe_rows),
        "probe_material_near_collisions": int(near.sum()),
        "probe_material_near_collisions_fraud_fraud": int((near & ff).sum()),
        "probe_material_near_collisions_fraud_legit": int((near & fl).sum()),
        "probe_material_exact_collisions": int(exact.sum()),
    }


def eligibility(diag: dict, control: dict, rules: tuple[str, ...]) -> dict[str, bool]:
    checks = {
        "single_qubit_phase_injective": diag["single_qubit_phase_injective"],
        "fewer_shared_fraud_vectors_than_control": diag["frauds_sharing_vector"]
        < control["frauds_sharing_vector"],
    }
    return {rule: checks[rule] for rule in rules}


# ------------------------------------------------------------------------------- CV


@dataclass
class FitRecord:
    cand_id: str
    fold: int
    restart: int
    init_seed: int
    result: TrainingResult
    train_auprc: float
    val: dict[str, float] = field(default_factory=dict)


def restart_seeds(study: RepairStudyConfig, seeds: SeedConfig, dataset_id: str) -> list[int]:
    """Identical restart seeds for every candidate and fold (pre-registered)."""
    key = study.restarts.seed_key
    return [
        derive_seed(seeds.model, "model", dataset_id, key, r) % (2**32)
        for r in range(study.restarts.n_restarts)
    ]


def held_out_metrics(y: np.ndarray, p: np.ndarray, eps: float) -> dict[str, float]:
    return {
        "auprc": M.average_precision(y, p),
        "auroc": M.roc_auc(y, p),
        "bce": bce(y, p, eps),
        "score_variance": float(np.var(p)),
        "unique_score_fraction": float(np.unique(np.round(p, 12)).size / len(p)),
        "separation": float(p[y == 1].mean() - p[y == 0].mean()),
    }


def fold_training_positions(
    train_df: pd.DataFrame,
    folds: pd.DataFrame,
    fold: int,
    legit_per_fraud: float,
    target: str,
    dataset_id: str,
    seeds: SeedConfig,
) -> np.ndarray:
    """All fold-train frauds + k legit per fraud from fold-train (identical for every candidate)."""
    fold_train_ids = folds.loc[folds[FOLD] != fold, ROW_ID]
    fold_train = train_df[train_df[ROW_ID].isin(fold_train_ids)]
    record = build_vqc_training_subset(
        fold_train,
        fold_train[[ROW_ID]].assign(**{PARTITION: "vqc_train"}),
        SubsetSpec(subset_id=f"p3ar-cv-f{fold}", legit_per_fraud=legit_per_fraud),
        target=target,
        dataset_id=dataset_id,
        undersample_seed=seeds.undersample,
    )
    return np.flatnonzero(train_df[ROW_ID].isin(record.row_ids).to_numpy())


def run_cv(
    train_df: pd.DataFrame,
    folds: pd.DataFrame,
    study: RepairStudyConfig,
    base: VQCConfig,
    seeds: SeedConfig,
    states_by_enc: dict[str, np.ndarray],
    *,
    target: str,
    dataset_id: str,
) -> tuple[list[FitRecord], dict[int, np.ndarray]]:
    """Every candidate x fold x restart, trained on vqc_train fold subsets only."""
    if not train_df[ROW_ID].is_monotonic_increasing or len(train_df) != len(folds):
        raise ValueError("train must be sorted by row_id and aligned with folds")
    y = train_df[target].to_numpy(dtype=np.int64)
    eps = base.training.bce_epsilon
    fold_of = folds[FOLD].to_numpy()
    n_folds = study.cv.n_folds
    train_pos = {
        f: fold_training_positions(
            train_df, folds, f, study.cv.training_legit_per_fraud, target, dataset_id, seeds
        )
        for f in range(n_folds)
    }
    seeds_r = restart_seeds(study, seeds, dataset_id)
    records: list[FitRecord] = []
    for cand in study.candidates:
        _, ans = C.build(candidate_vqc(base, cand.ansatz_reps))[:2]
        diag = observable_diagonal(cand.observable, base.n_qubits)
        states = states_by_enc[cand.encoding]
        for f in range(n_folds):
            tr, va = train_pos[f], np.flatnonzero(fold_of == f)
            for r, seed in enumerate(seeds_r):
                res = train(ans, states[tr], y[tr], study.optimizer, eps, seed, diag)
                p_tr = predict(ans, states[tr], res.theta, diag)
                p_va = predict(ans, states[va], res.theta, diag)
                records.append(
                    FitRecord(
                        cand_id=cand.cand_id,
                        fold=f,
                        restart=r,
                        init_seed=seed,
                        result=res,
                        train_auprc=M.average_precision(y[tr], p_tr),
                        val=held_out_metrics(y[va], p_va, eps),
                    )
                )
    return records, train_pos


def trainable_parameters(n_qubits: int, reps: int) -> int:
    return n_qubits * (reps + 1)  # RealAmplitudes: one RY layer per repetition plus the final one


def summarize(
    records: list[FitRecord], study: RepairStudyConfig, eligible: dict[str, bool], n_qubits: int
) -> pd.DataFrame:
    frame = pd.DataFrame(
        [
            {
                "cand_id": r.cand_id,
                "fold": r.fold,
                "restart": r.restart,
                "final_train_bce": r.result.final_loss,
                **{f"val_{k}": v for k, v in r.val.items()},
            }
            for r in records
        ]
    )
    kept = (
        frame.sort_values(["cand_id", "fold", "final_train_bce", "restart"])
        .groupby(["cand_id", "fold"], sort=False)
        .head(1)
    )
    spread = frame.groupby(["cand_id", "fold"])["val_auprc"].agg(lambda s: s.max() - s.min())
    rows = []
    for order, cand in enumerate(study.candidates):
        k = kept[kept["cand_id"] == cand.cand_id]
        rows.append(
            {
                "matrix_order": order + 1,
                "cand_id": cand.cand_id,
                "encoding": cand.encoding,
                "ansatz_reps": cand.ansatz_reps,
                "observable": cand.observable,
                "trainable_parameters": trainable_parameters(n_qubits, cand.ansatz_reps),
                "eligible": eligible[cand.encoding],
                "cv_auprc_mean": k["val_auprc"].mean(),
                "cv_auprc_std": k["val_auprc"].std(ddof=1),
                "cv_auprc_min": k["val_auprc"].min(),
                "cv_auprc_max": k["val_auprc"].max(),
                "cv_auroc_mean": k["val_auroc"].mean(),
                "cv_bce_mean": k["val_bce"].mean(),
                "cv_score_variance_mean": k["val_score_variance"].mean(),
                "cv_unique_score_fraction_mean": k["val_unique_score_fraction"].mean(),
                "cv_separation_mean": k["val_separation"].mean(),
                "restart_auprc_spread_mean": spread.loc[cand.cand_id].mean(),
                "restart_auprc_spread_max": spread.loc[cand.cand_id].max(),
                "final_train_bce_mean": k["final_train_bce"].mean(),
            }
        )
    return pd.DataFrame(rows)


def select(summary: pd.DataFrame, study: RepairStudyConfig) -> tuple[str, dict]:
    """Deterministic pre-registered rule; returns the selected candidate and the reasoning."""
    pool = summary[summary["eligible"]].copy()
    if pool.empty:
        raise RuntimeError("no eligible candidate: report failure before Phase 3B")
    best = pool["cv_auprc_mean"].max()
    tied = pool[pool["cv_auprc_mean"] >= best - study.selection.tie_tolerance].copy()
    keys = {
        "lower_cv_std": ("cv_auprc_std", True),
        "fewer_ansatz_reps": ("ansatz_reps", True),
        "fewer_trainable_parameters": ("trainable_parameters", True),
        "matrix_order": ("matrix_order", True),
    }
    cols = [keys[t][0] for t in study.selection.tie_breakers]
    ordered = tied.sort_values(cols, kind="stable")
    chosen = str(ordered.iloc[0]["cand_id"])
    return chosen, {
        "eligible_candidates": pool["cand_id"].tolist(),
        "best_mean_cv_auprc": float(best),
        "tie_tolerance": study.selection.tie_tolerance,
        "tied_candidates": tied["cand_id"].tolist(),
        "tie_break_order": list(study.selection.tie_breakers),
        "decided_by": "primary metric" if len(tied) == 1 else "tie-breakers",
        "selected": chosen,
    }


def final_train(
    ans,
    states: np.ndarray,
    y: np.ndarray,
    diag: np.ndarray,
    study: RepairStudyConfig,
    seeds_r: list[int],
    eps: float,
) -> tuple[int, list[TrainingResult]]:
    """Same restart seeds on the fixed 3A subset; keep the lowest final training BCE."""
    results = [train(ans, states, y, study.optimizer, eps, s, diag) for s in seeds_r]
    losses = [r.final_loss for r in results]
    return int(np.argmin(losses)), results


class FrozenRepairVQC(BaseModel):
    """The frozen Phase 3A-R model; committed under artifacts/frozen_vqcs/."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    vqc_id: str
    study_id: str
    study_config_sha256: str
    candidate: dict
    base_vqc_config_sha256: str
    theta: tuple[float, ...]
    theta_sha256: str
    encoder: dict
    encoder_sha256: str
    dataset_sha256: str
    split_vqc_train_sha256: str
    preprocessing_sha256: str
    subset_rows_sha256: str
    restart_seeds: tuple[int, ...]
    kept_restart: int
    readout: str
    software: dict[str, str]

    def artifact_sha256(self) -> str:
        return stable_hash(self)


def candidate_by_id(study: RepairStudyConfig, cand_id: str) -> RepairCandidateConfig:
    return next(c for c in study.candidates if c.cand_id == cand_id)
