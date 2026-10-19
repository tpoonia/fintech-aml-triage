"""Phase 4 on the real data: the mitigation study reproduces from configuration.

Slow (about 6 min) and skipped when the gitignored Phase 1 outputs are absent.
"""

from __future__ import annotations

import json

import pytest

from qtrace.config import repo_root
from qtrace.mitigation.outputs import render_mitigation
from qtrace.mitigation.study import run_mitigation_study
from qtrace.utils.hashing import file_sha256

ROOT = repo_root()
PROCESSED = ROOT / "data" / "processed" / "ulb_v1" / "features_preprocessed.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 1 outputs not present locally"),
]


def test_p4_reproduces_byte_for_byte_and_leaves_frozen_model_untouched():
    committed = json.loads((ROOT / "results" / "tables" / "p4_metadata.json").read_text())
    run = run_mitigation_study(ROOT)
    assert run.status == "completed"
    assert run.context["partitions_read"] == ["vqc_val"]
    assert run.context["artifact_file_sha256_before"] == run.context["artifact_file_sha256_after"]
    assert (
        file_sha256(ROOT / run.study.model.artifact)
        == committed["context"]["artifact_file_sha256_after"]
    )
    for rel, text in render_mitigation(run).items():
        assert text == (ROOT / rel).read_text(), rel
