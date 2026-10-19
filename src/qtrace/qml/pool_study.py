"""Phase 5A configured run: build, qualify and freeze the independent VQC pool (PREREG_P5A).

vqc_train fits every representation, encoder, subset and model; vqc_val is used only
for clean qualification and diversity. No noise, no mitigation, no controller.
Timing-dependent outputs (runtime table) are rendered separately from the
deterministic tables, which reproduce byte for byte.
"""

from __future__ import annotations

import io
import json
import time
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed
from scipy import stats
from scipy.cluster.hierarchy import leaves_list, linkage
from scipy.spatial.distance import squareform

from qtrace.classical.runner import vqc_val_bootstrap_seed
from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import FrozenModelRef, PoolStructureConfig, PoolStudyConfig
from qtrace.data.access import load_partitions
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import PARTITION
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.subset import SubsetSpec, build_vqc_training_subset
from qtrace.data.verify import verify_phase1
from qtrace.evaluation import metrics as M
from qtrace.evaluation.bootstrap import percentile_interval, stratified_weights
from qtrace.mitigation.zne import fold_global
from qtrace.noise.exact import exact_distributions
from qtrace.noise.frozen import load_frozen
from qtrace.noise.models import gate_noise_model
from qtrace.qml import pool as P
from qtrace.qml.model import predict, theta_sha256, train
from qtrace.qml.simulate import feature_states
from qtrace.utils.hashing import file_sha256, stable_hash
from qtrace.utils.seeds import derive_seed

EXPERIMENT_ID = "phase5a_pool"
STUDY_ID = "p5a_v1"
PHASE = "phase5a"
T = "results/tables/"
A = "artifacts/model_pool/"
DIGITS = 9
P4_FINITE_SAMPLING_CPU_S = 95.5  # Phase 4 measured (protocol §3.10): one model, 16 contexts
P4_FINITE_METRICS_CPU_S = 163.8
P4_BOOTSTRAP_CPU_S = 1397.8
P4_ROWS = 28372
P4_GATE_SIGNATURES = 5


@dataclass(frozen=True)
class Candidate:
    model_id: str
    role: str  # candidate | control
    structure: PoolStructureConfig
    seed_index: int


def load_pool_study(config_root: Path | None = None):
    return load_experiment(EXPERIMENT_ID, config_root), load_component(
        "pool_study", STUDY_ID, config_root
    )


def registry(study: PoolStudyConfig) -> list[Candidate]:
    """Every attempted model in registry order (candidates, then trained controls)."""
    out = [
        Candidate(f"p5a-{st.struct_id}-s{k}", "candidate", st, k)
        for st in study.structures
        for k in range(study.seeds_per_structure)
    ]
    out += [
        Candidate(c.control_id, "control", c.structure, c.seed_index)
        for c in study.controls
        if c.kind == "structure"
    ]
    return out


def _software() -> dict[str, str]:
    names = ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn")
    return {n: importlib_metadata.version(n) for n in names}


def _train_one(cand, ans_cfg, states_tr, y_tr, states_val, diag, opt, eps, init_seeds, tc, head):
    ans = P.ansatz(ans_cfg, 4)
    t0 = time.perf_counter()
    fits = [train(ans, states_tr, y_tr, opt, eps, s, diag) for s in init_seeds]
    train_s = time.perf_counter() - t0
    finals = [f.final_loss for f in fits]
    kept = int(np.argmin(finals))
    theta = fits[kept].theta
    t0 = time.perf_counter()
    p_val = predict(ans, states_val, theta, diag)
    infer_s = time.perf_counter() - t0
    again = [train(ans, states_tr, y_tr, opt, eps, s, diag) for s in init_seeds]
    identical = all(np.array_equal(a.theta, b.theta) for a, b in zip(fits, again, strict=True))
    p_again = predict(ans, states_val, again[kept].theta, diag)
    identical = identical and np.array_equal(p_val, p_again)
    probs = exact_distributions(tc, P.binding_values(tc, head, theta), None)
    aer_dev = float(np.max(np.abs(probs @ diag - (1.0 - 2.0 * p_val[: len(head)]))))
    return {
        "model_id": cand.model_id,
        "theta": theta,
        "restart_final_bce": tuple(float(v) for v in finals),
        "kept_restart": kept,
        "initial_bce": float(fits[kept].initial_loss),
        "final_bce": float(fits[kept].final_loss),
        "nfev": int(fits[kept].nfev),
        "optimizer_status": int(fits[kept].status),
        "p_val": p_val,
        "retrain_identical": bool(identical),
        "aer_max_abs_dz": aer_dev,
        "train_seconds": train_s,
        "inference_seconds": infer_s,
    }


def _bootstrap(y, s, n, seed, conf=0.95):
    a = np.empty(n)
    r = np.empty(n)
    for b, w in enumerate(stratified_weights(y, n, seed)):
        a[b] = M.average_precision(y, s, w)
        r[b] = M.roc_auc(y, s, w)
    return percentile_interval(a, conf), percentile_interval(r, conf)


def prediction_sha256(p: np.ndarray) -> str:
    return stable_hash([float(v) for v in np.round(p, 12)])


