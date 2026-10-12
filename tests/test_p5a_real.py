"""Phase 5A on the real data: the pool rebuilds byte for byte from configuration.

Slow (several minutes) and skipped when the gitignored Phase 1 outputs are absent. The
measured runtime table (Table E) is timing-dependent and deliberately not compared.
"""

from __future__ import annotations

import json

import pytest

from qtrace.config import repo_root
from qtrace.qml.pool_study import render_pool, run_pool
from qtrace.utils.hashing import file_sha256

ROOT = repo_root()
PROCESSED = ROOT / "data" / "processed" / "ulb_v1" / "features_preprocessed.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 1 outputs not present locally"),
]


def test_p5a_pool_rebuilds_byte_for_byte_and_anchor_is_untouched():
    manifest = json.loads(
        (ROOT / "artifacts" / "model_pool" / "p5a_pool_manifest.json").read_text()
    )
    run = run_pool(ROOT)
    assert run.context["partitions_read"] == ["vqc_train", "vqc_val"]
    assert (
        file_sha256(ROOT / run.study.anchor.artifact) == run.context["anchor_artifact_file_sha256"]
    )
    rendered = render_pool(run)
    assert len(manifest["primary_pool"]) == sum(r["qualified"] for r in run.records.values())
    for rel, text in rendered.items():
        assert text == (ROOT / rel).read_text(), rel
