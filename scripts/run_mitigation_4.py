"""Phase 4: pre-registered mitigation characterization of the frozen P3A-R VQC.

Usage:
    uv run python scripts/run_mitigation_4.py          # reported: clean git tree
    uv run python scripts/run_mitigation_4.py --dev

Exact stage -> run-time checks and negative controls -> E08 on folded circuits and
calibration checks -> finite-shot study (1,024 / 4,096 shots x 20 replicates) ->
Tables A-D, hypotheses, G2 (docs/PREREG_P4.md). Reads vqc_val only. Committed tables
are aggregate and deterministic; transaction-level scores and the runtime benchmark
go to gitignored results/raw/.
"""

from __future__ import annotations

import argparse
import platform
import resource
import sys

import pandas as pd

from qtrace.config import load_experiment, repo_root
from qtrace.mitigation.outputs import render_mitigation
from qtrace.mitigation.study import EXPERIMENT_ID, run_mitigation_study
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
    run = run_mitigation_study(root)
    run.timings["peak_rss_mib_main_process"] = _peak_rss_mib()
    written = []
    for rel, text in render_mitigation(run).items():
        path = root / rel
        path.write_text(text, encoding="utf-8")
        written.append(path)
    raw = root / "results" / "raw" / EXPERIMENT_ID / run_id
    raw.mkdir(parents=True, exist_ok=True)
    exact = pd.DataFrame(
        {f"{c}|{v}": s for c, e in run.exact.items() for v, s in e["scores"].items()}
    )
    exact.to_parquet(raw / "exact_scores.parquet", index=False)  # per-row: gitignored
    written.append(raw / "exact_scores.parquet")
    written.append(write_json(raw / "runtime.json", run.timings))
    manifest = RunManifest(
        run_id=run_id,
        experiment_id=EXPERIMENT_ID,
        protocol_version=resolved.spec.protocol_version,
        reporting=reporting,
        status="completed" if run.status == "completed" else "failed",
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
    v = run.validation
    print("status:", run.status)
    for k in (
        "frozen_tau",
        "ideal_computation_preserved",
        "noise_exposure",
        "phase3b_crosscheck",
        "negative_controls",
    ):
        print(f"  {k}: passed={v[k]['passed']}")
    if "e08_folded" in v:
        print("  e08_folded:", {k: r["passed"] for k, r in v["e08_folded"].items()})
        print(
            "  calibration_circuits:",
            {k: r["passed"] for k, r in v["calibration_circuits"].items()},
        )
    if run.analysis:
        print("G2:", run.analysis["g2"]["verdict"])
        for h, r in run.analysis["hypotheses"].items():
            print(f"  {h}: {r['outcome']}")
    print(
        "timings:", {k: round(t, 1) for k, t in run.timings.items() if not k.startswith("finite_")}
    )
    print(f"manifest: {manifest_path.relative_to(root)} (reporting={reporting})")
    return 0 if run.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