def clean_metrics(y, p, n_resamples, seed, ece_bins=10) -> dict:
    (alo, ahi), (rlo, rhi) = _bootstrap(y, p, n_resamples, seed)
    tau = M.max_f1_threshold(y, p)
    th = M.threshold_metrics(y, p, tau)
    return {
        "auprc": M.average_precision(y, p),
        "auprc_ci_low": alo,
        "auprc_ci_high": ahi,
        "auroc": M.roc_auc(y, p),
        "auroc_ci_low": rlo,
        "auroc_ci_high": rhi,
        "brier": M.brier(y, p),
        "ece": M.expected_calibration_error(y, p, ece_bins, "uniform"),
        "tau": tau,
        "precision_at_tau": th["precision"],
        "recall_at_tau": th["recall"],
        "f1_at_tau": th["f1"],
        "distinct_scores": int(np.unique(np.round(p, 12)).size),
        "score_sd": float(np.std(p)),
        "finite_in_unit_interval": bool(np.isfinite(p).all() and p.min() >= 0 and p.max() <= 1),
        "prediction_sha256": prediction_sha256(p),
    }


def qualify(m, o, enc_d, q, prevalence, th_sha, seen_theta, seen_pred) -> dict[str, bool]:
    """Pre-registered clean-validity criteria Q1-Q9 (PREREG_P5A §8)."""
    return {
        "Q1_auroc_ci_low": m["auroc_ci_low"] > q.min_auroc_ci_low,
        "Q2_auprc_ci_low": m["auprc_ci_low"] > q.min_auprc_ci_low_over_prevalence * prevalence,
        "Q3_loss_reduction": o["final_bce"]
        <= (1 - q.min_relative_loss_reduction) * o["initial_bce"],
        "Q4_distinct_scores": m["distinct_scores"] >= q.min_distinct_scores,
        "Q5_valid_probabilities": bool(m["finite_in_unit_interval"]),
        "Q6_encoding": bool(enc_d["alias_safe"])
        and enc_d["shared_fraud_vector_fraction"] <= q.max_shared_fraud_vector_fraction,
        "Q7_aer_crosscheck": o["aer_max_abs_dz"] <= q.aer_crosscheck_tol,
        "Q8_bitwise_retrain": bool(o["retrain_identical"]) or not q.require_bitwise_retrain,
        "Q9_not_duplicate": th_sha not in seen_theta and m["prediction_sha256"] not in seen_pred,
    }


@dataclass
class PoolRun:
    study: PoolStudyConfig
    y: np.ndarray
    candidates: list[Candidate]
    records: dict[str, dict]  # model_id -> everything about the model
    artifacts: dict[str, dict]  # model_id -> frozen artifact JSON (dict)
    encodings: list[dict]
    reference: dict[str, dict]  # anchor + replayed control -> metrics
    scores: dict[str, np.ndarray]  # qualified + anchor clean vqc_val scores (not rendered)
    context: dict
    timings: dict[str, float]
    diversity: dict = field(default_factory=dict)
    power: pd.DataFrame | None = None
    benchmark: dict = field(default_factory=dict)
    g3a: dict = field(default_factory=dict)


