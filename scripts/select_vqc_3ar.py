"""Phase 3A-R stage 1: pre-registered candidate CV and selection on vqc_train ONLY.

Usage:
    uv run python scripts/select_vqc_3ar.py          # reported: clean git tree
    uv run python scripts/select_vqc_3ar.py --dev    # dirty tree allowed

Reads only vqc_train (access phase "phase3ar_select"). Writes the encoding
diagnostics, folds, CV runs and summary, the selection, final training, and the
frozen selected VQC. It never reads vqc_val: that is scripts/evaluate_vqc_3ar.py.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from qtrace.config import repo_root
from qtrace.qml.repair_outputs import EXPERIMENT_ID, render_selection, run_selection
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
    run = run_selection(root)

    written = []
    for rel, text in render_selection(run).items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    raw = root / "results" / "raw" / f"{EXPERIMENT_ID}_selection" / run_id
    raw.mkdir(parents=True, exist_ok=True)
    traces = pd.DataFrame(
        [
            {
                "cand_id": r.cand_id,
                "fold": r.fold,
                "restart": r.restart,
                "evaluation": i + 1,
                "bce": v,
            }
            for r in run.records
            for i, v in enumerate(r.result.trace)
        ]
    )
    traces.to_parquet(raw / "cv_traces.parquet", index=False)
    written.append(raw / "cv_traces.parquet")
    written.append(write_json(raw / "runtime.json", run.timings))

    manifest = RunManifest(
        run_id=run_id,
        experiment_id=f"{EXPERIMENT_ID}_selection",
        protocol_version=run.resolved.spec.protocol_version,
        reporting=reporting,
        status="completed",
        command=sys.argv,
        resolved_config={
            "experiment": run.resolved.model_dump(mode="json"),
            "study": run.study.model_dump(mode="json"),
        },
        config_hash=run.context["study_config_sha256"],
        component_hashes=run.resolved.component_hashes(),
        git=git,
        environment=capture_environment(),
        hardware=capture_hardware(),
        seeds=run.resolved.spec.seeds.model_dump(),
        started_utc=started,
        finished_utc=utc_now(),
        outputs=[
            OutputRecord(path=str(p.relative_to(root)), sha256=file_sha256(p)) for p in written
        ],
    )
    manifest_path = write_manifest(manifest, raw)
    cols = [
        "cand_id",
        "eligible",
        "cv_auprc_mean",
        "cv_auprc_std",
        "cv_auroc_mean",
        "restart_auprc_spread_mean",
    ]
    print(run.summary[cols].round(4).to_string(index=False))
    print(
        f"\nselected: {run.chosen} ({run.reason['decided_by']}); kept restart {run.kept}; "
        f"retrain diff {run.retrain_max_abs_param_diff}"
    )
    print({k: round(v, 2) for k, v in run.timings.items()})
    print(f"manifest: {manifest_path.relative_to(root)} (reporting={reporting})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
