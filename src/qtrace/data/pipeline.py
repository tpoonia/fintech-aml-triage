"""Phase 1 pipeline: verify -> validate -> audit -> deduplicate -> partition -> preprocess.

Only the ``split`` seed stream influences any output of this pipeline.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd

from qtrace.config.schemas import PARTITION_NAMES, DatasetConfig, SeedConfig
from qtrace.data.duplicates import (
    FEATURE_HASH,
    DedupReport,
    DuplicateAudit,
    audit_duplicates,
    deduplicate,
    row_hashes,
)
from qtrace.data.ingest import ROW_ID, SchemaReport, load_raw
from qtrace.data.partition import (
    GROUP_KEY,
    PARTITION,
    PartitionStats,
    StratumAllocation,
    assign_partitions,
    grouping_summary,
    partition_ids,
    stratum_allocations,
    summarize_partitions,
)
from qtrace.data.preprocess import (
    FittedPreprocessor,
    fit_partition_hash,
    fit_preprocessor,
    transform,
)
from qtrace.utils.hashing import stable_hash


@dataclass(frozen=True)
class PreparedDataset:
    config: DatasetConfig
    dataset_sha256: str
    schema: SchemaReport
    audit: DuplicateAudit
    dedup: DedupReport
    frame: pd.DataFrame  # deduplicated raw values + row_id + feature_sha256
    assignment: pd.DataFrame  # row_id, partition, group_sha256
    partitions: list[PartitionStats]
    allocations: list[StratumAllocation]
    grouping: dict[str, Any]
    fitted: FittedPreprocessor
    features: pd.DataFrame  # row_id, partition, transformed features, label
    near_duplicate_groups_across_partitions: int
    checks: dict[str, bool]

    @property
    def passed(self) -> bool:
        return all(self.checks.values())


def _near_duplicates_across_partitions(
    frame: pd.DataFrame, assignment: pd.DataFrame, config
) -> int:
    """Groups identical except Time whose members fall in more than one partition."""
    columns = [c for c in config.feature_columns if c != "Time"]
    work = pd.DataFrame({ROW_ID: frame[ROW_ID].to_numpy(), "nh": row_hashes(frame, columns)})
    work = work.merge(assignment, on=ROW_ID, how="left")
    spans = work.groupby("nh")[PARTITION].nunique()
    return int((spans > 1).sum())


def run_checks(prepared: PreparedDataset) -> dict[str, bool]:
    cfg, frame, assignment = prepared.config, prepared.frame, prepared.assignment
    target = cfg.target_column
    final_ids = set(frame[ROW_ID].tolist())
    assigned = assignment[ROW_ID]
    by_partition = {name: set(partition_ids(assignment, name).tolist()) for name in PARTITION_NAMES}
    pairwise_overlap = sum(
        len(by_partition[a] & by_partition[b])
        for i, a in enumerate(PARTITION_NAMES)
        for b in PARTITION_NAMES[i + 1 :]
    )
    hash_partitions = (
        frame[[ROW_ID, FEATURE_HASH]].merge(assignment, on=ROW_ID).groupby(FEATURE_HASH)[PARTITION]
    )
    labels = frame.set_index(ROW_ID)[target]
    fraud_per_partition = {n: int(labels.loc[list(by_partition[n])].sum()) for n in PARTITION_NAMES}
    train_ids = partition_ids(assignment, cfg.preprocessing.fit_on)
    d = prepared.dedup
    return {
        "row_accounting_consistent": d.rows_before
        - d.rows_removed_conflicting
        - d.rows_removed_exact_duplicates
        == d.rows_after
        == len(frame),
        "every_row_assigned_exactly_once": assigned.is_unique and set(assigned) == final_ids,
        "zero_pairwise_partition_overlap": pairwise_overlap == 0,
        "feature_hashes_unique_after_dedup": frame[FEATURE_HASH].is_unique,
        "zero_duplicate_leakage_across_partitions": bool((hash_partitions.nunique() <= 1).all()),
        "zero_group_crossing_partitions": bool(
            (assignment.groupby(GROUP_KEY)[PARTITION].nunique() == 1).all()
        ),
        "zero_near_duplicates_ignoring_time_across_partitions": (
            prepared.near_duplicate_groups_across_partitions == 0
        ),
        "stratification_within_group_size_bound": all(a.within_bound for a in prepared.allocations),
        "every_partition_contains_fraud": all(v > 0 for v in fraud_per_partition.values()),
        "preprocessing_fit_on_vqc_train_only": (
            prepared.fitted.fit_partition == "vqc_train"
            and prepared.fitted.fit_partition_rows == len(train_ids)
            and prepared.fitted.fit_partition_hash
            == fit_partition_hash(prepared.dataset_sha256, "vqc_train", train_ids)
        ),
        "transformed_rows_match_final": len(prepared.features) == len(frame)
        and prepared.features[ROW_ID].is_unique,
    }


def prepare_dataset(
    raw_path: str | Path, config: DatasetConfig, seeds: SeedConfig
) -> PreparedDataset:
    raw, schema, sha256 = load_raw(raw_path, config)
    audit = audit_duplicates(raw, config)
    frame, dedup = deduplicate(raw, config)  # always before the split (A04)
    assignment = assign_partitions(frame, config, seeds.split)
    partitions = summarize_partitions(frame, assignment, config)
    fitted = fit_preprocessor(frame, assignment, config, sha256)  # corrected vqc_train only
    features = transform(frame, fitted, config.target_column).merge(assignment, on=ROW_ID)
    features = features[[ROW_ID, PARTITION, *fitted.output_columns, config.target_column]]
    prepared = PreparedDataset(
        config=config,
        dataset_sha256=sha256,
        schema=schema,
        audit=audit,
        dedup=dedup,
        frame=frame,
        assignment=assignment,
        partitions=partitions,
        allocations=stratum_allocations(frame, assignment, config),
        grouping=grouping_summary(frame, config),
        fitted=fitted,
        features=features,
        near_duplicate_groups_across_partitions=_near_duplicates_across_partitions(
            frame, assignment, config
        ),
        checks={},
    )
    return PreparedDataset(**{**prepared.__dict__, "checks": run_checks(prepared)})


def summary_table(prepared: PreparedDataset) -> pd.DataFrame:
    """Aggregate counts only: no transaction-level data."""
    d = prepared.dedup

    def row(scope, rows, fraud, target_fraction=None, of_final=False):
        return {
            "scope": scope,
            "rows": rows,
            "fraud": fraud,
            "legit": rows - fraud,
            "prevalence": round(fraud / rows, 8) if rows else None,
            "target_fraction": target_fraction,
            "fraction_of_final": round(rows / d.rows_after, 8) if of_final else None,
        }

    rows = [
        row("original", d.rows_before, d.fraud_before),
        row(
            "removed_conflicting_label_groups",
            d.rows_removed_conflicting,
            d.fraud_removed_conflicting,
        ),
        row(
            "removed_exact_duplicates",
            d.rows_removed_exact_duplicates,
            d.fraud_removed_exact_duplicates,
        ),
        row("final", d.rows_after, d.fraud_after, of_final=True),
        *(
            row(p.partition, p.rows, p.fraud, p.target_fraction, of_final=True)
            for p in prepared.partitions
        ),
    ]
    return pd.DataFrame(rows)


def committed_metadata(prepared: PreparedDataset) -> dict[str, Any]:
    """Deterministic, aggregate-only record for results/tables (no run ids or timestamps)."""
    cfg = prepared.config
    return {
        "dataset_id": cfg.dataset_id,
        "dataset_sha256": prepared.dataset_sha256,
        "dataset_config_sha256": stable_hash(cfg),
        "provenance": cfg.provenance.model_dump(mode="json") if cfg.provenance else None,
        "schema": prepared.schema.model_dump(mode="json"),
        "duplicate_audit": prepared.audit.model_dump(mode="json"),
        "deduplication": prepared.dedup.model_dump(mode="json"),
        "split": {
            "method": cfg.partitions.method,
            "group_key": cfg.partitions.group_key,
            "group_hash": "sha256 of float64 bytes of V1..V28 + Amount (-0.0 -> 0.0)",
            "group_stratum": cfg.partitions.group_stratum,
            "seed_stream": "split",
            "derivation_key": [cfg.dataset_id, "group_partition", "<stratum>"],
            "assignment_rule": "groups sorted by key, permuted, assigned by midpoint "
            "on cumulative largest-remainder targets",
        },
        "grouping": prepared.grouping,
        "stratum_allocations": [a.model_dump(mode="json") for a in prepared.allocations],
        "partitions": [p.model_dump(mode="json") for p in prepared.partitions],
        "near_duplicate_groups_ignoring_time_across_partitions": (
            prepared.near_duplicate_groups_across_partitions
        ),
        "preprocessing": {
            "fitted": prepared.fitted.model_dump(mode="json"),
            "artifact_sha256": prepared.fitted.artifact_sha256(),
        },
        "checks": prepared.checks,
    }
