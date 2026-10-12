"""Phase 2 on the real data: committed tables must reproduce from configuration.

Slow (~1.5 min) and skipped when the gitignored Phase 1 outputs are absent.
"""

from __future__ import annotations

import pytest

from qtrace.classical.pipeline import render_committed, run_configured
from qtrace.config import repo_root

ROOT = repo_root()
PROCESSED = ROOT / "data" / "processed" / "ulb_v1" / "features_preprocessed.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 1 outputs not present locally"),
]


def test_phase2_tables_reproduce_byte_for_byte():
    run = run_configured(ROOT)
    assert run.context["phase1_verification"]["partitions_read"] == ["vqc_train", "vqc_val"]
    for name, text in render_committed(run).items():
        assert text == (ROOT / "results" / "tables" / name).read_text(), name
