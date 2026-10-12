"""Phase 3A: train, freeze and evaluate the first clean 4-qubit fraud VQC.

Usage:
    uv run python scripts/train_vqc_3a.py          # reported: clean git tree
    uv run python scripts/train_vqc_3a.py --dev    # dirty tree allowed

Reads ONLY the VQC partitions (phase guard "phase3a"), after verifying them and
the preprocessing artifact against the committed Phase 1 metadata.

Committed outputs: results/tables/phase3a_* and artifacts/frozen_vqcs/<vqc_id>.json
Gitignored outputs: results/raw/phase3a_vqc/<run_id>/ (manifest, per-row scores,
subset row ids, runtime benchmark).
Figures: scripts/make_phase3a_figures.py (reads the committed tables).
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from qtrace.config import repo_root
from qtrace.qml.phase3a_outputs import EXPERIMENT_ID, render_committed, run_configured
from qtrace.records import OutputRecord, RunManifest
from qtrace.utils.hashing import file_sha256
from qtrace.utils.provenance import (
    capture_environment,
    capture_git_state,
    capture_hardware,
    new_run_id,
    utc_now,
    write_json,
    write_manifest,
)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dev", action="store_true", help="allow a dirty git tree")
    args = parser.parse_args(argv)

    root = repo_root()
    git = capture_git_state(root)
    reporting = "dev" if args.dev else "reported"
    if reporting == "reported" and (git.commit is None or git.dirty):
        print("refusing a reported run on a dirty or uncommitted tree; use --dev", file=sys.stderr)
        return 2

    started = utc_now()
    run_id = new_run_id(started)
    run = run_configured(root)
    res, spec = run.results, run.resolved.spec

    written = []
    for rel, text in render_committed(run, root).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)

    raw = root / "results" / "raw" / EXPERIMENT_ID / run_id
    raw.mkdir(parents=True, exist_ok=True)
    scores = pd.DataFrame({"vqc": res.vqc.scores} | {r.model_id: r.scores for r in res.classical})
    scores.to_parquet(raw / "vqc_val_scores.parquet", index=False)  # per-row: gitignored
    written.append(raw / "vqc_val_scores.parquet")
    written.append(write_json(raw / "subset_row_ids.json", list(res.subset.row_ids)))
    timings = res.timings | {"hardware": capture_hardware().model_dump()}
    written.append(write_json(raw / "runtime.json", timings))  # host-dependent: never committed

    manifest = RunManifest(
        run_id=run_id,
        experiment_id=spec.experiment_id,
        protocol_version=spec.protocol_version,
        reporting=reporting,
        status="completed",
        command=sys.argv,
        resolved_config=run.resolved.model_dump(mode="json"),
        config_hash=run.resolved.config_hash(),
        component_hashes=run.resolved.component_hashes(),
        git=git,
        environment=capture_environment(),
        hardware=capture_hardware(),
        seeds=spec.seeds.model_dump(),
        started_utc=started,
        finished_utc=utc_now(),
        outputs=[
            OutputRecord(path=str(p.relative_to(root)), sha256=file_sha256(p)) for p in written
        ],
    )
    manifest_path = write_manifest(manifest, raw)

    t = res.training
    print(
        f"features {res.features}; subset {len(res.subset.row_ids)} rows "
        f"({res.subset.n_fraud} fraud); circuit {res.circuit_stats['depth']} depth, "
        f"{res.circuit_stats['two_qubit_gates']} CX"
    )
    print(
        f"COBYLA: {t.nfev} evaluations, status {t.status} ({t.message}); "
        f"BCE {t.initial_loss:.4f} -> {t.final_loss:.4f}"
    )
    for r in [res.vqc, *res.classical]:
        lo, hi = r.intervals["auprc"]
        print(
            f"{r.model_id:7s} AUPRC {r.metrics['auprc']:.3f} [{lo:.3f}, {hi:.3f}] "
            f"AUROC {r.metrics['auroc']:.3f}"
        )
    print({k: round(v, 3) for k, v in res.timings.items()})
    print(
        f"retrain diff {res.retrain_max_abs_param_diff}, replay diff "
        f"{res.replay_max_abs_score_diff}, aer {run.aer_crosscheck}"
    )
    location = manifest_path.relative_to(root)
    print(f"manifest: {location} (reporting={reporting}, commit={git.commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
