"""Phase 2: classical fraud sanity baselines (fit vqc_train; select + report vqc_val).

Usage:
    uv run python scripts/run_classical_baselines.py          # reported: clean git tree
    uv run python scripts/run_classical_baselines.py --dev    # dirty tree allowed

Requires Phase 1 outputs in data/processed/<dataset_id>/. Reads ONLY the VQC
partitions through qtrace.data.access, after verifying their row-id hashes and
the preprocessing artifact against the committed Phase 1 metadata.

Committed outputs (aggregate only): results/tables/phase2_*
Gitignored outputs: results/raw/phase2_classical/<run_id>/ (manifest, per-row scores)
Figures: scripts/make_phase2_figures.py (reads the committed tables).
"""

from __future__ import annotations

import argparse
import sys

import pandas as pd

from qtrace.classical.pipeline import EXPERIMENT_ID, render_committed, run_configured
from qtrace.config import repo_root
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
    parser.add_argument("--n-jobs", type=int, default=-1)
    args = parser.parse_args(argv)

    root = repo_root()
    git = capture_git_state(root)
    reporting = "dev" if args.dev else "reported"
    if reporting == "reported" and (git.commit is None or git.dirty):
        print("refusing a reported run on a dirty or uncommitted tree; use --dev", file=sys.stderr)
        return 2

    started = utc_now()
    run_id = new_run_id(started)
    run = run_configured(root, n_jobs=args.n_jobs)
    res, spec = run.results, run.resolved.spec

    written = []
    for name, text in render_committed(run).items():
        path = root / "results" / "tables" / name
        path.write_text(text, encoding="utf-8")
        written.append(path)

    raw_dir = root / "results" / "raw" / EXPERIMENT_ID / run_id
    raw_dir.mkdir(parents=True, exist_ok=True)
    scores = pd.DataFrame(
        {"row_id": res.val_row_ids}
        | {f"{r.regime_id}|{r.draw}|{r.model_id}|{r.rep_id}": r.scores for r in res.results}
    )
    scores.to_parquet(raw_dir / "vqc_val_scores.parquet", index=False)  # per-row: gitignored
    written.append(raw_dir / "vqc_val_scores.parquet")
    subsets = {
        f"{ts.regime_id}|{ts.draw}": list(ts.subset.row_ids)
        for ts in res.training_sets
        if ts.subset is not None
    }
    written.append(write_json(raw_dir / "subset_row_ids.json", subsets))  # gitignored

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
    manifest_path = write_manifest(manifest, raw_dir)
    for r in res.results:
        if r.draw == 0:
            lo, hi = r.intervals["auprc"]
            auprc, auroc = r.metrics["auprc"], r.metrics["auroc"]
            print(
                f"{r.regime_id:7s} {r.model_id:7s} {r.rep_id:14s} "
                f"AUPRC {auprc:.3f} [{lo:.3f}, {hi:.3f}]  AUROC {auroc:.3f}"
            )
    location = manifest_path.relative_to(root)
    print(f"\nmanifest: {location} (reporting={reporting}, commit={git.commit})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
