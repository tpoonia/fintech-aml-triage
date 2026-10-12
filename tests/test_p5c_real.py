"""Phase 5C on the real data: partial regeneration matches the stored dataset row for row, and
the registered report and build records reproduce byte for byte. Slow; skipped when the
gitignored Phase 1/5C data are absent. The sealed test split is never read here."""

from __future__ import annotations

import pandas as pd
import pytest

from qtrace.config import repo_root
from qtrace.counterfactual import mixed_generate as MG
from qtrace.counterfactual.mixed_report import render_report, run_report
from qtrace.counterfactual.mixed_study import T, build, costs_table, load_mixed_study
from qtrace.counterfactual.pool_models import load_pool
from qtrace.counterfactual.study import _csv

ROOT = repo_root()
PROCESSED = ROOT / "results" / "processed" / "phase5c"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(
        not (PROCESSED / "mixed_train.parquet").is_file(),
        reason="Phase 5C datasets not present locally",
    ),
]


def test_partial_regeneration_matches_stored_dataset(tmp_path):
    ids = ("p5a-top4-e3-ra1-parity-s0", "p5a-top4-e3-ra2-parity-s1")  # one train, one val
    kw = dict(points=("g00-r1", "g07-r2", "g13-r0"), arms=("s256",), replicates=(0, 13))
    run = build(ROOT, tmp_path, n_jobs=2, model_ids=ids, **kw)
    for split in ("train", "val"):
        new = run.datasets[split]
        stored = pd.read_parquet(PROCESSED / f"mixed_{split}.parquet")
        keys = new[list(MG.KEYS)].drop_duplicates()
        old = stored.merge(keys, on=list(MG.KEYS)).sort_values(list(MG.KEYS))
        assert len(old) == len(new) and list(old.columns) == list(new.columns)
        pd.testing.assert_frame_equal(new.reset_index(drop=True), old.reset_index(drop=True))


def test_report_and_build_records_reproduce():
    for rel, text in render_report(run_report(ROOT)).items():
        assert text == (ROOT / rel).read_text(), rel
    _, study, base, pool, _, design = load_mixed_study()
    models = load_pool(ROOT, base, pool)
    panels = pd.read_csv(ROOT / T / "p5c_panels.csv").set_index("partition").rows.to_dict()
    assert (
        _csv(costs_table(models, study, base, panels)) == (ROOT / T / "p5c_costs.csv").read_text()
    )