def run_pool(root: Path, n_jobs: int = -1) -> PoolRun:
    timings: dict[str, float] = {}
    t_all = time.perf_counter()
    resolved, study = load_pool_study()
    spec, dataset = resolved.spec, resolved.dataset
    target = dataset.target_column
    anchor_before = file_sha256(root / study.anchor.artifact)
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, PHASE, [study.fit_partition, study.qualify_partition])
    verified = verify_phase1(
        root, dataset.dataset_id, frame, fitted, (study.fit_partition, study.qualify_partition)
    )
    train_df = frame[frame[PARTITION] == "vqc_train"].sort_values(ROW_ID).reset_index(drop=True)
    val = frame[frame[PARTITION] == "vqc_val"].sort_values(ROW_ID).reset_index(drop=True)
    y_train = train_df[target].to_numpy(dtype=np.int64)
    y = val[target].to_numpy(dtype=np.int64)
    columns = tuple(fitted.output_columns)
    train_sha = row_ids_sha256(train_df[ROW_ID])
    cands = registry(study)
    feat_cfg = {f.feat_id: f for f in study.feature_sets}
    enc_cfg = {e.enc_id: e for e in study.encodings}
    ans_cfg = {a.ans_id: a for a in study.ansatze}

    # ---- train-only representations and encoders
    reps = {
        fid: P.fit_feature_set(cfg, train_df, target, columns, train_sha)
        for fid, cfg in feat_cfg.items()
    }
    combos = sorted({(c.structure.features, c.structure.encoding) for c in cands})
    encoders, ang_tr, ang_val, encodings = {}, {}, {}, []
    for f, e in combos:
        x_tr, x_va = reps[f].transform(train_df), reps[f].transform(val)
        enc = P.fit_encoder(enc_cfg[e], x_tr)
        encoders[(f, e)] = enc
        ang_tr[(f, e)], ang_val[(f, e)] = enc.transform(x_tr), enc.transform(x_va)
        r_tr = enc.robust(x_tr)
        encodings.append(
            {
                "features": f,
                "encoding": e,
                "kind": enc.kind,
                "scale": enc.scale,
                "half_width": enc.half_width,
                "alias_safe": enc.half_width < np.pi / 2,
                "shared_fraud_vector_fraction": P.shared_fraud_vector_fraction(
                    ang_tr[(f, e)], y_train
                ),
                "fraud_values_beyond_scale": float((np.abs(r_tr[y_train == 1]) > enc.scale).mean()),
                "output_columns": "|".join(reps[f].output_columns),
            }
        )
    enc_ok = {(d["features"], d["encoding"]): d for d in encodings}

    # ---- training subsets (one draw per seed index, shared by every structure)
    subsets = {}
    for k in sorted({c.seed_index for c in cands}):
        rec = build_vqc_training_subset(
            train_df,
            train_df[[ROW_ID, PARTITION]],
            SubsetSpec(
                subset_id=f"{study.subset_id_prefix}-s{k}",
                legit_per_fraud=study.subset_legit_per_fraud,
            ),
            target=target,
            dataset_id=dataset.dataset_id,
            undersample_seed=spec.seeds.undersample,
        )
        pos = np.flatnonzero(train_df[ROW_ID].isin(rec.row_ids).to_numpy())
        subsets[k] = (rec, pos)

    # ---- feature-map states (train subsets and vqc_val), parallel over combinations
    t = time.perf_counter()
    fmap = P.feature_map(4, study)
    val_states = dict(
        zip(
            combos,
            Parallel(n_jobs=n_jobs)(delayed(feature_states)(fmap, ang_val[c]) for c in combos),
            strict=True,
        )
    )
    tr_states = {
        (c, k): feature_states(fmap, ang_tr[c][pos])
        for c in combos
        for k, (_, pos) in subsets.items()
    }
    timings["feature_states_s"] = time.perf_counter() - t

    # ---- transpile each structure once
    structs = {c.structure.struct_id: c.structure for c in cands}
    transpiled = {}
    for sid, st in structs.items():
        seed = derive_seed(
            spec.seeds.model, "model", dataset.dataset_id, study.seed_keys["transpile"], sid
        ) % (2**31)
        transpiled[sid] = (
            *P.transpile_structure(fmap, P.ansatz(ans_cfg[st.ansatz], 4), study, seed),
            seed,
        )

    # ---- train every attempted model (parallel), with retraining and Aer checks
    t = time.perf_counter()
    head_n = study.qualification.aer_crosscheck_rows

    def init_seeds(c):
        return [
            derive_seed(
                spec.seeds.model,
                "model",
                dataset.dataset_id,
                study.seed_keys["init"],
                c.structure.struct_id,
                c.seed_index,
                r,
            )
            % (2**32)
            for r in range(study.restarts)
        ]

    outs = Parallel(n_jobs=n_jobs)(
        delayed(_train_one)(
            c,
            ans_cfg[c.structure.ansatz],
            tr_states[((c.structure.features, c.structure.encoding), c.seed_index)],
            y_train[subsets[c.seed_index][1]],
            val_states[(c.structure.features, c.structure.encoding)],
            P.readout_diagonal(c.structure.readout, 4),
            study.optimizer,
            study.bce_epsilon,
            init_seeds(c),
            transpiled[c.structure.struct_id][0],
            ang_val[(c.structure.features, c.structure.encoding)][:head_n],
        )
        for c in cands
    )
    timings["training_wall_s"] = time.perf_counter() - t
    boot_seed = vqc_val_bootstrap_seed(spec.seeds, dataset.dataset_id)
    t = time.perf_counter()
    mets = Parallel(n_jobs=n_jobs)(
        delayed(clean_metrics)(y, o["p_val"], study.bootstrap_resamples, boot_seed) for o in outs
    )
    timings["qualification_bootstrap_s"] = time.perf_counter() - t

    # ---- qualification Q1-Q9 (registry order) and frozen artifacts
    q = study.qualification
    prevalence = float(y.mean())
    records, artifacts, scores = {}, {}, {}
    seen_theta, seen_pred = set(), set()
    software = _software()
    for c, o, m in zip(cands, outs, mets, strict=True):
        st = c.structure
        rec_sub, _ = subsets[c.seed_index]
        tc, cstats, tseed = transpiled[st.struct_id]
        enc_d = enc_ok[(st.features, st.encoding)]
        th_sha = theta_sha256(o["theta"])
        checks = qualify(m, o, enc_d, q, prevalence, th_sha, seen_theta, seen_pred)
        failed = [k for k, ok in checks.items() if not ok]
        qualified = c.role == "candidate" and not failed
        if c.role == "candidate" and checks["Q9_not_duplicate"]:
            seen_theta.add(th_sha)
            seen_pred.add(m["prediction_sha256"])
        config_hash = stable_hash(
            {
                "structure": st.model_dump(),
                "seed_index": c.seed_index,
                "subset_id": rec_sub.spec.subset_id,
                "optimizer": study.optimizer.model_dump(),
                "restarts": study.restarts,
                "feature_map": study.feature_map.model_dump(),
                "transpile_seed": tseed,
            }
        )
        art = P.FrozenPoolVQC(
            model_id=c.model_id,
            study_id=study.study_id,
            role=c.role,
            struct_id=st.struct_id,
            structure=st.model_dump(),
            seed_index=c.seed_index,
            model_config_sha256=config_hash,
            subset_id=rec_sub.spec.subset_id,
            subset_rows_sha256=rec_sub.row_ids_sha256,
            restart_seeds=tuple(init_seeds(c)),
            restart_final_bce=o["restart_final_bce"],
            kept_restart=o["kept_restart"],
            initial_bce=o["initial_bce"],
            final_bce=o["final_bce"],
            nfev=o["nfev"],
            optimizer_status=o["optimizer_status"],
            theta=tuple(float(v) for v in o["theta"]),
            theta_sha256=th_sha,
            representation=reps[st.features].model_dump(mode="json"),
            representation_sha256=reps[st.features].artifact_sha256(),
            encoder=encoders[(st.features, st.encoding)].model_dump(),
            encoder_sha256=encoders[(st.features, st.encoding)].artifact_sha256(),
            readout=st.readout,
            transpile_seed=tseed,
            circuit=cstats,
            dataset_sha256=dataset.expected_sha256,
            split_vqc_train_sha256=verified["phase1_partition_row_ids_sha256"]["vqc_train"],
            preprocessing_sha256=verified["phase1_preprocessing_artifact_sha256"],
            software=software,
        )
        artifacts[c.model_id] = {**art.model_dump(), "artifact_sha256": art.artifact_sha256()}
        records[c.model_id] = {
            "model_id": c.model_id,
            "role": c.role,
            "struct_id": st.struct_id,
            "features": st.features,
            "encoding": st.encoding,
            "ansatz": st.ansatz,
            "family": ans_cfg[st.ansatz].family,
            "reps": ans_cfg[st.ansatz].reps,
            "readout": st.readout,
            "seed_index": c.seed_index,
            "subset_id": rec_sub.spec.subset_id,
            "qualified": qualified,
            "failed_criteria": "|".join(failed),
            "exclusion_reason": (failed[0] if failed else "")
            if c.role == "candidate"
            else "diagnostic control (never in the primary pool)",
            **m,
            "initial_bce": o["initial_bce"],
            "final_bce": o["final_bce"],
            "relative_loss_reduction": 1 - o["final_bce"] / o["initial_bce"],
            "nfev": o["nfev"],
            "budget_bound": o["nfev"] >= study.optimizer.max_evaluations,
            "aer_max_abs_dz": o["aer_max_abs_dz"],
            "retrain_identical": o["retrain_identical"],
            "theta_sha256": th_sha,
            "model_config_sha256": config_hash,
            "artifact_sha256": artifacts[c.model_id]["artifact_sha256"],
            **{
                k: cstats[k]
                for k in ("depth", "noisy_depth", "cx", "noisy_1q", "trainable_parameters")
            },
            "circuit_qasm3_sha256": cstats["qasm3_sha256"],
            "train_seconds": o["train_seconds"],
            "inference_seconds": o["inference_seconds"],
        }
        if qualified:
            scores[c.model_id] = o["p_val"]

    # ---- anchor and replayed control (existing artifacts; never retrained)
    reference = {}
    for ref, role in [(study.anchor, "anchor")] + [
        (c, "control") for c in study.controls if c.kind == "existing_artifact"
    ]:
        mref = (
            ref
            if role == "anchor"
            else FrozenModelRef(
                model_id=ref.control_id,
                kind="p3a_original",
                role="exploratory_contrast",
                artifact=ref.artifact,
                artifact_sha256=ref.artifact_sha256,
                transpile_seed=ref.transpile_seed,
            )
        )
        fc = load_frozen(root, mref, resolved.vqc)
        p = fc.exact_engine_scores(val)
        m = clean_metrics(y, p, study.bootstrap_resamples, boot_seed)
        reference[mref.model_id] = {
            "model_id": mref.model_id,
            "role": role,
            **m,
            **{k: fc.stats[k] for k in ("depth", "trainable_parameters")},
            "cx": fc.stats["two_qubit_gates"],
            "noisy_1q": fc.stats["one_qubit_gates_physical"],
            "artifact_sha256": mref.artifact_sha256,
        }
        if role == "anchor":
            scores[mref.model_id] = p
    anchor_after = file_sha256(root / study.anchor.artifact)
    if anchor_after != anchor_before:
        raise RuntimeError("the anchor artifact changed during the run")

    run = PoolRun(
        study,
        y,
        cands,
        records,
        artifacts,
        encodings,
        reference,
        scores,
        {
            **verified,
            "vqc_val_rows": len(val),
            "vqc_val_frauds": int(y.sum()),
            "vqc_train_rows": len(train_df),
            "prevalence": prevalence,
            "experiment_config_hash": resolved.config_hash(),
            "study_config_hash": stable_hash(study),
            "anchor_artifact_file_sha256": anchor_after,
            "subsets": {
                k: {
                    "subset_id": r.spec.subset_id,
                    "rows": len(r.row_ids),
                    "frauds": r.n_fraud,
                    "row_ids_sha256": r.row_ids_sha256,
                }
                for k, (r, _) in subsets.items()
            },
        },
        timings,
    )
    t = time.perf_counter()
    run.diversity = diversity(run, n_jobs)
    timings["diversity_s"] = time.perf_counter() - t
    run.power = power_table(run, root)
    t = time.perf_counter()
    run.benchmark = benchmark(run, transpiled, n_jobs)
    timings["benchmark_s"] = time.perf_counter() - t
    run.g3a = g3a(run)
    timings["total_s"] = time.perf_counter() - t_all
    return run


