"""Repo hygiene: nothing large, secret or generated is tracked; the research report is intact."""

from __future__ import annotations

import csv
import json
import subprocess
from pathlib import Path

import pytest

from qtrace.utils.hashing import file_sha256

ROOT = Path(__file__).resolve().parents[1]
RESEARCH_REPORT = ROOT / "docs" / "research" / "deep-research-report.md"
RESEARCH_REPORT_SHA256 = "e1a8d0714a73b96ce67ddd05b9bd3108b65e040f6c1fe8311a8e17d80b1274f1"
MAX_TRACKED_BYTES = 1_000_000
# Finished submission documents (decks, PDFs, DOCX) under deliverables/ may be larger (E64).
DELIVERABLE_DIR = "deliverables/"
DELIVERABLE_SUFFIXES = (".pptx", ".pdf", ".docx")
MAX_DELIVERABLE_BYTES = 5_000_000

MUST_IGNORE = [
    "data/raw/creditcard.csv",
    "data/raw/creditcardfraud.zip",
    "data/raw/dataset-metadata.json",
    "data/processed/ulb_v1/partitions.parquet",
    "data/processed/ulb_v1/features_preprocessed.parquet",
    "data/processed/ulb_v1/preprocessing.json",
    "results/raw/prepare_ulb_v1/run/manifest.json",
    ".kaggle/access_token",
    "creditcard.csv",
    "creditcard.zip",
    "results/raw/smoke_env/run/manifest.json",
    "results/processed/deltas.parquet",
    "results/lockbox/meta_test.json",
    "artifacts/cache/transpiled.json",
    ".venv/bin/python",
    ".env",
    ".env.local",
    "kaggle.json",
    "qiskit-ibm.json",
    "configs/local/override.yaml",
    "configs/experiments/mine.local.yaml",
    "secrets.yaml",
    "exact_distributions.npz",
    "state.npy",
    "logs/run.log",
    ".DS_Store",
    ".vscode/settings.json",
    "src/qtrace/__pycache__/x.cpython-312.pyc",
    "deliverables/presentations/build/node_modules/pptxgenjs/package.json",
    "deliverables/presentations/semester/_system/node_modules/pptxgenjs/package.json",
    "deliverables/presentations/semester/_render/2026-10-13-1.png",
    "deliverables/presentations/_render/deck.pdf",
    "deliverables/paper/main.aux",
    "deliverables/paper/main.pdf",
]
MUST_NOT_IGNORE = [
    "src/qtrace/data/__init__.py",
    "pyproject.toml",
    "uv.lock",
    ".python-version",
    "configs/datasets/ulb_v1.yaml",
    "configs/features/registry.yaml",
    "results/tables/summary.csv",
    "results/tables/ulb_v1_dataset_summary.csv",
    "results/tables/ulb_v1_phase1_metadata.json",
    "results/figures/pareto.png",
    "tests/fixtures/ulb_like.csv",
    "docs/research/deep-research-report.md",
    "deliverables/paper/main.tex",
    "deliverables/paper/references.bib",
    "deliverables/paper/Q-TRACE_manuscript.pdf",
    "deliverables/presentations/Q-TRACE_Final_Capstone.pptx",
    "deliverables/presentations/semester/2026-12-08-final/Q-TRACE_2026-12-08_Final-Defense.pptx",
    "deliverables/presentations/semester/2026-09-15/source/deck.js",
]
SECRET_NAMES = {".env", "kaggle.json", "qiskit-ibm.json"}
SECRET_SUFFIXES = (".pem", ".key", ".p12")


def _git(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["git", "-C", str(ROOT), *args], capture_output=True, text=True)


def _in_git_repo() -> bool:
    return _git("rev-parse", "--is-inside-work-tree").stdout.strip() == "true"


needs_git = pytest.mark.skipif(not _in_git_repo(), reason="not a git work tree")


def test_research_report_unchanged():
    assert file_sha256(RESEARCH_REPORT) == RESEARCH_REPORT_SHA256


@needs_git
@pytest.mark.parametrize("path", MUST_IGNORE)
def test_generated_data_and_secrets_are_ignored(path):
    assert _git("check-ignore", "-q", "--no-index", path).returncode == 0, f"{path} not ignored"


@needs_git
@pytest.mark.parametrize("path", MUST_NOT_IGNORE)
def test_source_and_records_are_not_ignored(path):
    assert _git("check-ignore", "-q", "--no-index", path).returncode == 1, f"{path} is ignored"


@needs_git
def test_no_large_or_secret_tracked_files():
    tracked = [p for p in _git("ls-files", "-z").stdout.split("\0") if p]
    for rel in tracked:
        path = ROOT / rel
        if path.is_file():
            if rel.startswith(DELIVERABLE_DIR) and rel.endswith(DELIVERABLE_SUFFIXES):
                assert path.stat().st_size <= MAX_DELIVERABLE_BYTES, f"{rel} exceeds 5 MB"
            else:
                assert path.stat().st_size <= MAX_TRACKED_BYTES, f"{rel} exceeds 1 MB"
        name = Path(rel).name
        assert name not in SECRET_NAMES and not name.endswith(SECRET_SUFFIXES), rel
        assert not rel.startswith(("data/", "results/raw/", "results/processed/")), rel


# Columns that would indicate transaction-level data in a committed table.
TRANSACTION_COLUMNS = {
    "row_id",
    "Time",
    "Amount",
    "Class",
    "score",
    "scores",
    "y_true",
    "y_score",
    "prediction",
    *(f"V{i}" for i in range(1, 29)),
}
MAX_TABLE_ROWS = 2000  # the smallest partition has 28,372 rows; fraud-only dumps are column-checked
MAX_JSON_LIST = 200


def _longest_list(obj) -> int:
    if isinstance(obj, dict):
        return max((_longest_list(v) for v in obj.values()), default=0)
    if isinstance(obj, list):
        return max([len(obj), *(_longest_list(v) for v in obj)])
    return 0


def test_committed_tables_hold_no_transaction_level_data():
    tables = ROOT / "results" / "tables"
    for path in sorted(tables.glob("*.csv")):
        with path.open() as handle:
            rows = list(csv.reader(handle))
        assert rows, path
        assert not TRANSACTION_COLUMNS & set(rows[0]), f"{path.name} has transaction columns"
        assert len(rows) <= MAX_TABLE_ROWS, f"{path.name} has too many rows for an aggregate table"
    for path in sorted(tables.glob("*.json")):
        # Only short lists (feature names, loadings); never per-row values or ids.
        assert _longest_list(json.loads(path.read_text())) <= MAX_JSON_LIST, path.name
