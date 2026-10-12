"""Phase 5B mechanics on synthetic panels with the real frozen pool artifacts: split and
partition isolation, frozen hashes, probes, counterfactual completeness, determinism, costs,
deterministic merge and the controller-feature leakage guard. No transaction data."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtrace.config import repo_root
from qtrace.counterfactual import generate as G
from qtrace.counterfactual import probes as PR
from qtrace.counterfactual.features import check_features, controller_table, feature_names
from qtrace.counterfactual.pool_models import load_pool, split_of
from qtrace.counterfactual.study import load_counterfactual_study
from qtrace.features import LeakageError, load_registry
from qtrace.utils.seeds import make_rng

ROOT = repo_root()


@pytest.fixture(scope="module")
def setup():
    resolved, study, pool, mit, profiles = load_counterfactual_study()
    models = load_pool(ROOT, study, pool)
    return resolved, study, pool, mit, profiles, {m.model_id: m for m in models}


def test_structure_split_and_partition_isolation(setup):
    _, study, pool, _, _, models = setup
    split = split_of(study)
    assert len(split) == 16 and set(split) == {s.struct_id for s in pool.structures}
    assert [len(getattr(study.structure_split, k)) for k in ("train", "val", "test")] == [8, 4, 4]
    by_struct = {}
    for m in models.values():
        by_struct.setdefault(m.struct_id, set()).add((m.split, m.partition))
        assert m.partition == study.partition_of[m.split]
    assert all(len(v) == 1 for v in by_struct.values())  # all seeds of a structure together
    counts = pd.Series([m.split for m in models.values()]).value_counts()
    assert counts.to_dict() == {"train": 32, "val": 16, "test": 16}


def test_frozen_pool_is_verified(setup):
    _, study, pool, _, _, models = setup
    assert len(models) == 64
    bad = study.model_copy(update={"pool_manifest_sha256": "0" * 64})
    with pytest.raises(RuntimeError, match="manifest"):
        load_pool(ROOT, bad, pool)


@pytest.fixture(scope="module")
def synth_run(setup):
    resolved, study, pool, mit, profiles, models = setup
    rng = np.random.default_rng(5)
    angles = rng.uniform(-np.pi / 4, np.pi / 4, size=(120, 4))
    y = np.zeros(120, dtype=np.int64)
    y[:12] = 1
    probe_ang = PR.probe_angles(32, np.pi / 4, make_rng(2307, "model", "t-probe"))
    cal = {c: G.calibration_exact(p) for c, p in profiles.items()}
    kw = dict(conditions=("clean", "ro-sym-high", "dep-high"), arms=("s1024",), replicates=(0, 1))
    m = models["p5a-top4-e3-esu1-mean_z-s0"]
    run1 = G.run_model(m, angles, y, probe_ang, profiles, cal, study, mit, 9011, None, **kw)
    run2 = G.run_model(m, angles, y, probe_ang, profiles, cal, study, mit, 9011, None, **kw)
    return run1, run2


def test_counterfactual_completeness_and_determinism(synth_run):
    a, b = synth_run
    fa, fb = a["frame"], b["frame"]
    assert len(fa) == 3 * 1 * 2 * 6
    assert not fa.duplicated(list(G.KEYS)).any()
    per = fa.groupby(["condition", "arm", "replicate"]).action.apply(set)
    assert all(v == set(G.VECTORS) for v in per)
    pd.testing.assert_frame_equal(fa, fb)
    assert a["validation"]["passed"]


def test_probe_features_behave_and_are_shared_within_a_replicate(synth_run):
    f = synth_run[0]["frame"]
    probe_cols = [c for c in f.columns if c.startswith("probe_")]
    assert f.groupby(["condition", "replicate"])[probe_cols].nunique().max().max() == 1
    clean = f[(f.condition == "clean") & (f.action == "A0")]
    assert (clean.probe_readout_error_mean == 0).all()
    assert np.allclose(clean.probe_gate_contraction, 1.0, atol=0.15)
    ro = f[(f.condition == "ro-sym-high") & (f.action == "A0")]
    assert np.allclose(ro.probe_readout_error_mean, 0.05, atol=0.02)
    dep = f[(f.condition == "dep-high") & (f.action == "A0")]
    assert (dep.probe_gate_contraction < 0.9).all()


def test_clean_readout_mitigation_is_identity(synth_run):
    f = synth_run[0]["frame"]
    c = f[f.condition == "clean"].set_index(["replicate", "action"])
    for r in (0, 1):
        assert c.loc[(r, "A1"), "brier"] == c.loc[(r, "A0"), "brier"]


def test_costs_and_probe_costs(setup):
    _, study, _, _, _, models = setup
    m = models["p5a-top4-e3-ra2-parity-s0"]
    t = G.costs_table([m], study, {m.partition: 1000}).set_index(["arm", "action"])
    a0, a4 = t.loc[("s1024", "A0")], t.loc[("s1024", "A4")]
    assert a4.total_shots == 3 * a0.total_shots and a4.cx_shots == 3 * a0.cx_shots
    assert t.loc[("s1024", "A2")].total_shots == a4.total_shots
    assert t.loc[("s1024", "A2")].cx_shots > a4.cx_shots  # A4 cheaper in CX exposure
    assert a0.probe_gate_shots == 64 * 1024 and a0.probe_readout_shots == 2 * 1024
    assert a0.probe_total_circuit_executions == 66
    assert t.loc[("s1024", "A1")].calibration_shots == 2 * 1024


def test_merge_is_order_independent(tmp_path, synth_run):
    f = synth_run[0]["frame"]
    a = f.assign(model_id="m-a")
    b = f.assign(model_id="m-b")
    pa, pb = tmp_path / "m-a.parquet", tmp_path / "m-b.parquet"
    a.to_parquet(pa, index=False)
    b.to_parquet(pb, index=False)
    m1, m2 = G.merge([pa, pb]), G.merge([pb, pa])
    pd.testing.assert_frame_equal(m1, m2)
    assert G.content_sha256(m1) == G.content_sha256(m2)
    a.to_parquet(pb, index=False)  # duplicate rows must be refused
    with pytest.raises(RuntimeError, match="duplicate"):
        G.merge([pa, pb])


def test_controller_features_are_deployable_and_leak_free(setup, synth_run):
    _, study, _, _, _, models = setup
    reg = load_registry()
    names = feature_names(study)
    check_features(names, study, reg)
    assert not set(names) & set(study.prohibited_features)
    f = synth_run[0]["frame"]
    rep = f[f.action == "A0"]
    m = models["p5a-top4-e3-esu1-mean_z-s0"]
    static = {m.model_id: m.static}
    keys, feats = controller_table(rep, static, study, reg)
    assert list(feats.columns) == list(names) and len(keys) == len(feats)
    leaked = {"model_id", "struct_id", "condition", "brier", "auprc", "preferred", "replicate"}
    assert not leaked & set(feats.columns)
    for bad in ("readout_p01", "noise_family", "model_id", "preferred_action", "p1"):
        with pytest.raises(LeakageError):
            check_features([*names, bad], study, reg)


def test_probe_cannot_use_labels_or_transactions():
    import inspect

    src = inspect.getsource(PR)
    assert "label" not in src.split('"""', 2)[2] and "Class" not in src


