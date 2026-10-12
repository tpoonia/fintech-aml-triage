"""Configured Phase 2 run: load (VQC partitions only), verify Phase 1, run, render outputs.

``render_committed`` returns the exact text of every committed Phase 2 table, so
the script writes it and a slow test can compare it with the committed files.
"""

from __future__ import annotations

import io
import json
from dataclasses import dataclass
from pathlib import Path

import pandas as pd

from qtrace.classical import tables
from qtrace.classical.runner import EVAL, FIT, Phase2Results, run_phase2
from qtrace.config import load_experiment
from qtrace.config.schemas import ResolvedExperiment
from qtrace.data.access import load_partitions
from qtrace.data.partition import PARTITION
from qtrace.data.preprocess import FittedPreprocessor
from qtrace.data.verify import verify_phase1
from qtrace.utils.hashing import stable_hash
from qtrace.utils.provenance import capture_environment

EXPERIMENT_ID = "phase2_classical"


@dataclass
class Phase2Run:
    resolved: ResolvedExperiment
    results: Phase2Results
    context: dict


def run_configured(root: Path, n_jobs: int = -1) -> Phase2Run:
    resolved = load_experiment(EXPERIMENT_ID)
    spec, dataset, baseline = resolved.spec, resolved.dataset, resolved.baseline
    processed = root / "data" / "processed" / dataset.dataset_id
    fitted = FittedPreprocessor.model_validate_json((processed / "preprocessing.json").read_text())
    frame = load_partitions(processed, "phase2", [FIT, EVAL])  # controller partitions never read
    verified = verify_phase1(root, dataset.dataset_id, frame, fitted, (FIT, EVAL))
    res = run_phase2(
        frame[frame[PARTITION] == FIT],
        frame[frame[PARTITION] == EVAL],
        baseline,
        spec.seeds,
        dataset_id=dataset.dataset_id,
        target=dataset.target_column,
        feature_columns=fitted.output_columns,
        n_jobs=n_jobs,
    )
    packages = capture_environment().packages
    context = {
        "experiment_id": spec.experiment_id,
        "dataset_id": dataset.dataset_id,
        "dataset_sha256": dataset.expected_sha256,
        "experiment_config_sha256": resolved.config_hash(),
        "baseline_config_sha256": stable_hash(baseline),
        "phase1_verification": verified,
        "packages": {k: packages[k] for k in ("scikit-learn", "numpy", "scipy", "pandas")},
    }
    return Phase2Run(resolved, res, context)


def _csv(frame: pd.DataFrame) -> str:
    buffer = io.StringIO()
    frame.to_csv(buffer, index=False, lineterminator="\n")
    return buffer.getvalue()


def render_committed(run: Phase2Run) -> dict[str, str]:
    """Exact contents of every committed Phase 2 table, keyed by file name."""
    res, cfg = run.results, run.resolved.baseline
    out = {
        "phase2_classical_metrics.csv": _csv(tables.metrics_table(res)),
        "phase2_regime_summary.csv": _csv(tables.regime_summary(res)),
        "phase2_representation_comparison.csv": _csv(
            tables.representation_comparison(res, cfg.bootstrap.confidence)
        ),
        "phase2_calibration_bins.csv": _csv(tables.calibration_table(res, cfg)),
        "phase2_pr_curves.csv": _csv(tables.pr_curve_table(res, cfg)),
    }
    meta = tables.metadata(res, cfg, run.context)
    out["phase2_metadata.json"] = json.dumps(meta, indent=2, sort_keys=True, default=str) + "\n"
    return out