# ----------------------------------------------------------------------- diversity

AXES = ("features", "encoding", "family", "reps", "readout")


def _pair(a: np.ndarray, b: np.ndarray) -> tuple[float, float]:
    return M.spearman(a, b), M.kendall(a, b)


def diversity(run: PoolRun, n_jobs: int) -> dict:
    ids = [m for m in run.records if run.records[m]["qualified"]] + [run.study.anchor.model_id]
    pairs = [(i, j) for a, i in enumerate(ids) for j in ids[a + 1 :]]
    res = Parallel(n_jobs=n_jobs)(delayed(_pair)(run.scores[i], run.scores[j]) for i, j in pairs)
    n = len(ids)
    rho = np.eye(n)
    tau_k = np.eye(n)
    idx = {m: k for k, m in enumerate(ids)}
    for (i, j), (r, k) in zip(pairs, res, strict=True):
        rho[idx[i], idx[j]] = rho[idx[j], idx[i]] = r
        tau_k[idx[i], idx[j]] = tau_k[idx[j], idx[i]] = k
    taus = {m: run.records[m]["tau"] if m in run.records else run.reference[m]["tau"] for m in ids}
    flags = {m: run.scores[m] >= taus[m] for m in ids}
    info = {m: run.records.get(m) for m in ids}
    rows = []
    for (i, j), (r, k) in zip(pairs, res, strict=True):
        if i == run.study.anchor.model_id or j == run.study.anchor.model_id:
            ptype = "with_anchor"
            n_diff = None
        else:
            n_diff = sum(info[i][a] != info[j][a] for a in AXES)
            ptype = (
                "same_structure"
                if n_diff == 0
                else ("one_axis" if n_diff == 1 else "two_plus_axes")
            )
        rows.append(
            {
                "model_a": i,
                "model_b": j,
                "pair_type": ptype,
                "axes_differing": n_diff,
                "spearman": r,
                "kendall": k,
                "mean_abs_diff": float(np.mean(np.abs(run.scores[i] - run.scores[j]))),
                "flag_disagreement": float(np.mean(flags[i] != flags[j])),
            }
        )
    pairs_df = pd.DataFrame(rows)
    dist = np.clip(1 - rho, 0, None)
    np.fill_diagonal(dist, 0)
    order = [ids[k] for k in leaves_list(linkage(squareform(dist, checks=False), "average"))]
    return {"ids": ids, "order": order, "spearman": rho, "kendall": tau_k, "pairs": pairs_df}


