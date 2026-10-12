"""Phase 5B: build the pre-registered cross-model counterfactual action dataset.

Usage:
    caffeinate -i uv run python scripts/build_counterfactual_5b.py          # reported
    uv run python scripts/build_counterfactual_5b.py --dev

Every frozen pool model x 8 conditions x 2 shot budgets x 20 replicates x (A0-A4, RM9) on
its structure's controller partition (A04). Per-model outputs are written by isolated
workers and merged deterministically. Train/val -> results/processed/phase5b (gitignored);
TEST -> results/lockbox/phase5b (gitignored, sealed). Committed: build records only.
"""

from __future__ import annotations

import argparse
import platform
import resource
import sys

from qtrace.config import load_experiment, repo_root
from qtrace.counterfactual.study import (
    EXPERIMENT_ID,
    build,
    lockbox_hash,
    render_build,
    write_datasets,
)
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
    raw = root / "results" / "raw" / EXPERIMENT_ID / run_id
    run = build(root, raw / "models")
    run.timings["peak_rss_mib_main_process"] = _peak_rss_mib()
    written = []
    for path in write_datasets(root, run).values():
        written.append(path)
    for rel, text in render_build(run).items():
        path = root / rel
        path.write_text(text, encoding="utf-8")
        written.append(path)
    written.append(write_json(raw / "runtime.json", run.timings))
    manifest = RunManifest(
        run_id=run_id,
        experiment_id=EXPERIMENT_ID,
        protocol_version=resolved.spec.protocol_version,
        reporting=reporting,
        status="completed" if all(v["passed"] for v in run.validation.values()) else "failed",
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
    print("rows:", {k: len(v) for k, v in run.datasets.items()})
    print("validation passed:", all(v["passed"] for v in run.validation.values()))
    print("lockbox file sha256:", lockbox_hash(root, run.study))
    print(
        "timings:", {k: round(v, 1) for k, v in run.timings.items() if not k.startswith("model_")}
    )
    print(f"manifest: {manifest_path.relative_to(root)} (reporting={reporting})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
