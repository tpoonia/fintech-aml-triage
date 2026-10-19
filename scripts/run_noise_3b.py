"""Phase 3B: pre-registered controlled-noise characterization of the frozen VQCs.

Usage:
    uv run python scripts/run_noise_3b.py          # reported: clean git tree
    uv run python scripts/run_noise_3b.py --dev

Stage 1 exact distributions -> negative control -> E08 -> Stage 2 finite-shot pilot
-> A13 labels and G1 (docs/PREREG_P3B.md). Reads vqc_val only. Committed tables are
aggregate and deterministic; transaction-level scores/distributions and the runtime
benchmark go to gitignored results/raw/.
"""

from __future__ import annotations

import argparse
import sys

import numpy as np
import pandas as pd

from qtrace.config import load_experiment, repo_root
from qtrace.noise.study import EXPERIMENT_ID, render_noise_study, run_noise_study
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
    run = run_noise_study(root)
    written = []
    for rel, text in render_noise_study(run).items():
        path = root / rel
        path.write_text(text, encoding="utf-8")
        written.append(path)
    raw = root / "results" / "raw" / EXPERIMENT_ID / run_id
    raw.mkdir(parents=True, exist_ok=True)
    for mid, mr in run.models.items():  # per-row: gitignored
        scores = pd.DataFrame({"row_id": run.row_ids, **mr.scores})
        scores.to_parquet(raw / f"{mid}_exact_scores.parquet", index=False)
        np.savez_compressed(raw / f"{mid}_exact_distributions.npz", **mr.probs)
        written += [raw / f"{mid}_exact_scores.parquet", raw / f"{mid}_exact_distributions.npz"]
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
    for mid, mr in run.models.items():
        print(
            f"{mid}: tau={mr.tau:.4f} clean-vs-engine max|dz|={mr.clean_crosscheck_max_abs_z:.1e}"
        )
        for pid, m in mr.metrics.items():
            labels = ",".join(k for k, v in mr.labels[pid].items() if v) or "none"
            print(
                f"  {pid:14s} dAUPRC {m['delta_auprc']:+.4f} dAUROC {m['delta_auroc']:+.4f} "
                f"rho {m['spearman']:.6f} top47 {m['top47_overlap']:.3f} "
                f"cross {m['crossing_fraction']:.4f} [{labels}]"
            )
    print(
        "negative control:",
        {k: v["passed"] for r in run.models.values() for k, v in r.negative_control.items()},
    )
    print("E08:", {k: v["passed"] for k, v in run.e08.items()})
    print("status:", run.status, "| G1:", run.g1["verdict"] if run.g1 else "not issued")
    print("timings:", {k: round(v, 2) for k, v in run.timings.items()})
    print(f"manifest: {manifest_path.relative_to(root)} (reporting={reporting})")
    return 0 if run.status == "completed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
