"""Real-dataset checks. Skipped when the gitignored ULB file is absent (e.g. fresh clones).

Marked ``slow``; run with ``uv run pytest -m slow``.
"""

from __future__ import annotations

import io
import json

import pytest

from qtrace.config import load_experiment, repo_root
from qtrace.data.pipeline import committed_metadata, prepare_dataset, summary_table
from qtrace.utils.hashing import file_sha256

RESOLVED = load_experiment("prepare_ulb_v1")
CONFIG = RESOLVED.dataset
RAW = repo_root() / CONFIG.raw_path
TABLES = repo_root() / "results" / "tables"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not RAW.is_file(), reason="ULB dataset not present locally"),
]


@pytest.fixture(scope="module")
def prepared():
    return prepare_dataset(RAW, CONFIG, RESOLVED.spec.seeds)


def test_checksum_matches_recorded_value():
    assert file_sha256(RAW) == CONFIG.expected_sha256


def test_real_data_sanity_checks(prepared):
    assert prepared.passed, prepared.checks
    assert prepared.dedup.rows_after == sum(p.rows for p in prepared.partitions)


def test_real_data_rerun_is_identical(prepared):
    again = prepare_dataset(RAW, CONFIG, RESOLVED.spec.seeds)
    assert again.assignment.equals(prepared.assignment)
    assert committed_metadata(again) == committed_metadata(prepared)


def test_committed_tables_reproduce_byte_for_byte(prepared):
    summary_path = TABLES / f"{CONFIG.dataset_id}_dataset_summary.csv"
    meta_path = TABLES / f"{CONFIG.dataset_id}_phase1_metadata.json"
    if not summary_path.is_file():
        pytest.skip("summary tables not generated yet")
    buffer = io.StringIO()
    summary_table(prepared).to_csv(buffer, index=False, lineterminator="\n")
    assert buffer.getvalue() == summary_path.read_text()
    expected = (
        json.dumps(committed_metadata(prepared), indent=2, sort_keys=True, default=str) + "\n"
    )
    assert expected == meta_path.read_text()
