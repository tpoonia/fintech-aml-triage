"""Final-evaluation machinery on synthetic replicate data (no simulator, no sealed data): learned
comparators fit and choose, policies evaluate with paired differences and cluster CIs, the 5B
adapter, fingerprint stability and the pre-specified hypothesis logic and sign conventions."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest
import yaml

from qtrace.config import load_component, repo_root
from qtrace.controller import final_eval as FE
from qtrace.utils.seeds import make_rng

ROOT = repo_root()
HYP = yaml.safe_load((ROOT / "configs/final_test/final_v1.yaml").read_text())["hypotheses"]


@pytest.fixture(scope="module")
def cfgs():
    study = load_component("mixed_noise_study", "p5c_v1")
    base = load_component("counterfactual_study", "p5b_v1")
    statics = pd.read_csv(ROOT / "results/tables/p5b_static_features.csv")
    return study, base, statics


def _synthetic(statics, models, seed=0):
    """Replicate rows where readout noise needs A1/A3 and gate noise needs A2/A3."""
    rng = np.random.default_rng(seed)
    rows, cost_rows = [], []
    probes = [
        "probe_readout_p01_mean",
        "probe_readout_p10_mean",
        "probe_readout_error_mean",
        "probe_readout_asymmetry",
        "probe_readout_se",
        "probe_gate_abs_z_lambda1",
        "probe_gate_abs_z_lambda3",
        "probe_gate_contraction",
        "probe_gate_slope",
        "probe_gate_abs_slope",
        "probe_gate_shot_variance",
    ]
    for m in models:
        st = statics.set_index("model_id").loc[m]
        for p in range(12):
            ro, ga = (p % 3) * 0.02, 1.0 - (p // 3) * 0.15
            for arm, S in (("s1024", 1024), ("s4096", 4096)):
                for rep in range(4):
                    base_b = 0.02 + 0.6 * ro + 0.05 * (1 - ga)
                    br = {
                        "A0": base_b,
                        "A1": base_b - 0.6 * ro,
                        "A2": base_b - 0.04 * (1 - ga),
                        "A3": base_b - 0.6 * ro - 0.04 * (1 - ga),
                        "A4": base_b * 0.999,
                    }
                    pv = dict.fromkeys(probes, 0.0)
                    pv["probe_readout_error_mean"] = ro + rng.normal(0, 0.001)
                    pv["probe_gate_contraction"] = ga + rng.normal(0, 0.01)
                    for a, b in br.items():
                        rows.append(
                            {
                                "model_id": m,
                                "struct_id": st.struct_id,
                                "seed_index": 0,
                                "split": "val",
                                "partition": "ctrl_val",
                                "point_id": f"p{p:02d}",
                                "gate_plot": f"g{p // 3}",
                                "arm": arm,
                                "shots_per_circuit": S,
                                "replicate": rep,
                                "action": a,
                                "brier": b + rng.normal(0, 1e-5),
                                "ece": b,
                                "auprc": 0.3,
                                "auroc": 0.9,
                                "precision": 0.5,
                                "recall": 0.5,
                                "f1": 0.5,
                                "f2": 0.5,
                                **pv,
                            }
                        )
            for arm, S in (("s1024", 1024), ("s4096", 4096)):
                for a, mult in (("A0", 1), ("A1", 1), ("A2", 3), ("A3", 3), ("A4", 3)):
                    extra = 2 * S / 1000 if a in ("A1", "A3") else 0
                    cost_rows.append(
                        {
                            "model_id": m,
                            "arm": arm,
                            "action": a,
                            "shots_per_inference": mult * S + extra,
                            "cx_shots_per_inference": {"A2": 9, "A3": 9, "A4": 3}.get(a, 1) * S,
                            "probe_shots_per_inference": 66 * S / 1000,
                        }
                    )
    return pd.DataFrame(rows), pd.DataFrame(cost_rows).drop_duplicates(
        ["model_id", "arm", "action"]
    )


def test_end_to_end_on_synthetic_data(cfgs):
    study, base, statics = cfgs
    from qtrace.counterfactual import mixed_analysis as AN

    train_models = [
        m for m in statics.model_id if statics.set_index("model_id").loc[m, "split"] == "train"
    ][:6]
    val_models = [
        m for m in statics.model_id if statics.set_index("model_id").loc[m, "split"] == "val"
    ][:6]
    tr, costs_tr = _synthetic(statics, train_models, 1)
    va, costs_va = _synthetic(statics, val_models, 2)
    costs = pd.concat([costs_tr, costs_va])
    eps = study.preferred_relative_tolerance
    orc = AN.oracle(AN.context_means(tr), eps, base.cost_order)
    learned = FE.fit_learned(
        AN.decisions_frame(tr), orc, FE.static_map(statics, base), base, study, eps, seed=7
    )
    rules = AN.fit_rules(AN.decisions_frame(tr), orc, statics, study, base, base.cost_order)
    rng = make_rng(1, "bootstrap", "t")
    res = FE.evaluate_environment(va, costs, statics, rules, learned, base, study, rng, 200)
    pol = res["policies"].set_index(["policy", "arm"])
    assert pol.loc[("oracle", "all")].failure == 0
    assert pol.loc[("R_thr", "all")].failure < pol.loc[("always_A0", "all")].failure
    assert set(res["paired_vs_rthr"].comparator) >= set(FE.LEARNED_SPECS)
    assert set(res["fingerprints"]) == set(FE.LEARNED_SPECS)
    again = FE.evaluate_environment(
        va, costs, statics, rules, learned, base, study, make_rng(1, "bootstrap", "t"), 200
    )
    pd.testing.assert_frame_equal(res["policies"], again["policies"])  # deterministic
    h = FE.hypotheses(res, None, HYP)
    assert set(h) >= {
        "H1_simple_rule_near_oracle",
        "H2_learning_adds_no_meaningful_value",
        "H3_rule_beats_fixed_policies",
    }


def test_from_5b_and_fingerprint():
    df = pd.DataFrame({"condition": ["clean", "clean"], "action": ["A0", "RM9"], "x": [1, 2]})
    out = FE.from_5b(df)
    assert list(out.action) == ["A0"] and out.point_id.iloc[0] == "clean"
    c = pd.DataFrame(
        {
            "model_id": ["m", "m"],
            "point_id": ["a", "b"],
            "arm": ["s", "s"],
            "replicate": [0, 0],
            "choice": ["A1", "A2"],
        }
    )
    assert FE.fingerprint(c) == FE.fingerprint(c.iloc[::-1])
    assert FE.fingerprint(c) != FE.fingerprint(c.assign(choice=["A1", "A3"]))


def _res(material_rthr, regret, diff_material, ci_lo, diff_shots, shots=5000.0):
    rows = [
        {
            "policy": "R_thr",
            "arm": "all",
            "material_failure": material_rthr,
            "mean_rel_brier_regret": regret,
            "mean_total_shots_per_inference": shots,
        }
    ]
    for a in ("A0", "A1", "A2", "A3", "A4"):
        rows.append(
            {
                "policy": f"always_{a}",
                "arm": "all",
                "material_failure": 0.5,
                "mean_rel_brier_regret": 0.1,
                "mean_total_shots_per_inference": 5400.0,
            }
        )
    paired = pd.DataFrame(
        [
            {
                "comparator": n,
                "diff_material": diff_material,
                "diff_material_ci_lo": ci_lo,
                "diff_total_shots_per_inference": diff_shots,
            }
            for n in FE.LEARNED_SPECS
        ]
    )
    return {"policies": pd.DataFrame(rows), "paired_vs_rthr": paired}


def test_hypothesis_sign_conventions():
    neg = FE.hypotheses(_res(0.02, 0.003, 0.001, -0.002, 10.0), None, HYP)
    assert neg["H1_simple_rule_near_oracle"] and neg["H2_learning_adds_no_meaningful_value"]
    assert neg["H3_rule_beats_fixed_policies"]
    better = FE.hypotheses(_res(0.08, 0.003, 0.03, 0.01, 0.0), None, HYP)
    assert not better["H1_simple_rule_near_oracle"]
    assert not better["H2_learning_adds_no_meaningful_value"]  # comparator materially better
    cheaper = FE.hypotheses(_res(0.02, 0.003, 0.0, -0.01, 300.0), None, HYP)
    assert not cheaper["H2_learning_adds_no_meaningful_value"]  # >= 5% fewer shots
    worse_but_cheaper = FE.hypotheses(_res(0.02, 0.003, -0.02, -0.03, 300.0), None, HYP)
    assert worse_but_cheaper["H2_learning_adds_no_meaningful_value"]


def test_rules_survive_the_json_round_trip(cfgs):
    """Frozen rules are read back from JSON; decisions must equal the in-memory rules'."""
    import json

    from qtrace.counterfactual import mixed_analysis as AN

    study, base, statics = cfgs
    models = [
        m for m in statics.model_id if statics.set_index("model_id").loc[m, "split"] == "train"
    ][:4]
    tr, _ = _synthetic(statics, models, 3)
    orc = AN.oracle(AN.context_means(tr), study.preferred_relative_tolerance, base.cost_order)
    dec = AN.decisions_frame(tr)
    rules = AN.fit_rules(dec, orc, statics, study, base, base.cost_order)
    loaded = FE.rules_from_json(json.loads(json.dumps(rules)))
    for name in FE.RULES:
        a = AN.apply_rule(name, rules[name], dec, statics, study)
        b = AN.apply_rule(name, loaded[name], dec, statics, study)
        assert (a.choice.to_numpy() == b.choice.to_numpy()).all()
