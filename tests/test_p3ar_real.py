"""Phase 3A-R on the real data: selection and one-time evaluation reproduce from configuration.

Slow (~4 min) and skipped when the gitignored Phase 1 outputs are absent.
"""

from __future__ import annotations

import pytest

from qtrace.config import load_experiment, repo_root
from qtrace.qml.repair_outputs import (
    EXPERIMENT_ID,
    render_evaluation,
    render_selection,
    run_evaluation,
    run_selection,
)

ROOT = repo_root()
PROCESSED = ROOT / "data" / "processed" / "ulb_v1" / "features_preprocessed.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 1 outputs not present locally"),
]


def test_p3ar_selection_reproduces_byte_for_byte():
    run = run_selection(ROOT)
    assert run.context["partitions_read_during_selection"] == ["vqc_train"]
    for rel, text in render_selection(run).items():
        assert text == (ROOT / rel).read_text(), rel


def test_p3ar_evaluation_reproduces_byte_for_byte():
    run = run_evaluation(ROOT)
    for rel, text in render_evaluation(run, load_experiment(EXPERIMENT_ID).baseline).items():
        assert text == (ROOT / rel).read_text(), rel