def diversity_summary(pairs: pd.DataFrame) -> pd.DataFrame:
    rows = []
    groups = [("all_pool_pairs", pairs[pairs.pair_type != "with_anchor"])]
    groups += [
        (t, pairs[pairs.pair_type == t])
        for t in ("same_structure", "one_axis", "two_plus_axes", "with_anchor")
    ]
    groups += [("between_structure", pairs[pairs.pair_type.isin(["one_axis", "two_plus_axes"])])]
    for name, g in groups:
        if g.empty:
            continue
        rows.append(
            {
                "pair_type": name,
                "n_pairs": len(g),
                "spearman_median": g.spearman.median(),
                "spearman_q05": g.spearman.quantile(0.05),
                "spearman_q95": g.spearman.quantile(0.95),
                "spearman_min": g.spearman.min(),
                "spearman_max": g.spearman.max(),
                "kendall_median": g.kendall.median(),
                "mean_abs_diff_median": g.mean_abs_diff.median(),
                "flag_disagreement_median": g.flag_disagreement.median(),
                "pairs_spearman_ge_0999": int((g.spearman >= 0.999).sum()),
                "pairs_spearman_ge_09999": int((g.spearman >= 0.9999).sum()),
            }
        )
    return pd.DataFrame(rows)


# --------------------------------------------------------------------------- power


def _phase4_within_sd(root: Path) -> dict[str, float]:
    """Median within-model replicate SD of applicable resource-matched deltas (Phase 4)."""
    rep = pd.concat([pd.read_csv(root / T / f"p4_replicates_{a}.csv") for a in ("s1024", "s4096")])
    rm = pd.read_csv(root / T / "p4_resource_matched.csv")
    cells = rm[(rm.comparison_role == "primary") & (rm.applicability != "negative_control")]
    sds = {"auprc": [], "brier": [], "f1": []}
    for (cond, arm, action, comp), _ in cells.groupby(["condition", "arm", "action", "comparator"]):
        a = rep[(rep.condition == cond) & (rep.arm == arm) & (rep.vector == action)].sort_values(
            "replicate"
        )
        b = rep[(rep.condition == cond) & (rep.arm == arm) & (rep.vector == comp)].sort_values(
            "replicate"
        )
        for m in sds:
            sds[m].append(float(np.std(a[m].to_numpy() - b[m].to_numpy(), ddof=1)))
    return {m: float(np.median(v)) for m, v in sds.items()}


