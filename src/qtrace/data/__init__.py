"""ULB data: verification, duplicate audit, deduplication, partitions, preprocessing (Phase 1).

Also provides the VQC-training-subset utility and the evaluation-panel interface.
"""

from qtrace.data.duplicates import DedupReport, DuplicateAudit, audit_duplicates, deduplicate
from qtrace.data.ingest import (
    ROW_ID,
    DataValidationError,
    load_raw,
    validate_schema,
    verify_checksum,
)
from qtrace.data.panels import Panel, PanelSampler, validate_panel_membership
from qtrace.data.partition import PARTITION, allocate_counts, assign_partitions
from qtrace.data.pipeline import PreparedDataset, prepare_dataset
from qtrace.data.preprocess import FittedPreprocessor, fit_preprocessor, transform
from qtrace.data.subset import SubsetRecord, SubsetSpec, build_vqc_training_subset

__all__ = [
    "PARTITION",
    "ROW_ID",
    "DataValidationError",
    "DedupReport",
    "DuplicateAudit",
    "FittedPreprocessor",
    "Panel",
    "PanelSampler",
    "PreparedDataset",
    "SubsetRecord",
    "SubsetSpec",
    "allocate_counts",
    "assign_partitions",
    "audit_duplicates",
    "build_vqc_training_subset",
    "deduplicate",
    "fit_preprocessor",
    "load_raw",
    "prepare_dataset",
    "transform",
    "validate_panel_membership",
    "validate_schema",
    "verify_checksum",
]
