"""Phase 5C registered design and config: determinism, registered hash, ranges within the
validated anchors, split-plot / sliced-LHS structure, and the inherited Phase 5B setup."""

from __future__ import annotations

import numpy as np
import pytest
from pydantic import ValidationError

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import MixedNoiseAnchors, MixedNoiseStudyConfig
from qtrace.counterfactual import mixed as MX
from qtrace.counterfactual.mixed_study import load_mixed_study


@pytest.fixture(scope="module")
def loaded():
    return load_mixed_study()


def test_design_regenerates_to_the_registered_hash(loaded, monkeypatch):
    from qtrace.counterfactual import mixed_study as MS

    resolved, study, *_, design = loaded
    again = MX.build_design(study.design, resolved.spec.seeds.noise)
    assert MX.design_sha256(again) == study.design.design_sha256 == MX.design_sha256(design)
    other = MX.build_design(study.design, resolved.spec.seeds.noise + 1)
    assert MX.design_sha256(other) != study.design.design_sha256  # the seed matters
    monkeypatch.setattr(MS.MX, "design_sha256", lambda d: "0" * 64)
    with pytest.raises(RuntimeError, match="registered design hash"):
        MS.load_mixed_study()


def test_design_shape_and_split_plot_structure(loaded):
    study, design = loaded[1], loaded[-1]
    k, plots = study.design.readout_points_per_plot, study.design.gate_plots + 1
    assert len(design) == plots * k and design.point_id.is_unique
    assert design.groupby("gate_plot").size().eq(k).all()
    gate = design.groupby("gate_plot")[["s_dep", "s_th"]].nunique()
    assert gate.eq(1).all().all()  # gate noise is constant within a plot
    g00 = design[design.gate_plot == "g00"]
    assert (g00[["s_dep", "s_th", "p1", "p2"]] == 0).all().all() and np.isinf(g00.t1_us).all()
    lhs = design.groupby("gate_plot")[["s_dep", "s_th"]].first().drop(index="g00")
    for col in ("s_dep", "s_th"):  # one gate plot per 1/16 stratum of [0, 3]
        strata = np.floor(lhs[col].to_numpy() / 3 * study.design.gate_plots).astype(int)
        assert sorted(strata) == list(range(study.design.gate_plots))


def test_sliced_readout_design(loaded):
    study, design = loaded[1], loaded[-1]
    k = study.design.readout_points_per_plot
    n = len(design)
    for col, top in (("s_ro", 3.0), ("alpha", 0.5)):
        fine = np.floor(design[col].to_numpy() / top * n).astype(int)
        assert sorted(fine) == list(range(n))  # LHS over all points
        coarse = np.floor(design[col] / top * k).astype(int)
        assert (
            design.assign(c=coarse)
            .groupby("gate_plot")
            .c.apply(lambda c: sorted(c) == list(range(k)))
            .all()
        )  # one point per quarter within every plot


def test_ranges_stay_within_validated_anchors(loaded):
    design = loaded[-1]
    assert design[["s_ro", "s_dep", "s_th"]].min().min() >= 0
    assert design[["s_ro", "s_dep", "s_th"]].max().max() <= 3
    assert design.alpha.between(0, 0.5).all()
    assert design.readout_mean.max() <= 0.05 and design.readout_p10.max() <= 0.075
    assert design.p1.max() <= 0.003 and design.p2.max() <= 0.020
    finite = np.isfinite(design.t1_us)
    assert (design.t1_us[finite] >= 50).all() and (design.t2_us[finite] >= 70).all()
    assert (design.t2_us[finite] <= 2 * design.t1_us[finite] + 1e-9).all()
    assert set(design.region) == set(MX.REGIONS)
    for _, r in design.iterrows():
        MX.profile_of(r)  # every point is a valid NoiseProfile


def test_anchor_interpolation_hits_the_rr_anchors(loaded):
    a = loaded[1].design.anchors
    assert MX._interp(1, a.readout_mean) == 0.005 and MX._interp(3, a.depolarizing_p2) == 0.020
    assert np.isclose(1 / MX._interp(2, a.thermal_rate1_per_us), 100)
    assert np.isclose(1 / MX._interp(3, a.thermal_rate2_per_us), 70)


def test_inherits_phase5b_unchanged(loaded):
    resolved, study, base, pool, mit, _ = loaded
    assert study.base_study == "p5b_v1" and base.study_id == "p5b_v1"
    assert resolved.spec.seeds == load_experiment("phase5b_counterfactual").spec.seeds
    assert base.cost_order == ("A0", "A1", "A4", "A2", "A3")
    assert study.lockbox_dir.startswith("results/lockbox/")


def test_schema_guards():
    good = dict(
        readout_mean=(0, 0.005, 0.02, 0.05),
        depolarizing_p1=(0, 0.0005, 0.001, 0.003),
        depolarizing_p2=(0, 0.005, 0.01, 0.02),
        thermal_rate1_per_us=(0, 0.005, 0.01, 0.02),
        thermal_rate2_per_us=(0, 0.004, 0.0067, 0.0143),
    )
    MixedNoiseAnchors(**good)
    with pytest.raises(ValidationError, match="T2"):
        MixedNoiseAnchors(**{**good, "thermal_rate2_per_us": (0, 0.001, 0.0067, 0.0143)})
    with pytest.raises(ValidationError, match="increase"):
        MixedNoiseAnchors(**{**good, "readout_mean": (0, 0.02, 0.005, 0.05)})
    raw = load_component("mixed_noise_study", "p5c_v1").model_dump()
    for bad in (
        {"lockbox_dir": "results/processed/x"},
        {"tolerance_sensitivity": (0.10,)},
        {"design": {**raw["design"], "severity_max": 4.0}},
        {"design": {**raw["design"], "asymmetry_max": 0.8}},
    ):
        with pytest.raises(ValidationError):
            MixedNoiseStudyConfig(**{**raw, **bad})