def mde_ratio(n_models: int, replicates: int, alpha: float, power: float) -> float:
    """Minimum detectable sigma_b / sigma_w in a balanced one-way random-effects F test.

    Under H1, MS_between / MS_within ~ (1 + R sigma_b^2 / sigma_w^2) F(N-1, N(R-1)), so
    power = P(F > F_crit / (1 + R lambda)); solve for lambda = sigma_b^2 / sigma_w^2.
    """
    df1, df2 = n_models - 1, n_models * (replicates - 1)
    crit = stats.f.ppf(1 - alpha, df1, df2)
    q = stats.f.ppf(1 - power, df1, df2)
    return float(np.sqrt(max(crit / q - 1, 0) / replicates))


def power_table(run: PoolRun, root: Path) -> pd.DataFrame:
    """Minimum detectable between-model SD of a mitigation benefit (one-way random effects)."""
    cfg = run.study.power
    sw = _phase4_within_sd(root)
    n_pool = sum(r["qualified"] for r in run.records.values())
    rows = []
    for n in sorted({*cfg.model_counts, n_pool}):
        for r in cfg.replicate_counts:
            ratio = mde_ratio(n, r, cfg.alpha, cfg.power)
            n_test = max(int(round(cfg.meta_test_fraction * n)), 2)
            d = (stats.norm.ppf(1 - cfg.alpha / 2) + stats.norm.ppf(cfg.power)) / np.sqrt(n_test)
            rows.append(
                {
                    "models": n,
                    "is_pool_size": n == n_pool,
                    "replicates": r,
                    "mde_sigma_b_over_sigma_w": ratio,
                    **{f"mde_sigma_b_{m}": ratio * s for m, s in sw.items()},
                    **{f"phase4_sigma_w_{m}": s for m, s in sw.items()},
                    "meta_test_models": n_test,
                    "controller_vs_rule_mde_sd_units": d,
                }
            )
    return pd.DataFrame(rows)


# ----------------------------------------------------------------------- benchmark


def _bench_one(sid, tc, profile, factors, rows, seed):
    rng = np.random.default_rng(seed)
    params = list(tc.parameters)
    values = np.column_stack(
        [
            rng.uniform(-np.pi / 4, np.pi / 4, rows)
            if p.name.startswith("x")
            else rng.uniform(-np.pi, np.pi, rows)
            for p in params
        ]
    )
    model = gate_noise_model(profile, ("rz", "sx", "x", "cx"))
    out = {}
    for f in factors:
        folded = fold_global(tc, f, ("rz", "sx", "x", "cx"), 0)
        t = time.perf_counter()
        exact_distributions(folded, values, model)
        out[f] = (time.perf_counter() - t) / rows
    return sid, out


def benchmark(run: PoolRun, transpiled: dict, n_jobs: int) -> dict:
    """Simulation time per row (timing only; synthetic bindings; no metrics)."""
    cfg = run.study.benchmark
    profile = next(
        p
        for p in load_component("noise", "anchors_rr_v1").profiles
        if p.profile_id == cfg.noise_profile
    )
    sids = sorted({r["struct_id"] for r in run.records.values() if r["qualified"]})
    res = Parallel(n_jobs=min(cfg.cores, len(sids) or 1))(
        delayed(_bench_one)(sid, transpiled[sid][0], profile, cfg.noise_factors, cfg.rows, k)
        for k, sid in enumerate(sids)
    )
    per_struct = dict(res)
    qualified = [r for r in run.records.values() if r["qualified"]]
    per_model_exact = [
        P4_GATE_SIGNATURES * sum(per_struct[r["struct_id"]].values()) * P4_ROWS for r in qualified
    ]
    finite = P4_FINITE_SAMPLING_CPU_S + P4_FINITE_METRICS_CPU_S
    scen = {
        "phase4_design_full": [e + finite + P4_BOOTSTRAP_CPU_S for e in per_model_exact],
        "no_two_stage_bootstrap": [e + finite for e in per_model_exact],
        "ten_replicates": [e + 0.5 * (finite + P4_BOOTSTRAP_CPU_S) for e in per_model_exact],
    }
    projection = []
    for name, cpu in scen.items():
        total = float(np.sum(cpu))
        projection.append(
            {
                "scenario": name,
                "models": len(cpu),
                "per_model_cpu_hours_mean": float(np.mean(cpu)) / 3600 if cpu else 0.0,
                "pool_cpu_hours": total / 3600,
                "wall_hours_at_cores": total / 3600 / cfg.cores,
                "cores": cfg.cores,
            }
        )
    return {"per_structure_seconds_per_row": per_struct, "projection": projection}


# ---------------------------------------------------------------------------- G3A


def g3a(run: PoolRun) -> dict:
    wall = next(p for p in run.benchmark["projection"] if p["scenario"] == "phase4_design_full")[
        "wall_hours_at_cores"
    ]
    q = [r for r in run.records.values() if r["qualified"]]
    return g3a_rule(
        q,
        run.diversity["pairs"],
        wall,
        run.study.g3a,
        run.context["prevalence"],
        run.study.seeds_per_structure,
        sum(r["role"] == "candidate" for r in run.records.values()),
    )


LEVELS = {
    "features": ["top4", "next4", "pca4"],
    "encoding": ["e3", "e2", "s5"],
    "family": ["real_amplitudes", "efficient_su2"],
    "reps": [1, 2],
    "readout": ["parity", "mean_z"],
}


