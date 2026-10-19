"""Phase 5C analysis logic on hand-constructed inputs: Oracle and failure, material failure,
rule fitting, noise-only ceiling, label instability, the G3C decision and the lockbox guard."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtrace.config import load_component
from qtrace.counterfactual import mixed_analysis as AN

ORDER = ("A0", "A1", "A4", "A2", "A3")


@pytest.fixture(scope="module")
def study():
    return load_component("mixed_noise_study", "p5c_v1")


def _ctx(briers: dict[tuple, dict[str, float]]) -> pd.DataFrame:
    rows = []
    for (m, p, arm), b in briers.items():
        for a, v in b.items():
            rows.append({"model_id": m, "point_id": p, "arm": arm, "action": a, "brier": v})
    return pd.DataFrame(rows)


def test_oracle_is_cheapest_within_tolerance():
    ctx = _ctx(
        {
            ("m", "p0", "s"): dict(A0=0.0200, A1=0.0195, A2=0.0190, A3=0.0189, A4=0.0199),
            ("m", "p1", "s"): dict(A0=0.0600, A1=0.0300, A2=0.0500, A3=0.0250, A4=0.0600),
            ("m", "p2", "s"): dict(A0=0.0600, A1=0.0590, A2=0.0400, A3=0.0420, A4=0.0600),
        }
    )
    o = AN.oracle(ctx, 0.10, ORDER).set_index("point_id")
    assert o.preferred.to_dict() == {"p0": "A0", "p1": "A3", "p2": "A2"}
    assert o.loc["p1", "reliability_best"] == "A3" and o.loc["p0", "min_brier"] == 0.0189


def _shots(models=("m",), arm="s", S=1000.0, n=10_000):
    rows = []
    for m in models:
        for a, (mult, extra) in {
            "A0": (1, 0),
            "A1": (1, 2),
            "A2": (3, 0),
            "A3": (3, 2),
            "A4": (3, 0),
        }.items():
            rows.append(
                {
                    "model_id": m,
                    "arm": arm,
                    "action": a,
                    "shots_per_inference": mult * S + extra * S / n,
                    "cx_shots_per_inference": {"A2": 9, "A3": 9, "A4": 3}.get(a, 1) * S,
                    "probe_shots_per_inference": 66 * S / n,
                }
            )
    return AN.shots_table(pd.DataFrame(rows))


def test_failure_equals_disagreement_and_material_failure(study):
    ctx = _ctx({("m", "p", "s"): dict(A0=0.060, A1=0.030, A2=0.050, A3=0.0285, A4=0.059)})
    orc = AN.oracle(ctx, 0.10, ORDER)  # min 0.0285; A1 within 10% -> p* = A1
    assert orc.preferred.item() == "A1"
    chosen = pd.DataFrame(
        {
            "model_id": "m",
            "point_id": "p",
            "arm": "s",
            "replicate": range(5),
            "choice": ["A0", "A1", "A4", "A2", "A3"],
        }
    )
    ev = AN.evaluate(chosen, orc, _shots(), study, 0.10, True).set_index("choice")
    assert ev.fail.to_dict() == {"A0": True, "A1": False, "A4": True, "A2": True, "A3": True}
    # A0: Brier 0.060 > 1.2 x 0.0285 (material); A3: costs ~2S more than A1 (material)
    assert ev.material.to_dict() == {"A0": True, "A1": False, "A4": True, "A2": True, "A3": True}
    assert ev.loc["A1", "cost_regret_S"] == 0 and ev.loc["A3", "cost_regret_S"] == pytest.approx(2)
    assert ev.loc["A1", "total_shots_per_inference"] > ev.loc["A1", "action_shots_per_inference"]


def test_near_tie_and_cheap_overspend_are_not_material(study):
    ctx = _ctx({("m", "p", "s"): dict(A0=0.0230, A1=0.0200, A2=0.0201, A3=0.0199, A4=0.0229)})
    orc = AN.oracle(ctx, 0.10, ORDER)
    assert orc.preferred.item() == "A1"
    chosen = pd.DataFrame(
        {"model_id": "m", "point_id": "p", "arm": "s", "replicate": [0, 1], "choice": ["A0", "A3"]}
    )
    ev = AN.evaluate(chosen, orc, _shots(), study, 0.10, False).set_index("choice")
    assert ev.loc["A0", "fail"] and not ev.loc["A0", "material"]  # 0.023 < 1.2 x 0.0199
    assert ev.loc["A3", "fail"] and ev.loc["A3", "material"]  # A3 costs ~2S more than A1


def test_decision_list_recovers_a_threshold_structure():
    rng = np.random.default_rng(0)
    n = 4000
    ro, ga = rng.uniform(0, 0.05, n), rng.uniform(0.3, 1.0, n)
    target = np.select([(ro >= 0.01) & (ga <= 0.8), ro >= 0.01, ga <= 0.8], [4, 1, 3], 0)
    rank = np.array([ORDER.index(a) for a in AN.ACTIONS])
    q = np.linspace(0.025, 0.975, 39)
    fit = AN.fit_decision_list(ro, ga, target, rank, np.quantile(ro, q), np.quantile(ga, q))
    assert abs(fit["t_r"] - 0.01) < 0.003 and abs(fit["t_g"] - 0.8) < 0.04
    assert fit["cells"] == {0: "A0", 1: "A3", 2: "A1", 3: "A4"}  # codes -> ACTIONS order


def test_noise_only_ceiling_counts_model_disagreement():
    rows = []
    for m, s in (("m1", "a"), ("m2", "a"), ("m3", "b")):
        rows.append(
            {"model_id": m, "point_id": "p", "arm": "s", "preferred": "A1" if s == "a" else "A0"}
        )
        rows.append({"model_id": m, "point_id": "q", "arm": "s", "preferred": "A2"})
    out = AN.noise_only_ceiling(pd.DataFrame(rows), {"m1": "a", "m2": "a", "m3": "b"}, ORDER)
    assert out["overall"] == pytest.approx(1 / 6)
    assert out["per_structure"] == {"a": 0.0, "b": 0.5}


def test_label_instability_is_zero_without_replicate_noise():
    rows = []
    for rep in range(10):
        for a, v in dict(A0=0.06, A1=0.03, A2=0.05, A3=0.029, A4=0.06).items():
            rows.append(
                {
                    "model_id": "m",
                    "point_id": "p",
                    "arm": "s",
                    "replicate": rep,
                    "action": a,
                    "brier": v,
                }
            )
    df = pd.DataFrame(rows)
    rng = np.random.default_rng(0)
    assert AN.label_instability(df, 0.10, ORDER, rng, 50) == 0.0
    noisy = df.assign(brier=df.brier + rng.normal(0, 0.01, len(df)))
    assert AN.label_instability(noisy, 0.10, ORDER, rng, 50) > 0.0


def _metrics(**over):
    base = dict(
        max_share_train=0.4,
        max_share_val=0.4,
        actions_useful_both=3,
        best_rule_failure_val=0.25,
        best_rule_material_failure_val=0.15,
        split_half_agreement_train=0.9,
        noise_only_failure_val=0.2,
        noise_only_structures_val=3,
        noise_only_structures_train=5,
        label_instability_val=0.05,
        action_support_ok=True,
        best_rule_max_structure_failure_share_val=0.4,
    )
    return base | over


def test_g3c_verdicts(study):
    g = study.g3c
    assert AN.g3c_rule(_metrics(), g)["verdict"] == "PASS"
    assert AN.g3c_rule(_metrics(best_rule_failure_val=0.03), g)["verdict"] == "FAIL"
    assert AN.g3c_rule(_metrics(best_rule_material_failure_val=0.02), g)["verdict"] == "FAIL"
    assert AN.g3c_rule(_metrics(max_share_val=0.95), g)["verdict"] == "FAIL"
    assert AN.g3c_rule(_metrics(split_half_agreement_train=0.5), g)["verdict"] == "FAIL"
    cond = AN.g3c_rule(_metrics(noise_only_structures_val=1), g)  # single-structure residual
    assert (
        cond["verdict"] == "CONDITIONAL" and not cond["pass_criteria"]["P3_model_noise_interaction"]
    )
    assert AN.g3c_rule(_metrics(best_rule_failure_val=0.12), g)["verdict"] == "CONDITIONAL"
    assert AN.g3c_rule(_metrics(label_instability_val=0.2), g)["verdict"] == "CONDITIONAL"


def test_lockbox_refuses_the_test_split(tmp_path):
    with pytest.raises(AN.LockboxError):
        AN.load_split(tmp_path, "test")
    pd.DataFrame({"split": ["val"]}).to_parquet(tmp_path / "mixed_train.parquet")
    with pytest.raises(AN.LockboxError, match="content"):
        AN.load_split(tmp_path, "train")
