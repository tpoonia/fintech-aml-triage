"""Phase 3A on the real data: committed tables and the frozen VQC reproduce from configuration.

Slow (~1 min) and skipped when the gitignored Phase 1 outputs are absent.
"""

from __future__ import annotations

import pytest

from qtrace.config import repo_root
from qtrace.qml.phase3a_outputs import render_committed, run_configured

ROOT = repo_root()
PROCESSED = ROOT / "data" / "processed" / "ulb_v1" / "features_preprocessed.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 1 outputs not present locally"),
]


def test_phase3a_outputs_reproduce_byte_for_byte():
    run = run_configured(ROOT)
    assert run.context["phase1_verification"]["partitions_read"] == ["vqc_train", "vqc_val"]
    for rel, text in render_committed(run, ROOT).items():
        assert text == (ROOT / rel).read_text(), rel
