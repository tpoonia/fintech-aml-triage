"""Phase 5C generation mechanics on synthetic panels with the real frozen pool artifacts:
completeness, determinism, Phase 4 pairing, run-time validation, end-to-end build into the
lockbox split, registered report rendering, and the controller-feature leakage guard."""

from __future__ import annotations

import shutil

import numpy as np
import pandas as pd
import pytest

from qtrace.config import repo_root
from qtrace.counterfactual import generate as G
from qtrace.counterfactual import mixed as MX
from qtrace.counterfactual import mixed_generate as MG
from qtrace.counterfactual import probes as PR
from qtrace.counterfactual.features import mixed_controller_table, mixed_prohibited
from qtrace.counterfactual.mixed_study import load_mixed_study
from qtrace.counterfactual.pool_models import load_pool
from qtrace.features import LeakageError, load_registry
from qtrace.mitigation.study import draw_context
from qtrace.utils.seeds import make_rng

ROOT = repo_root()
POINTS = ("g00-r0", "g00-r3", "g05-r1")


@pytest.fixture(scope="module")
def setup():
    resolved, study, base, pool, mit, design = load_mixed_study()
    models = {m.model_id: m for m in load_pool(ROOT, base, pool)}
    cal = {r.point_id: G.calibration_exact(MX.profile_of(r)) for _, r in design.iterrows()}
    return resolved, study, base, pool, mit, design, models, cal


@pytest.fixture(scope="module")
def synth(setup):
    _, study, base, _, mit, design, models, cal = setup
    rng = np.random.default_rng(7)
    angles = rng.uniform(-np.pi / 4, np.pi / 4, size=(300, 4))
    y = np.zeros(300, dtype=np.int64)
    y[:30] = 1
    probe_ang = PR.probe_angles(32, np.pi / 4, make_rng(2307, "model", "t-probe"))
    kw = dict(points=POINTS, arms=("s256", "s1024"), replicates=(0, 1))
    m = models["p5a-top4-e3-ra1-parity-s0"]
    args = (m, angles, y, probe_ang, design, cal, study, base, mit, 9011, None)
    return MG.run_model_mixed(*args, **kw), MG.run_model_mixed(*args, **kw)


def test_completeness_determinism_and_validation(synth):
    a, b = synth
    fa = a["frame"]
    assert len(fa) == len(POINTS) * 2 * 2 * len(MG.ACTIONS)
    assert not fa.duplicated(list(MG.KEYS)).any()
    pd.testing.assert_frame_equal(fa, b["frame"])
    v = a["validation"]
    assert v["passed"] and v["noise_amplification_monotone"] == {"g05": True}
    assert v["exact_a1_gate_free_recovers_clean"] <= 1e-10
    assert {"brier", "ece", "auprc", "f1"} <= set(fa.columns)
    assert not {"spearman", "kendall", "RM9"} & (set(fa.columns) | set(fa.action))


def test_probes_shared_within_replicate_and_track_noise(synth):
    f = synth[0]["frame"]
    probe = [c for c in f.columns if c.startswith("probe_")]
    assert f.groupby(["point_id", "arm", "replicate"])[probe].nunique().eq(1).all().all()
    a0 = f[f.action == "A0"].groupby("point_id")[["probe_gate_contraction"]].mean()
    assert a0.loc["g05-r1"].item() < a0.loc["g00-r0"].item()  # gate noise contracts the probe


def test_draws_pair_with_phase4_draw_context(setup):
    *_, cal = setup
    rng = np.random.default_rng(1)
    probs = {f: rng.dirichlet(np.ones(16), size=20) for f in (1, 3, 5)}

    def r(component):
        return make_rng(9011, "shots", "t", component)

    new = MG.draw_mixed(probs, cal["g05-r1"], 256, (1, 3, 5), r)
    old = draw_context(probs, cal["g05-r1"], 256, (1, 3, 5), r)
    for k in new:
        np.testing.assert_array_equal(new[k], old[k])  # identical paired draws, RM9 dropped


