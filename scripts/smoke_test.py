"""Phase 0 environment smoke test (the only experiment permitted in Phase 0).

Usage:  uv run python scripts/smoke_test.py

Writes ``results/raw/smoke_env/<run_id>/{summary.json,manifest.json}`` (gitignored)
and exits non-zero if any check fails.
"""

from __future__ import annotations

import json
import sys

from qtrace.config import load_experiment, repo_root
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
from qtrace.utils.seeds import derive_seed
from qtrace.utils.smoke import run_smoke_test


def main() -> int:
    root = repo_root()
    resolved = load_experiment("smoke_env")
    spec = resolved.spec
    assert resolved.noise is not None and spec.execution.shots_per_circuit is not None
    profile = resolved.noise.profiles[0]

    started = utc_now()
    run_id = new_run_id(started)
    out_dir = root / "results" / "raw" / spec.experiment_id / run_id

    seed = derive_seed(spec.seeds.shots, "shots", spec.experiment_id, profile.profile_id)
    summary = run_smoke_test(
        profile,
        shots=spec.execution.shots_per_circuit,
        seed=seed,
        basis_gates=spec.execution.basis_gates,
        optimization_level=spec.execution.optimization_level,
    )
    summary_path = write_json(out_dir / "summary.json", summary)

    manifest = RunManifest(
        run_id=run_id,
        experiment_id=spec.experiment_id,
        protocol_version=spec.protocol_version,
        reporting=spec.reporting,
        status="completed" if summary["passed"] else "failed",
        command=sys.argv,
        resolved_config=resolved.model_dump(mode="json"),
        config_hash=resolved.config_hash(),
        component_hashes=resolved.component_hashes(),
        git=capture_git_state(root),
        environment=capture_environment(),
        hardware=capture_hardware(),
        seeds=spec.seeds.model_dump(),
        started_utc=started,
        finished_utc=utc_now(),
        outputs=[
            OutputRecord(path=str(summary_path.relative_to(root)), sha256=file_sha256(summary_path))
        ],
    )
    manifest_path = write_manifest(manifest, out_dir)

    print(json.dumps(summary, indent=2, sort_keys=True))
    print(f"\nmanifest: {manifest_path.relative_to(root)}")
    print(f"config_hash: {manifest.config_hash}")
    print(f"git: commit={manifest.git.commit} dirty={manifest.git.dirty}")
    print("SMOKE TEST", "PASSED" if summary["passed"] else "FAILED")
    return 0 if summary["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