def g3a_rule(q, pairs, wall, g, prevalence, seeds_per_structure, attempted) -> dict:
    """The registered G3A rule (PREREG_P5A §13) on the qualified records and pair table."""
    n = len(q)
    pool_pairs = pairs[pairs.pair_type != "with_anchor"]
    between = pairs[pairs.pair_type.isin(["one_axis", "two_plus_axes"])]
    med_between = float(between.spearman.median()) if len(between) else 1.0
    ident = float((pool_pairs.spearman >= g.identical_spearman).mean()) if len(pool_pairs) else 1.0
    coverage = {
        f"{axis}={lvl}": sum(r[axis] == lvl for r in q) for axis, lv in LEVELS.items() for lvl in lv
    }

    def share(key, values):
        return max((sum(r[key] == v for r in q) / n) for v in values) if n else 1.0

    shares = {
        "max_family_share": share("family", LEVELS["family"]),
        "max_seed_share": share("seed_index", range(seeds_per_structure)),
        "max_structure_share": share("struct_id", {r["struct_id"] for r in q}),
    }
    median_auprc = float(np.median([r["auprc"] for r in q])) if q else 0.0
    crit = {
        "a_size": n >= g.min_qualified,
        "b_coverage": all(v >= g.min_models_per_level for v in coverage.values()),
        "c_prediction_diversity": med_between <= g.pass_max_median_between_structure_spearman
        and ident < g.pass_max_identical_pair_fraction,
        "d_no_dominance": shares["max_family_share"] <= g.max_family_share
        and shares["max_seed_share"] <= g.max_seed_share
        and shares["max_structure_share"] <= g.max_structure_share,
        "e_clean_signal": median_auprc >= 10 * prevalence,
        "f_feasible": wall <= g.pass_max_projected_wall_hours,
    }
    fail = {
        "too_few_models": n < g.min_qualified,
        "near_identical_predictions": med_between >= g.fail_min_median_between_structure_spearman,
        "mostly_identical_pairs": ident >= g.fail_min_identical_pair_fraction,
        "infeasible_compute": wall > g.fail_min_projected_wall_hours,
    }
    verdict = (
        "FAIL" if any(fail.values()) else ("PASS" if all(crit.values()) else "CONDITIONAL PASS")
    )
    return {
        "verdict": verdict,
        "criteria": crit,
        "fail_conditions": fail,
        "qualified": n,
        "attempted_candidates": attempted,
        "median_between_structure_spearman": med_between,
        "identical_pair_fraction": ident,
        "coverage": coverage,
        "shares": shares,
        "median_auprc": median_auprc,
    }


# ------------------------------------------------------------------------ rendering


def _csv(frame: pd.DataFrame, digits: int = DIGITS) -> str:
    buffer = io.StringIO()
    frame.round(digits).to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def _json(obj) -> str:
    def default(o):
        if isinstance(o, np.integer):
            return int(o)
        if isinstance(o, np.floating):
            return float(o)
        if isinstance(o, np.bool_):
            return bool(o)
        raise TypeError(type(o))

    return json.dumps(obj, indent=2, default=default, sort_keys=False) + "\n"


TIMING = ("train_seconds", "inference_seconds")
REGISTRY_COLS = (
    "model_id",
    "role",
    "struct_id",
    "features",
    "encoding",
    "ansatz",
    "family",
    "reps",
    "readout",
    "seed_index",
    "subset_id",
    "qualified",
    "exclusion_reason",
    "failed_criteria",
    "auprc",
    "auprc_ci_low",
    "auroc",
    "auroc_ci_low",
    "relative_loss_reduction",
    "distinct_scores",
    "aer_max_abs_dz",
    "retrain_identical",
    "model_config_sha256",
    "artifact_sha256",
)
METRIC_COLS = (
    "model_id",
    "role",
    "struct_id",
    "auprc",
    "auprc_ci_low",
    "auprc_ci_high",
    "auroc",
    "auroc_ci_low",
    "auroc_ci_high",
    "brier",
    "ece",
    "tau",
    "precision_at_tau",
    "recall_at_tau",
    "f1_at_tau",
    "initial_bce",
    "final_bce",
    "relative_loss_reduction",
    "nfev",
    "budget_bound",
    "distinct_scores",
    "score_sd",
    "depth",
    "noisy_depth",
    "cx",
    "noisy_1q",
    "trainable_parameters",
    "theta_sha256",
    "prediction_sha256",
    "circuit_qasm3_sha256",
)


