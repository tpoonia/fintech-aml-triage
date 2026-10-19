"""Phase 5A: build, qualify and freeze the pre-registered independent VQC pool.

Usage:
    uv run python scripts/build_pool_5a.py          # reported: clean git tree
    uv run python scripts/build_pool_5a.py --dev

Fits on vqc_train, qualifies on clean vqc_val (docs/PREREG_P5A.md). Writes the frozen
model artifacts and manifest (artifacts/model_pool/), deterministic tables
(results/tables/p5a_*), the measured runtime table, and raw runtime/scores.
No noise, no mitigation, no controller; controller partitions are never read.
"""

from __future__ import annotations

import argparse
import platform
import resource
import sys

import pandas as pd

from qtrace.config import load_experiment, repo_root
from qtrace.qml.pool_study import EXPERIMENT_ID, render_pool, render_runtime, run_pool
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


def _peak_rss_mib() -> float:
    rss = resource.getrusage(resource.RUSAGE_SELF).ru_maxrss
    return rss / 2**20 if platform.system() == "Darwin" else rss / 2**10


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
    run = run_pool(root)
    run.timings["peak_rss_mib_main_process"] = _peak_rss_mib()
    written = []
    for rel, text in {**render_pool(run), **render_runtime(run)}.items():
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(text, encoding="utf-8")
        written.append(path)
    raw = root / "results" / "raw" / EXPERIMENT_ID / run_id
    raw.mkdir(parents=True, exist_ok=True)
    pd.DataFrame(run.scores).to_parquet(raw / "clean_vqc_val_scores.parquet", index=False)
    written.append(raw / "clean_vqc_val_scores.parquet")  # per-row: gitignored
    written.append(
        write_json(
            raw / "runtime.json",
            {
                **run.timings,
                "per_model": {
                    m: {
                        "train_seconds": r["train_seconds"],
                        "inference_seconds": r["inference_seconds"],
                    }
                    for m, r in run.records.items()
                },
                "benchmark": run.benchmark,
            },
        )
    )
    manifest = RunManifest(
        run_id=run_id,
        experiment_id=EXPERIMENT_ID,
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
    g = run.g3a
    print(f"attempted {g['attempted_candidates']}, qualified {g['qualified']}")
    excl = [
        (m, r["exclusion_reason"])
        for m, r in run.records.items()
        if r["role"] == "candidate" and not r["qualified"]
    ]
    print("excluded:", excl)
    print("G3A:", g["verdict"], g["criteria"], "| fail:", g["fail_conditions"])
    print(
        "median between-structure Spearman:",
        round(g["median_between_structure_spearman"], 4),
        "| identical-pair fraction:",
        round(g["identical_pair_fraction"], 4),
    )
    print("projection:", run.benchmark["projection"])
    print("timings:", {k: round(v, 1) for k, v in run.timings.items()})
    print(f"manifest: {manifest_path.relative_to(root)} (reporting={reporting})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