def test_gate_free_plot_has_no_gate_signal(synth):
    f = synth[0]["frame"]
    free = f[(f.gate_plot == "g00") & (f.action == "A0")]
    assert (free.probe_gate_contraction - 1).abs().max() < 0.15  # only shot noise
    g = f[f.point_id == "g00-r0"].pivot_table(
        index=["arm", "replicate"], columns="action", values="brier"
    )
    assert (g["A1"] - g["A0"]).abs().max() < 0.01  # near-zero readout: A1 ~ A0


def test_controller_table_is_leak_free(setup, synth):
    _, study, base, *_ = setup
    f = synth[0]["frame"]
    rep = f[f.action == "A0"]
    static = {
        rep.model_id.iloc[0]: {c: 0 for c in base.static_features if c != "shots_per_circuit"}
    }
    keys, feats = mixed_controller_table(rep, static, base, study, load_registry())
    banned = set(mixed_prohibited(base, study))
    assert not banned & set(feats.columns)
    assert {"point_id", "gate_plot"} <= set(keys.columns) and "point_id" not in feats.columns
    assert {"noise_point_id", "severity_readout", "readout_mean_true"} <= banned
    leaky = base.model_copy(update={"probe_features": (*base.probe_features, "p2")})
    with pytest.raises(LeakageError):
        mixed_controller_table(rep.assign(p2=0.0), static, leaky, study, load_registry())


def _fake_panel(cols):
    def fake(root, dataset, partition, phase="phase5c"):
        assert phase == "phase5c"
        rng = np.random.default_rng(len(partition))
        n = 120
        frame = pd.DataFrame(rng.normal(size=(n, len(cols))), columns=list(cols))
        frame["row_id"] = np.arange(n)
        frame["partition"] = partition
        frame["Class"] = (np.arange(n) < 12).astype(int)
        return frame

    return fake


def test_build_report_end_to_end_on_synthetic_panels(monkeypatch, tmp_path, setup):
    """build -> isolated files -> merge -> lockbox split -> records -> registered report."""
    from qtrace.counterfactual import mixed_report as RP
    from qtrace.counterfactual import mixed_study as MS

    _, study, *_, models, _ = setup
    cols = models["p5a-top4-e3-ra1-parity-s0"].representation.input_columns
    monkeypatch.setattr(MS, "load_panel", _fake_panel(cols))
    ids = (
        *(f"p5a-top4-e3-ra1-parity-s{k}" for k in range(3)),  # train
        *(f"p5a-top4-e3-ra2-parity-s{k}" for k in range(3)),  # val
        "p5a-top4-e3-esu1-parity-s0",  # test
    )
    run = MS.build(
        ROOT,
        tmp_path / "models",
        n_jobs=3,
        model_ids=ids,
        points=("g00-r0", "g00-r2", "g03-r3", "g11-r1"),
        replicates=(0, 1, 2, 3),
    )
    assert {m.split for m in run.models} == {"train", "val", "test"}
    assert all(v["passed"] for v in run.validation.values())
    repo = tmp_path / "repo"
    paths = MS.write_datasets(repo, run)
    assert "lockbox" in str(paths["test"]) and "processed" in str(paths["train"])
    (repo / MS.T).mkdir(parents=True)
    for rel, text in MS.render_build(run).items():
        (repo / rel).write_text(text)
    lock = (repo / MS.T / "p5c_lockbox_manifest.json").read_text()
    assert '"sealed": true' in lock and "brier" not in lock
    shutil.copy(ROOT / MS.T / "p5b_static_features.csv", repo / MS.T)
    out = RP.render_report(RP.run_report(repo))
    assert {MS.T + "p5c_metadata.json", MS.T + "p5c_policy_eval.csv"} <= set(out)
    assert out == RP.render_report(RP.run_report(repo))  # deterministic
    meta = out[MS.T + "p5c_metadata.json"]
    assert '"verdict"' in meta and "esu1-parity" not in out[MS.T + "p5c_policy_eval.csv"]
    assert not (repo / study.processed_dir / "mixed_test.parquet").exists()