def render_pool(run: PoolRun) -> dict[str, str]:
    """Deterministic outputs (tables, artifacts, manifest). Timing lives in render_runtime."""
    out: dict[str, str] = {}
    recs = pd.DataFrame(list(run.records.values()))
    out[T + "p5a_candidates.csv"] = _csv(recs[list(REGISTRY_COLS)])
    pool = recs[recs.qualified | (recs.role == "control")][[c for c in METRIC_COLS if c in recs]]
    ref = pd.DataFrame(list(run.reference.values()))
    table_b = pd.concat([pool, ref.reindex(columns=pool.columns)], ignore_index=True)
    out[T + "p5a_pool_metrics.csv"] = _csv(table_b)
    cov = []
    for axis in AXES:
        for lvl in sorted(recs[axis].unique(), key=str):
            a = recs[(recs.role == "candidate") & (recs[axis] == lvl)]
            cov.append(
                {
                    "axis": axis,
                    "level": lvl,
                    "attempted": len(a),
                    "qualified": int(a.qualified.sum()),
                }
            )
    out[T + "p5a_structural_coverage.csv"] = _csv(pd.DataFrame(cov))
    out[T + "p5a_encoding_diagnostics.csv"] = _csv(pd.DataFrame(run.encodings))
    d = run.diversity
    out[T + "p5a_prediction_diversity.csv"] = _csv(diversity_summary(d["pairs"]))
    for name in ("spearman", "kendall"):
        mat = pd.DataFrame(d[name], index=d["ids"], columns=d["ids"]).loc[d["order"], d["order"]]
        out[T + f"p5a_{name}_matrix.csv"] = _csv(mat.reset_index(names="model_id"), 6)
    out[T + "p5a_power.csv"] = _csv(run.power)
    for mid, art in run.artifacts.items():
        out[A + f"p5a/{mid}.json"] = _json(art)
    manifest = {
        "study_id": run.study.study_id,
        "preregistration": "docs/PREREG_P5A.md (committed d542770 before training)",
        "frozen": True,
        "rule": "primary pool = every qualified candidate; single wave; no later additions "
        "or removals without a new registration",
        "primary_pool": [
            {
                "model_id": r["model_id"],
                "artifact": A + f"p5a/{r['model_id']}.json",
                "artifact_sha256": r["artifact_sha256"],
                "model_config_sha256": r["model_config_sha256"],
                "theta_sha256": r["theta_sha256"],
                "prediction_sha256": r["prediction_sha256"],
                "tau": r["tau"],
                "clean": {k: r[k] for k in ("auprc", "auroc", "brier", "ece", "f1_at_tau")},
                "meta_split": None,
            }
            for r in run.records.values()
            if r["qualified"]
        ],
        "excluded_candidates": [
            {
                "model_id": r["model_id"],
                "artifact_sha256": r["artifact_sha256"],
                "exclusion_reason": r["exclusion_reason"],
                "failed_criteria": r["failed_criteria"],
            }
            for r in run.records.values()
            if r["role"] == "candidate" and not r["qualified"]
        ],
        "diagnostic_controls": [
            {
                "model_id": r["model_id"],
                "artifact_sha256": r["artifact_sha256"],
                "note": "never in the primary pool",
            }
            for r in run.records.values()
            if r["role"] == "control"
        ]
        + [
            {"model_id": k, "artifact_sha256": v["artifact_sha256"], "note": "replayed control"}
            for k, v in run.reference.items()
            if v["role"] == "control"
        ],
        "anchor": {
            "model_id": run.study.anchor.model_id,
            "artifact": run.study.anchor.artifact,
            "artifact_sha256": run.study.anchor.artifact_sha256,
            "note": "historical anchor, replayed only, not counted in the pool",
        },
    }
    out[A + "p5a_pool_manifest.json"] = _json(manifest)
    out[T + "p5a_metadata.json"] = _json(
        {
            "experiment_id": EXPERIMENT_ID,
            "study_id": run.study.study_id,
            "g3a": run.g3a,
            "context": run.context,
            "software": _software(),
            "notes": {
                "threshold": "per-model tau = max-F1 on clean vqc_val (optimistic on vqc_val)",
                "exclusions": "no noise, mitigation, counterfactuals or controller; controller "
                "partitions not read (access phase phase5a)",
                "runtime": "timing-dependent outputs are in p5a_runtime_projection.csv (measured; "
                "not byte-reproducible) and raw runtime.json",
            },
        }
    )
    return out


def render_runtime(run: PoolRun) -> dict[str, str]:
    """Measured (non-deterministic) Table E: runtime and the projected Phase 5B cost."""
    recs = pd.DataFrame([r for r in run.records.values() if r["qualified"]])
    rows = [
        {"item": "training per model (3 restarts), mean s", "value": recs.train_seconds.mean()},
        {"item": "training per model, max s", "value": recs.train_seconds.max()},
        {"item": "vqc_val inference per model, mean s", "value": recs.inference_seconds.mean()},
        {
            "item": "pool training wall s (parallel, incl. retraining check)",
            "value": run.timings.get("training_wall_s", 0.0),
        },
        {"item": "feature-map states wall s", "value": run.timings.get("feature_states_s", 0.0)},
    ]
    for sid, per in sorted(run.benchmark["per_structure_seconds_per_row"].items()):
        for f, s in per.items():
            rows.append({"item": f"Aer DM ms/row, {sid}, lambda {f} (comb-high)", "value": 1e3 * s})
    for p in run.benchmark["projection"]:
        rows.append(
            {"item": f"projection {p['scenario']}: pool CPU hours", "value": p["pool_cpu_hours"]}
        )
        rows.append(
            {
                "item": f"projection {p['scenario']}: wall hours on {p['cores']} cores",
                "value": p["wall_hours_at_cores"],
            }
        )
    return {T + "p5a_runtime_projection.csv": _csv(pd.DataFrame(rows), 3)}
