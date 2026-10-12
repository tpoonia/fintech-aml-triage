"""Phase 5B on the real data: partial regeneration matches the stored counterfactual
dataset row for row; the registered report and the generation-independent build records
reproduce byte for byte. Slow; skipped when the gitignored Phase 1/5B data are absent.
The sealed test split is never read here."""

from __future__ import annotations

import pandas as pd
import pytest

from qtrace.config import repo_root
from qtrace.counterfactual import generate as G
from qtrace.counterfactual.pool_models import load_pool
from qtrace.counterfactual.report import render_report, run_report
from qtrace.counterfactual.study import T, _csv, build, load_counterfactual_study

ROOT = repo_root()
PROCESSED = ROOT / "results" / "processed" / "phase5b" / "counterfactual_train.parquet"

pytestmark = [
    pytest.mark.slow,
    pytest.mark.skipif(not PROCESSED.is_file(), reason="Phase 5B datasets not present locally"),
]


def test_partial_regeneration_matches_stored_dataset(tmp_path):
    ids = ("p5a-top4-e3-ra1-parity-s0", "p5a-top4-e3-ra2-parity-s1")  # one train, one val
    kw = dict(conditions=("clean", "ar-050", "dep-high"), arms=("s1024",), replicates=(0, 7))
    run = build(ROOT, tmp_path, n_jobs=2, model_ids=ids, **kw)
    for split in ("train", "val"):
        new = run.datasets[split]
        stored = pd.read_parquet(
            ROOT / "results" / "processed" / "phase5b" / f"counterfactual_{split}.parquet"
        )
        keys = new[list(G.KEYS)].drop_duplicates()
        old = stored.merge(keys, on=list(G.KEYS)).sort_values(list(G.KEYS)).reset_index(drop=True)
        # Top-k overlap columns are named per panel (k = frauds, 1% of rows); the full merge
        # is the union over all panels, so other panels' columns are all-NaN for these rows.
        extra = [c for c in old.columns if c not in new.columns]
        assert all(c.startswith("top") and c.endswith("_overlap") for c in extra), extra
        assert old[extra].isna().all().all()
        assert not set(new.columns) - set(old.columns)
        pd.testing.assert_frame_equal(
            new[[c for c in old.columns if c in new.columns]].reset_index(drop=True),
            old.drop(columns=extra),
        )


def test_report_and_static_records_reproduce():
    for rel, text in render_report(run_report(ROOT)).items():
        assert text == (ROOT / rel).read_text(), rel
    _, study, pool, _, _ = load_counterfactual_study()
    models = load_pool(ROOT, study, pool)
    panels = pd.read_csv(ROOT / T / "p5b_panels.csv").set_index("partition").rows.to_dict()
    assert _csv(G.costs_table(models, study, panels)) == (ROOT / T / "p5b_costs.csv").read_text()
