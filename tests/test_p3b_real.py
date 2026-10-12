"""Phase 3B on the real data: the controlled-noise study reproduces from configuration.

Slow (several minutes) and skipped when the gitignored Phase 1 outputs are absent.
"""

from __future__ import annotations

import json

import pytest

from qtrace.config import repo_root
from qtrace.noise.study import load_study, render_noise_study, run_noise_study
from qtrace.utils.hashing import file_sha256

ROOT = repo_root()
PROCESSED = ROOT / "data" / "processed" / "ulb_v1" / "features_preprocessed.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 1 outputs not present locally"),
]


def test_p3b_reproduces_byte_for_byte_and_leaves_frozen_models_untouched():
    _, study, _ = load_study()
    committed = json.loads((ROOT / "results" / "tables" / "p3b_metadata.json").read_text())
    run = run_noise_study(ROOT)
    assert run.context["partitions_read"] == ["vqc_val"]
    for m in study.models:
        assert (
            file_sha256(ROOT / m.artifact)
            == committed["models"][m.model_id]["artifact_file_sha256"]
        )
    for rel, text in render_noise_study(run).items():
        assert text == (ROOT / rel).read_text(), rel
