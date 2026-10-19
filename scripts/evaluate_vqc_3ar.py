"""Phase 3A-R stage 2: ONE-TIME vqc_val evaluation of the frozen selected VQC.

Usage:
    uv run python scripts/evaluate_vqc_3ar.py          # reported: clean git tree
    uv run python scripts/evaluate_vqc_3ar.py --dev

Requires the committed selection (results/tables/p3ar_selection.json and the frozen
artifact). It never revisits selection; re-running reproduces the same numbers.
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from qtrace.config import load_experiment, repo_root
from qtrace.qml.repair_outputs import EXPERIMENT_ID, render_evaluation, run_evaluation
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
    resolved = load_experiment(EXPERIMENT_ID)
    run = run_evaluation(root)
    written = []
    for rel, text in render_evaluation(run, resolved.baseline).items():
        path = root / rel
        path.write_text(text, encoding="utf-8")
        written.append(path)
    raw = root / "results" / "raw" / f"{EXPERIMENT_ID}_evaluation" / run_id
    raw.mkdir(parents=True, exist_ok=True)
    pd.DataFrame({k: r.scores for k, r in run.results.items()}).to_parquet(
        raw / "vqc_val_scores.parquet", index=False
    )  # per-row: gitignored
    written.append(raw / "vqc_val_scores.parquet")
    written.append(write_json(raw / "runtime.json", run.timings))
    manifest = RunManifest(
        run_id=run_id,
        experiment_id=f"{EXPERIMENT_ID}_evaluation",
        protocol_version=resolved.spec.protocol_version,
        reporting=reporting,
        status="completed",
        command=sys.argv,
        resolved_config=resolved.model_dump(mode="json"),
        config_hash=resolved.config_hash(),
        component_hashes=resolved.component_hashes(),
        git=git,
        environment=capture_environment(),
        hardware=capture_hardware(),
        seeds=resolved.spec.seeds.model_dump(),
        started_utc=started,
        finished_utc=utc_now(),
        outputs=[
            OutputRecord(path=str(p.relative_to(root)), sha256=file_sha256(p)) for p in written
        ],
    )
    manifest_path = write_manifest(manifest, raw)
    for key, r in run.results.items():
        lo, hi = r.intervals["auprc"]
        print(
            f"{key:13s} AUPRC {r.metrics['auprc']:.3f} [{lo:.3f}, {hi:.3f}]  "
            f"AUROC {r.metrics['auroc']:.3f}"
        )
    print("sanity:", run.sanity["checks"], "passed:", run.sanity["passed"])
    print(f"manifest: {manifest_path.relative_to(root)} (reporting={reporting})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
