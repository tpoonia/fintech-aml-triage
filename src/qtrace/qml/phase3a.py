"""Phase 3A: the first clean 4-qubit VQC and its equal-input/equal-data classical comparison.

Reads only vqc_train / vqc_val (phase "phase3a", E26). Steps:

1. reproduce the Phase 2 supervised top-4 selection on vqc_train and assert it
   equals the configured features (O02, provisional);
2. fit the robust symmetric angle encoder on vqc_train (O03);
3. draw the fixed 1,065-row training subset from vqc_train (O17, 3A only);
4. train the VQC on exact statevector expectations (BCE, COBYLA, fixed budget);
5. retrain from the same seed and replay the frozen parameters (reproducibility);
6. score vqc_val and compare with LR/RF/HGB trained on the SAME angles and rows.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from qtrace.classical.models import build_model
from qtrace.classical.runner import (
    EVAL,
    FIT,
    ConfigResult,
    bootstrap_metrics,
    crossfit_seed,
    point_metrics,
    vqc_val_bootstrap_seed,
)
from qtrace.config.schemas import ClassicalBaselineConfig, SeedConfig, VQCConfig
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import PARTITION
from qtrace.data.representation import fit_representation
from qtrace.data.subset import SubsetRecord, SubsetSpec, build_vqc_training_subset
from qtrace.evaluation import metrics as M
from qtrace.qml import circuit as C
from qtrace.qml.encoding import AngleEncoder, fit_angle_encoder
from qtrace.qml.model import FrozenVQC, TrainingResult, bce, predict, theta_sha256, train
from qtrace.qml.simulate import feature_states
from qtrace.utils.hashing import stable_hash
from qtrace.utils.seeds import derive_seed

PHASE = "phase3a"
REGIME = "p3a-lpf4"


class SelectionMismatch(RuntimeError):
    pass


@dataclass
class Phase3AResults:
    features: tuple[str, ...]
    selection_scores: dict[str, float]
    encoder: AngleEncoder
    subset: SubsetRecord
    circuit_stats: dict
    training: TrainingResult
    retrain_max_abs_param_diff: float
    replay_max_abs_score_diff: float
    frozen: FrozenVQC
    y_val: np.ndarray
    vqc: ConfigResult
    classical: list[ConfigResult]
    context_unclipped: list[ConfigResult]
    clip_fractions: dict[str, dict[str, float]]
    training_diagnostics: dict = field(default_factory=dict)
    timings: dict[str, float] = field(default_factory=dict)


def _score(y, scores, model_id, rep_id, n_train, n_fraud, rows_sha, seed, cfg, boot, cross):
    metrics = point_metrics(y, scores, cfg, cross)
    intervals, samples = bootstrap_metrics(
        y, scores, metrics["threshold"], cfg.bootstrap.n_resamples, boot, cfg.bootstrap.confidence
    )
    return ConfigResult(
        model_id=model_id,
        rep_id=rep_id,
        regime_id=REGIME,
        draw=0,
        n_train=n_train,
        n_train_fraud=n_fraud,
        train_rows_sha256=rows_sha,
        model_seed=seed,
        scores=scores,
        metrics=metrics,
        intervals=intervals,
        auprc_samples=samples,
    )


def run_phase3a(
    train_df: pd.DataFrame,
    val_df: pd.DataFrame,
    cfg: VQCConfig,
    baseline: ClassicalBaselineConfig,
    seeds: SeedConfig,
    *,
    dataset_id: str,
    target: str,
    feature_columns: tuple[str, ...],
    provenance: dict,
) -> Phase3AResults:
    if set(train_df[PARTITION]) != {FIT} or set(val_df[PARTITION]) != {EVAL}:
        raise ValueError("Phase 3A trains on vqc_train and evaluates on vqc_val only")
    timings: dict[str, float] = {}
    t0 = time.perf_counter()
    train_df = train_df.sort_values(ROW_ID).reset_index(drop=True)
    val_df = val_df.sort_values(ROW_ID).reset_index(drop=True)
    y_val = val_df[target].to_numpy(dtype=np.int64)
    train_hash = row_ids_sha256(train_df[ROW_ID])

    # 1. Reproduce the provisional top-4 selection (fitted on all of vqc_train).
    rep = fit_representation(cfg.representation, train_df, target, feature_columns, train_hash)
    if tuple(rep.output_columns) != tuple(cfg.expected_features):
        raise SelectionMismatch(f"selected {rep.output_columns} != {cfg.expected_features}")
    features = tuple(rep.output_columns)

    # 2. Angle encoder (vqc_train only).
    encoder = fit_angle_encoder(cfg.encoding, train_df, features, train_hash)

    # 3. Fixed training subset (vqc_train only, undersample stream).
    subset = build_vqc_training_subset(
        train_df,
        train_df[[ROW_ID, PARTITION]],
        SubsetSpec(subset_id=cfg.subset.subset_id, legit_per_fraud=cfg.subset.legit_per_fraud),
        target=target,
        dataset_id=dataset_id,
        undersample_seed=seeds.undersample,
    )
    if cfg.subset.expected_rows is not None and len(subset.row_ids) != cfg.subset.expected_rows:
        raise ValueError(
            f"subset has {len(subset.row_ids)} rows, expected {cfg.subset.expected_rows}"
        )
    sub = train_df[train_df[ROW_ID].isin(subset.row_ids)].sort_values(ROW_ID)
    y_sub = sub[target].to_numpy(dtype=np.int64)
    theta_sub, theta_val = encoder.transform(sub), encoder.transform(val_df)
    timings["data_and_encoding_s"] = time.perf_counter() - t0

    # 4. Circuit.
    t = time.perf_counter()
    transpile_seed = derive_seed(seeds.model, "model", dataset_id, PHASE, cfg.vqc_id, "transpile")
    fmap, ans, _ = C.build(cfg)
    _, stats = C.transpiled_statistics(cfg, transpile_seed % (2**31))
    timings["circuit_build_and_transpile_s"] = time.perf_counter() - t

    t = time.perf_counter()
    states_sub = feature_states(fmap, theta_sub)
    timings["feature_states_train_s"] = time.perf_counter() - t
    t = time.perf_counter()
    states_val = feature_states(fmap, theta_val)
    timings["feature_states_val_s"] = time.perf_counter() - t

    # 5. Train, retrain (reproducibility), freeze, replay.
    init_seed = derive_seed(seeds.model, "model", dataset_id, PHASE, cfg.vqc_id) % (2**32)
    eps = cfg.training.bce_epsilon
    result = train(ans, states_sub, y_sub, cfg.optimizer, eps, init_seed)
    timings["training_s"] = result.seconds
    again = train(ans, states_sub, y_sub, cfg.optimizer, eps, init_seed)
    retrain_diff = float(np.max(np.abs(again.theta - result.theta)))

    t = time.perf_counter()
    vqc_scores = predict(ans, states_val, result.theta)
    timings["inference_val_exact_s"] = time.perf_counter() - t
    timings["inference_per_example_exact_us"] = (
        1e6 * (timings["feature_states_val_s"] + timings["inference_val_exact_s"]) / len(val_df)
    )
    frozen = FrozenVQC(
        vqc_id=cfg.vqc_id,
        theta=tuple(float(v) for v in result.theta),
        theta_sha256=theta_sha256(result.theta),
        vqc_config_sha256=stable_hash(cfg),
        dataset_sha256=provenance["dataset_sha256"],
        split_vqc_train_sha256=train_hash,
        preprocessing_sha256=provenance["preprocessing_sha256"],
        features=features,
        encoder=encoder.model_dump(mode="json"),
        encoder_sha256=encoder.artifact_sha256(),
        subset_rows_sha256=subset.row_ids_sha256,
        init_seed=init_seed,
        readout=cfg.readout.orientation,
        software=provenance["software"],
    )
    # Training-data-only diagnostics (no vqc_val information): where does the model sit?
    p_train = predict(ans, states_sub, result.theta)
    saturated = np.abs(encoder.robust(sub)) > encoder.clip
    fraud_vectors = {tuple(np.round(a, 12)) for a in theta_sub[y_sub == 1]}

    def fidelity(partner: float) -> float:
        base = np.array([-0.4] + [partner] * (cfg.n_qubits - 1))
        shifted = base.copy()
        shifted[0] += np.pi
        a, b = feature_states(fmap, np.vstack([base, shifted]))
        return float(abs(np.vdot(a, b)) ** 2)

    diagnostics = {
        "train_bce": bce(y_sub, p_train, eps),
        "constant_prevalence_bce": bce(y_sub, np.full(len(y_sub), y_sub.mean()), eps),
        "train_subset_prevalence": float(y_sub.mean()),
        "train_auprc": M.average_precision(y_sub, p_train),
        "train_auroc": M.roc_auc(y_sub, p_train),
        "train_frauds_all_features_clipped": int(saturated[y_sub == 1].all(axis=1).sum()),
        "train_legit_all_features_clipped": int(saturated[y_sub == 0].all(axis=1).sum()),
        "train_distinct_fraud_angle_vectors": len(fraud_vectors),
        "feature_map_alias_fidelity": {
            "x0=-0.4 vs x0=-0.4+pi, partners=+pi": fidelity(np.pi),
            "x0=-0.4 vs x0=-0.4+pi, partners=0": fidelity(0.0),
            "x0=-0.4 vs x0=-0.4+pi, partners=-pi": fidelity(-np.pi),
        },
    }
    replay = predict(ans, states_val, np.array(frozen.theta))
    replay_diff = float(np.max(np.abs(replay - vqc_scores)))

    # 6. Metrics: VQC and equal-input/equal-data classical models, same resamples.
    boot, cross = vqc_val_bootstrap_seed(seeds, dataset_id), crossfit_seed(seeds, dataset_id)
    n_sub, n_fraud = len(sub), int(y_sub.sum())
    vqc = _score(
        y_val,
        vqc_scores,
        "vqc",
        "top4-angles",
        n_sub,
        n_fraud,
        subset.row_ids_sha256,
        init_seed,
        baseline,
        boot,
        cross,
    )
    classical, unclipped = [], []
    r_sub, r_val = encoder.robust(sub), encoder.robust(val_df)
    for inputs, x_tr, x_va, bucket in (
        ("top4-angles", theta_sub, theta_val, classical),
        ("top4-robust-unclipped", r_sub, r_val, unclipped),
    ):
        for model_cfg in baseline.models:
            seed = derive_seed(seeds.model, "model", dataset_id, PHASE, model_cfg.model_id, inputs)
            seed %= 2**32
            model = build_model(model_cfg, None, seed).fit(x_tr, y_sub)
            scores = model.predict_proba(x_va)[:, 1]
            bucket.append(
                _score(
                    y_val,
                    scores,
                    model_cfg.model_id,
                    inputs,
                    n_sub,
                    n_fraud,
                    subset.row_ids_sha256,
                    seed,
                    baseline,
                    boot,
                    cross,
                )
            )
    return Phase3AResults(
        features=features,
        selection_scores=rep.selector_scores,
        encoder=encoder,
        subset=subset,
        circuit_stats=stats,
        training=result,
        retrain_max_abs_param_diff=retrain_diff,
        replay_max_abs_score_diff=replay_diff,
        frozen=frozen,
        y_val=y_val,
        vqc=vqc,
        classical=classical,
        context_unclipped=unclipped,
        clip_fractions={
            "vqc_train": encoder.clip_fractions(train_df),
            "training_subset": encoder.clip_fractions(sub),
            "vqc_val": encoder.clip_fractions(val_df),
        },
        training_diagnostics=diagnostics,
        timings=timings,
    )
