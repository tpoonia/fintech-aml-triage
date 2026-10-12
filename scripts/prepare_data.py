"""Phase 1: prepare the ULB dataset (verify, audit, deduplicate, partition, preprocess).

Usage:
    uv run python scripts/prepare_data.py          # reported run: requires a clean git tree
    uv run python scripts/prepare_data.py --dev    # allowed on a dirty tree; manifest says "dev"

Outputs
    data/processed/<dataset_id>/   (gitignored) partitions, preprocessed features, fitted params
    results/tables/                (committed)  aggregate summary + metadata, deterministic
    results/raw/<experiment_id>/<run_id>/manifest.json  (gitignored) run record
"""

from __future__ import annotations

import argparse
import sys

from qtrace.config import load_experiment, repo_root
from qtrace.data.pipeline import committed_metadata, prepare_dataset, summary_table
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

EXPERIMENT_ID = "prepare_ulb_v1"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--dev", action="store_true", help="allow a dirty git tree")
    args = parser.parse_args(argv)

    root = repo_root()
    git = capture_git_state(root)
    reporting = "dev" if args.dev else "reported"
    if reporting == "reported" and (git.commit is None or git.dirty):
        print("refusing a reported run on a dirty or uncommitted tree; use --dev", file=sys.stderr)
        return 2

    resolved = load_experiment(EXPERIMENT_ID)
    spec, config = resolved.spec, resolved.dataset
    assert config is not None
    started = utc_now()
    run_id = new_run_id(started)

    prepared = prepare_dataset(root / config.raw_path, config, spec.seeds)
    if not prepared.passed:
        failed = [name for name, ok in prepared.checks.items() if not ok]
        print(f"SANITY CHECKS FAILED: {failed}", file=sys.stderr)
        return 1

    processed = root / "data" / "processed" / config.dataset_id
    processed.mkdir(parents=True, exist_ok=True)
    tables = root / "results" / "tables"
    outputs = []

    path = processed / "partitions.parquet"
    prepared.assignment.merge(
        prepared.frame[["row_id", config.target_column]], on="row_id"
    ).to_parquet(path, index=False)
    outputs.append(path)
    path = processed / "features_preprocessed.parquet"
    prepared.features.to_parquet(path, index=False)
    outputs.append(path)
    outputs.append(
        write_json(processed / "preprocessing.json", prepared.fitted.model_dump(mode="json"))
    )
    outputs.append(
        write_json(processed / "duplicate_audit.json", prepared.audit.model_dump(mode="json"))
    )
    outputs.append(
        write_json(processed / "dedup_report.json", prepared.dedup.model_dump(mode="json"))
    )

    path = tables / f"{config.dataset_id}_dataset_summary.csv"
    summary_table(prepared).to_csv(path, index=False, lineterminator="\n")
    outputs.append(path)
    outputs.append(
        write_json(
            tables / f"{config.dataset_id}_phase1_metadata.json", committed_metadata(prepared)
        )
    )

    manifest = RunManifest(
        run_id=run_id,
        experiment_id=spec.experiment_id,
        protocol_version=spec.protocol_version,
        reporting=reporting,
        status="completed",
        command=sys.argv,
        resolved_config=resolved.model_dump(mode="json"),
        config_hash=resolved.config_hash(),
        component_hashes=resolved.component_hashes(),
        git=git,
        environment=capture_environment(),
        hardware=capture_hardware(),
        seeds=spec.seeds.model_dump(),
        started_utc=started,
        finished_utc=utc_now(),
        outputs=[
            OutputRecord(path=str(p.relative_to(root)), sha256=file_sha256(p)) for p in outputs
        ],
        notes=f"dataset_sha256={prepared.dataset_sha256}",
    )
    manifest_path = write_manifest(manifest, root / "results" / "raw" / spec.experiment_id / run_id)

    print(summary_table(prepared).to_string(index=False))
    print(f"\npreprocessing artifact sha256: {prepared.fitted.artifact_sha256()}")
    print(f"checks: {prepared.checks}")
    print(
        f"manifest: {manifest_path.relative_to(root)} (reporting={reporting}, commit={git.commit})"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
