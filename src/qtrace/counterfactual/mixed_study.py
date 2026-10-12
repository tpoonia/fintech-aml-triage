"""Phase 5C build: registered design, panels, parallel per-model generation, lockbox split.

Inherits the Phase 5B pool, structure split, A04 panels (access phase "phase5c"), probe
bindings and features unchanged. Train/val datasets go to gitignored
``results/processed/phase5c``; the TEST split goes to the gitignored lockbox and only its
row count and content hash are committed.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from importlib import metadata as importlib_metadata
from pathlib import Path

import numpy as np
import pandas as pd
from joblib import Parallel, delayed

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import CounterfactualStudyConfig, MixedNoiseStudyConfig
from qtrace.counterfactual import generate as G
from qtrace.counterfactual import mixed as MX
from qtrace.counterfactual import mixed_generate as MG
from qtrace.counterfactual import probes as PR
from qtrace.counterfactual.pool_models import PoolModel, load_pool
from qtrace.counterfactual.study import _csv, _json, load_panel
from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.features import load_registry
from qtrace.mitigation import readout as RO
from qtrace.mitigation import zne as Z
from qtrace.mitigation.costs import action_costs
from qtrace.utils.hashing import file_sha256, stable_hash
from qtrace.utils.seeds import make_rng

EXPERIMENT_ID = "phase5c_mixed_noise"
STUDY_ID = "p5c_v1"
PHASE = "phase5c"
T = "results/tables/"


def load_mixed_study(config_root=None):
    """(resolved experiment, 5C study, 5B base study, pool study, mitigation study, design)."""
    resolved = load_experiment(EXPERIMENT_ID, config_root)
    study: MixedNoiseStudyConfig = load_component("mixed_noise_study", STUDY_ID, config_root)
    base: CounterfactualStudyConfig = load_component(
        "counterfactual_study", study.base_study, config_root
    )
    pool = load_component("pool_study", base.pool_study, config_root)
    mit = load_component("mitigation_study", base.mitigation_study, config_root)
    design = MX.build_design(study.design, resolved.spec.seeds.noise)
    if MX.design_sha256(design) != study.design.design_sha256:
        raise RuntimeError("the regenerated design differs from the registered design hash")
    return resolved, study, base, pool, mit, design


def costs_table(
    models: list[PoolModel],
    study: MixedNoiseStudyConfig,
    base: CounterfactualStudyConfig,
    panel_rows: dict[str, int],
) -> pd.DataFrame:
    """Raw resources per model x arm x action; probe cost in its own columns (not collapsed)."""
    cal_stats = tuple(Z.circuit_statistics(c) for c in RO.calibration_circuits(4))
    rows = []
    for m in models:
        n = panel_rows[m.partition]
        for b in study.shot_budgets:
            s = b.shots_per_circuit
            probe = PR.probe_costs(s, base.gate_probe.bindings, m.folded_stats, cal_stats, n)
            for a in MG.ACTIONS:
                c = action_costs(G.COST_NAME[a], s, n, m.folded_stats, cal_stats)
                rows.append({"model_id": m.model_id, "arm": b.arm_id, "action": a, **c, **probe})
    return pd.DataFrame(rows)


@dataclass
class MixedRun:
    study: MixedNoiseStudyConfig
    base: CounterfactualStudyConfig
    design: pd.DataFrame
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
) -> MixedRun:
    """Generate the Phase 5C dataset (``model_ids``/``subset`` only for tests)."""
    t0 = time.perf_counter()
    resolved, study, base, pool, mit, design = load_mixed_study()
    spec, dataset = resolved.spec, resolved.dataset
    models = load_pool(root, base, pool)
    if model_ids is not None:
        models = [m for m in models if m.model_id in model_ids]
    panels, frames = {}, {}
    for part in sorted({m.partition for m in models}):
        frame = load_panel(root, dataset, part, PHASE)
        frames[part] = frame
        y = frame[dataset.target_column].to_numpy(dtype=np.int64)
        panels[part] = {
            "partition": part,
            "kind": base.panel_kind,
            "rows": len(frame),
            "frauds": int(y.sum()),
            "row_ids_sha256": row_ids_sha256(frame[ROW_ID]),
        }
    cal_exact = {r.point_id: G.calibration_exact(MX.profile_of(r)) for _, r in design.iterrows()}
    probe_ang = PR.probe_angles(  # the Phase 5B probe bindings, unchanged
        base.gate_probe.bindings,
        base.gate_probe.angle_half_width,
        make_rng(spec.seeds.model, "model", base.gate_probe.seed_key),
    )
    out_dir.mkdir(parents=True, exist_ok=True)
    jobs = sorted(models, key=lambda m: (-panels[m.partition]["rows"], m.model_id))
    t = time.perf_counter()
    results = Parallel(n_jobs=n_jobs)(
        delayed(MG.run_model_mixed)(
            m,
            m.angles(frames[m.partition]),
            frames[m.partition][dataset.target_column].to_numpy(dtype=np.int64),
            probe_ang,
            design,
            cal_exact,
            study,
            base,
            mit,
            spec.seeds.shots,
            out_dir,
            **subset,
        )
        for m in jobs
    )
    timings = {"generation_wall_s": time.perf_counter() - t}
    merged = MG.merge([Path(r["path"]) for r in results])
    datasets = {
        s: merged[merged.split == s].reset_index(drop=True) for s in ("train", "val", "test")
    }
    hashes = {s: G.content_sha256(d) for s, d in datasets.items() if len(d)}
    validation = {r["model_id"]: r["validation"] for r in results}
    for r in results:
        for k, v in r["timings"].items():
            timings[f"model_{r['model_id']}_{k}"] = v
    costs = costs_table(models, study, base, {p: v["rows"] for p, v in panels.items()})
    timings["total_s"] = time.perf_counter() - t0
    context = {
        "experiment_config_hash": resolved.config_hash(),
        "study_config_hash": stable_hash(study),
        "base_study_config_hash": stable_hash(base),
        "design_sha256": MX.design_sha256(design),
        "pool_manifest_sha256": base.pool_manifest_sha256,
        "probe_angles_sha256": stable_hash([float(v) for v in probe_ang.ravel()]),
        "registry_deployable": list(load_registry().deployable("qtrace_s")),
    }
    return MixedRun(
        study, base, design, models, panels, validation, costs, datasets, hashes, context, timings
    )


def write_datasets(root: Path, run: MixedRun) -> dict[str, Path]:
    """Train/val -> processed (gitignored); test -> lockbox (gitignored, sealed)."""
    out = {}
    for split, frame in run.datasets.items():
        if not len(frame):
            continue
        base = run.study.lockbox_dir if split == "test" else run.study.processed_dir
        path = root / base / f"mixed_{split}.parquet"
        path.parent.mkdir(parents=True, exist_ok=True)
        frame.to_parquet(path, index=False)
        out[split] = path
    return out


def render_build(run: MixedRun) -> dict[str, str]:
    """Deterministic build records (no outcome of the sealed test split)."""
    study = run.study
    test = run.datasets.get("test")
    return {
        T + "p5c_design.csv": MX.design_csv(run.design),
        T + "p5c_panels.csv": _csv(pd.DataFrame(list(run.panels.values()))),
        T + "p5c_costs.csv": _csv(run.costs),
        T + "p5c_validation.json": _json(
            {
                "per_model": run.validation,
                "all_passed": all(v["passed"] for v in run.validation.values()),
            }
        ),
        T + "p5c_lockbox_manifest.json": _json(
            {
                "sealed": True,
                "location": study.lockbox_dir + "/mixed_test.parquet (gitignored)",
                "rows": 0 if test is None else len(test),
                "models": 0 if test is None else int(test.model_id.nunique()),
                "content_sha256": run.hashes.get("test"),
                "rule": "read only by the single post-freeze final evaluation (protocol §17)",
            }
        ),
        T + "p5c_build.json": _json(
            {
                "experiment_id": EXPERIMENT_ID,
                "study_id": study.study_id,
                "base_study": study.base_study,
                "preregistration": "docs/PREREG_P5C.md (committed before any outcome)",
                "dataset_content_sha256": {k: v for k, v in run.hashes.items() if k != "test"},
                "rows": {k: len(v) for k, v in run.datasets.items()},
                "context": run.context,
                "software": {
                    n: importlib_metadata.version(n)
                    for n in ("qiskit", "qiskit-aer", "numpy", "scipy", "scikit-learn", "pandas")
                },
            }
        ),
    }


def lockbox_hash(root: Path, study: MixedNoiseStudyConfig) -> str | None:
    path = root / study.lockbox_dir / "mixed_test.parquet"
    return file_sha256(path) if path.is_file() else None
