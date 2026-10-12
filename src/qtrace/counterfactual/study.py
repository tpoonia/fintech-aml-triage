"""Phase 5B build: panels, parallel per-model generation, deterministic merge, lockbox split.

Each model reads only its structure's controller partition (A04; access phase "phase5b").
Train/val datasets go to gitignored ``results/processed/phase5b``; the TEST split goes to
the gitignored lockbox and only its hashes and counts are committed (protocol §17).
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

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import CounterfactualStudyConfig
from qtrace.counterfactual import generate as G
from qtrace.counterfactual import probes as PR
from qtrace.counterfactual.pool_models import PoolModel, load_pool
from qtrace.data.access import load_partitions
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.verify import verify_phase1
from qtrace.features import load_registry
from qtrace.noise.study import CLEAN
from qtrace.utils.hashing import file_sha256, stable_hash
from qtrace.utils.seeds import make_rng

EXPERIMENT_ID = "phase5b_counterfactual"
STUDY_ID = "p5b_v1"
PHASE = "phase5b"
T = "results/tables/"


def load_counterfactual_study(config_root=None):
    resolved = load_experiment(EXPERIMENT_ID, config_root)
    study: CounterfactualStudyConfig = load_component("counterfactual_study", STUDY_ID, config_root)
    pool = load_component("pool_study", study.pool_study, config_root)
    mit = load_component("mitigation_study", study.mitigation_study, config_root)
    profiles = {
        p.profile_id: p
        for sid in mit.noise_sets
        for p in load_component("noise", sid, config_root).profiles
    }
    profiles["clean"] = CLEAN
    return resolved, study, pool, mit, {c: profiles[c] for c in study.conditions}


def load_panel(root: Path, dataset, partition: str, phase: str = PHASE) -> pd.DataFrame:
    """The full controller partition (registered panel), verified against Phase 1, row order."""
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, phase, [partition])
    verify_phase1(root, dataset.dataset_id, frame, fitted, (partition,))
    return frame.sort_values(ROW_ID).reset_index(drop=True)


@dataclass
class BuildRun:
    study: CounterfactualStudyConfig
    models: list[PoolModel]
    panels: dict[str, dict]
    validation: dict[str, dict]
    costs: pd.DataFrame
    datasets: dict[str, pd.DataFrame]
    hashes: dict[str, str]
    context: dict
    timings: dict[str, float] = field(default_factory=dict)


def build(
    root: Path,
    out_dir: Path,
    n_jobs: int = -1,
    model_ids: tuple[str, ...] | None = None,
    **subset,
) -> BuildRun:
    """Generate the counterfactual dataset (``model_ids``/``subset`` only for tests)."""
    t0 = time.perf_counter()
    resolved, study, pool, mit, profiles = load_counterfactual_study()
    spec, dataset = resolved.spec, resolved.dataset
    models = load_pool(root, study, pool)
    if model_ids is not None:
        models = [m for m in models if m.model_id in model_ids]
    panels, frames = {}, {}
    for part in sorted({m.partition for m in models}):
        frame = load_panel(root, dataset, part)
        frames[part] = frame
        y = frame[dataset.target_column].to_numpy(dtype=np.int64)
        panels[part] = {
            "partition": part,
            "kind": study.panel_kind,
            "rows": len(frame),
            "frauds": int(y.sum()),
            "row_ids_sha256": row_ids_sha256(frame[ROW_ID]),
        }
    cal_exact = {c: G.calibration_exact(p) for c, p in profiles.items()}
    probe_ang = PR.probe_angles(
        study.gate_probe.bindings,
        study.gate_probe.angle_half_width,
        make_rng(spec.seeds.model, "model", study.gate_probe.seed_key),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = sorted(models, key=lambda m: (-panels[m.partition]["rows"], m.model_id))
    t = time.perf_counter()
    results = Parallel(n_jobs=n_jobs)(
        delayed(G.run_model)(
            m,
            m.angles(frames[m.partition]),
            frames[m.partition][dataset.target_column].to_numpy(dtype=np.int64),
            probe_ang,
            profiles,
            cal_exact,
            study,
            mit,
            spec.seeds.shots,
            out_dir,
            **subset,
        )
        for m in jobs
    )
    timings = {"generation_wall_s": time.perf_counter() - t}
    merged = G.merge([Path(r["path"]) for r in results])
    datasets = {
        s: merged[merged.split == s].reset_index(drop=True) for s in ("train", "val", "test")
    }
    hashes = {s: G.content_sha256(d) for s, d in datasets.items() if len(d)}
    validation = {r["model_id"]: r["validation"] for r in results}
    for r in results:
        timings[f"model_{r['model_id']}_s"] = r["timings"]["total_s"]
    costs = G.costs_table(models, study, {p: v["rows"] for p, v in panels.items()})
    timings["total_s"] = time.perf_counter() - t0
    context = {
        "experiment_config_hash": resolved.config_hash(),
        "study_config_hash": stable_hash(study),
        "pool_manifest_sha256": study.pool_manifest_sha256,
        "probe_angles_sha256": stable_hash([float(v) for v in probe_ang.ravel()]),
        "registry_deployable": list(load_registry().deployable("qtrace_s")),
    }
    return BuildRun(study, models, panels, validation, costs, datasets, hashes, context, timings)


def write_datasets(root: Path, run: BuildRun) -> dict[str, Path]:
    """Train/val -> processed (gitignored); test -> lockbox (gitignored)."""
    out = {}
    for split, frame in run.datasets.items():
        if not len(frame):
            continue
        base = run.study.lockbox_dir if split == "test" else run.study.processed_dir
        path = root / base / f"counterfactual_{split}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        out[split] = path
    return out


def _csv(frame: pd.DataFrame, digits: int = 9) -> str:
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

    return json.dumps(obj, indent=2, default=default) + "\n"


def render_build(run: BuildRun) -> dict[str, str]:
    """Deterministic build records (no outcomes of the sealed test split)."""
    study = run.study
    out: dict[str, str] = {}
    split_rows = []
    for name in ("train", "val", "test"):
        for sid in getattr(study.structure_split, name):
            ms = [m for m in run.models if m.struct_id == sid]
            st = ms[0].structure if ms else {}
            split_rows.append(
                {
                    "struct_id": sid,
                    "split": name,
                    "partition": study.partition_of[name],
                    "models": len(ms),
                    "features": st.get("features"),
                    "encoding": st.get("encoding"),
                    "ansatz": st.get("ansatz"),
                    "readout": st.get("readout"),
                }
            )
    out[T + "p5b_split.csv"] = _csv(pd.DataFrame(split_rows))
    out[T + "p5b_panels.csv"] = _csv(pd.DataFrame(list(run.panels.values())))
    out[T + "p5b_costs.csv"] = _csv(run.costs)
    statics = pd.DataFrame(
        [
            {"model_id": m.model_id, "struct_id": m.struct_id, "split": m.split, **m.static}
            for m in run.models
        ]
    )
    out[T + "p5b_static_features.csv"] = _csv(statics)
    reg = load_registry()
    defs = []
    for cls, names in (("static", study.static_features), ("probe", study.probe_features)):
        for n in names:
            f = reg.get(n)
            defs.append(
                {
                    "feature": n,
                    "class": cls,
                    "group": f.group,
                    "availability": f.availability,
                    "status": f.status,
                    "description": f.description,
                }
            )
    for n in study.prohibited_features:
        f = reg.get(n)
        defs.append(
            {
                "feature": n,
                "class": "PROHIBITED",
                "group": f.group if f else "",
                "availability": f.availability if f else "",
                "status": "offline_only",
                "description": f.description if f else "",
            }
        )
    out[T + "p5b_feature_definitions.csv"] = _csv(pd.DataFrame(defs))
    out[T + "p5b_validation.json"] = _json(
        {
            "per_model": run.validation,
            "all_passed": all(v["passed"] for v in run.validation.values()),
        }
    )
    test = run.datasets.get("test")
    out[T + "p5b_lockbox_manifest.json"] = _json(
        {
            "sealed": True,
            "location": study.lockbox_dir + "/counterfactual_test.parquet (gitignored)",
            "rows": 0 if test is None else len(test),
            "models": 0 if test is None else int(test.model_id.nunique()),
            "content_sha256": run.hashes.get("test"),
            "rule": "read only by the single post-freeze evaluation script (protocol §17)",
        }
    )
    out[T + "p5b_build.json"] = _json(
        {
            "experiment_id": EXPERIMENT_ID,
            "study_id": study.study_id,
            "preregistration": "docs/PREREG_P5B.md (committed before any outcome)",
            "dataset_content_sha256": {k: v for k, v in run.hashes.items() if k != "test"},
            "rows": {k: len(v) for k, v in run.datasets.items()},
            "context": run.context,
            "software": {
                n: importlib_metadata.version(n)
                for n in ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn", "pandas")
            },
        }
    )
    return out


def lockbox_hash(root: Path, study: CounterfactualStudyConfig) -> str | None:
    path = root / study.lockbox_dir / "counterfactual_test.parquet"
    return file_sha256(path) if path.is_file() else None