def test_build_end_to_end_on_synthetic_panels(monkeypatch, tmp_path, setup):
    """build() -> isolated per-model files -> deterministic merge -> lockbox split -> records."""
    from qtrace.counterfactual import study as ST

    _, study, pool, _, _, models = setup
    cols = models["p5a-top4-e3-ra1-parity-s0"].representation.input_columns

    def fake_panel(root, dataset, partition):
        rng = np.random.default_rng(len(partition))
        n = 80
        frame = pd.DataFrame(rng.normal(size=(n, len(cols))), columns=list(cols))
        frame["row_id"] = np.arange(n) + 10_000 * len(partition)
        frame["partition"] = partition
        frame["Class"] = (np.arange(n) < 8).astype(int)
        return frame

    monkeypatch.setattr(ST, "load_panel", fake_panel)
    ids = ("p5a-top4-e3-ra1-parity-s0", "p5a-top4-e3-ra2-parity-s0", "p5a-top4-e3-esu1-parity-s0")
    run = ST.build(
        ROOT,
        tmp_path / "models",
        n_jobs=2,
        model_ids=ids,
        conditions=("clean", "ar-050"),
        arms=("s1024",),
        replicates=(0,),
    )
    assert {m.split for m in run.models} == {"train", "val", "test"}
    assert {k: len(v) for k, v in run.datasets.items()} == {"train": 12, "val": 12, "test": 12}
    assert sorted(p.name for p in (tmp_path / "models").iterdir()) == sorted(
        f"{i}.parquet" for i in ids
    )
    root2 = tmp_path / "repo"
    paths = ST.write_datasets(root2, run.__class__(**{**run.__dict__, "study": run.study}))
    assert "lockbox" in str(paths["test"]) and "processed" in str(paths["train"])
    rendered = ST.render_build(run)
    lock = rendered[ST.T + "p5b_lockbox_manifest.json"]
    assert '"sealed": true' in lock and "brier" not in lock
    assert run.validation and all(v["passed"] for v in run.validation.values())


def test_report_end_to_end_on_synthetic_panels(monkeypatch, tmp_path, setup):
    """build -> datasets + records in a temporary repo -> registered report renders."""
    from qtrace.counterfactual import report as RP
    from qtrace.counterfactual import study as ST

    _, study, pool, _, _, models = setup
    cols = models["p5a-top4-e3-ra1-parity-s0"].representation.input_columns

    def fake_panel(root, dataset, partition):
        rng = np.random.default_rng(len(partition))
        n = 120
        frame = pd.DataFrame(rng.normal(size=(n, len(cols))), columns=list(cols))
        frame["row_id"] = np.arange(n)
        frame["partition"] = partition
        frame["Class"] = (np.arange(n) < 12).astype(int)
        return frame

    monkeypatch.setattr(ST, "load_panel", fake_panel)
    ids = tuple(f"p5a-top4-e3-ra1-parity-s{k}" for k in range(3)) + tuple(
        f"p5a-top4-e3-ra2-parity-s{k}" for k in range(3)
    )
    run = ST.build(
        ROOT,
        tmp_path / "models",
        n_jobs=3,
        model_ids=ids,
        conditions=("clean", "ro-sym-high", "dep-high"),
        replicates=(0, 1, 2, 3),
    )
    repo = tmp_path / "repo"
    ST.write_datasets(repo, run)
    (repo / ST.T).mkdir(parents=True)
    for rel, text in ST.render_build(run).items():
        (repo / rel).write_text(text)
    monkeypatch.setattr(RP, "load_counterfactual_study", ST.load_counterfactual_study)
    rep = RP.run_report(repo)
    out = RP.render_report(rep)
    assert {
        ST.T + "p5b_metadata.json",
        ST.T + "p5b_heterogeneity.csv",
        ST.T + "p5b_preferred_actions_train.csv",
        ST.T + "p5b_pareto.csv",
    } <= set(out)
    assert out == RP.render_report(RP.run_report(repo))  # deterministic
    assert not (repo / study.processed_dir / "counterfactual_test.parquet").exists()
    meta = out[ST.T + "p5b_metadata.json"]
    assert '"verdict"' in meta and "ctrl_test" not in out[ST.T + "p5b_preferred_actions_val.csv"]
