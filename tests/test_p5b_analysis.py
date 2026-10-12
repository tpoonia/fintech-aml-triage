"""Phase 5B registered analysis on synthetic counterfactual data: preferred action, failure
definition, heterogeneity statistics, a priori probe categories, the train-fitted category
rule, structure association, the G3B rule and the lockbox refusal."""

from __future__ import annotations

import numpy as np
import pandas as pd
import pytest

from qtrace.counterfactual import analysis as AN
from qtrace.counterfactual.study import load_counterfactual_study


@pytest.fixture(scope="module")
def study():
    return load_counterfactual_study()[1]


BRIER = {
    "clean": {"A0": 0.010, "A1": 0.010, "A2": 0.0101, "A3": 0.0101, "A4": 0.010},
    "ro": {"A0": 0.050, "A1": 0.010, "A2": 0.050, "A3": 0.0105, "A4": 0.050},
    "gate": {"A0": 0.050, "A1": 0.049, "A2": 0.020, "A3": 0.020, "A4": 0.050},
}
PROBE = {"clean": (0.0, 1.0), "ro": (0.05, 1.0), "gate": (0.0, 0.5)}


def synth(split="train", models=6, reps=4, model_effect=0.0, seed=0):
    rng = np.random.default_rng(seed)
    rows = []
    for k in range(models):
        eff = model_effect * (k - models / 2)
        for cond, br in BRIER.items():
            for r in range(reps):
                ro, ga = PROBE[cond]
                for a, b in br.items():
                    noise = rng.normal(0, 1e-5)
                    rows.append(
                        {
                            "model_id": f"m{k}",
                            "struct_id": f"s{k % 3}",
                            "split": split,
                            "partition": "ctrl_train",
                            "condition": cond,
                            "arm": "s1024",
                            "shots_per_circuit": 1024,
                            "replicate": r,
                            "action": a,
                            "brier": b + (eff if a == "A1" else 0) + noise,
                            **{m: 0.5 for m in AN.OUTCOMES if m != "brier"},
                            "probe_readout_error_mean": ro,
                            "probe_gate_contraction": ga,
                        }
                    )
    return pd.DataFrame(rows)


def test_preferred_action_and_failure(study):
    pref = AN.preferred(AN.context_means(synth()), study).set_index("condition")
    assert set(pref.loc["clean"].preferred) == {"A0"}
    assert set(pref.loc["ro"].preferred) == {"A1"}
    assert set(pref.loc["gate"].preferred) == {"A2"}
    row = pref.loc["gate"].iloc[0]
    assert AN.fails(row, "A0", study)  # Brier too high
    assert AN.fails(row, "A3", study)  # within tolerance but more expensive (overspend)
    assert not AN.fails(row, "A2", study)


def test_category_rule_and_universal_failure(study):
    train, val = synth("train"), synth("val", seed=1)
    out = AN.analyse(train, val, study, 9011)
    assert out["rule"]["none|s1024"] == "A0" and out["rule"]["readout|s1024"] == "A1"
    assert out["rule"]["gate|s1024"] == "A2"
    assert out["val"]["rule_failure"] == 0.0
    assert min(out["val"]["universal_failure"].values()) == pytest.approx(2 / 3)
    g = out["g3b"]
    assert g["verdict"] == "FAIL" and g["fail_conditions"]["fixed_rule_sufficient"]


def test_heterogeneity_detects_model_effects(study):
    het0 = AN.heterogeneity(synth(models=8, reps=6, model_effect=0.0), study)
    het1 = AN.heterogeneity(synth(models=8, reps=6, model_effect=0.002), study)
    c0 = het0[(het0.action == "A1") & (het0.condition == "ro")].iloc[0]
    c1 = het1[(het1.action == "A1") & (het1.condition == "ro")].iloc[0]
    assert c1.icc > 0.9 and c1.p_holm < 0.05 and c1.heterogeneous
    assert c0.icc < 0.5
    assert (het1.p_holm >= het1.p).all()


def test_probe_categories_are_a_priori(study):
    rep = pd.DataFrame(
        {
            "probe_readout_error_mean": [0.0, 0.01, 0.0, 0.02],
            "probe_gate_contraction": [1.0, 1.0, 0.5, 0.5],
        }
    )
    assert list(AN.probe_category(rep, study)) == ["none", "readout", "gate", "both"]


def test_structure_association_is_deterministic(study):
    pref = AN.preferred(AN.context_means(synth()), study)
    pref = pref.merge(synth()[["model_id", "struct_id"]].drop_duplicates(), on="model_id")
    pref["stratum"] = pref.condition + "|" + pref.arm
    small = study.model_copy(
        update={"heterogeneity": study.heterogeneity.model_copy(update={"permutations": 200})}
    )
    a = AN.structure_association(pref, small, 9011)
    b = AN.structure_association(pref, small, 9011)
    assert a == b and a["conditional_mi"] == pytest.approx(0.0, abs=1e-12)


def _metrics(**kw):
    base = {
        "max_action_share": 0.5,
        "actions_with_share": 3,
        "improvable_fraction": 0.6,
        "split_half_agreement": 0.9,
        "best_universal_failure_val": 0.6,
        "rule_failure_val": 0.2,
        "rule_gain_val": 0.4,
        "structure_association_p": 0.01,
        "heterogeneous_cell_fraction": 0.5,
    }
    return base | kw


def test_g3b_rule(study):
    g = study.g3b
    assert AN.g3b_rule(_metrics(), g)["verdict"] == "PASS"
    assert AN.g3b_rule(_metrics(structure_association_p=0.3), g)["verdict"] == "CONDITIONAL PASS"
    assert (
        AN.g3b_rule(_metrics(heterogeneous_cell_fraction=0.1), g)["verdict"] == "CONDITIONAL PASS"
    )
    assert AN.g3b_rule(_metrics(rule_failure_val=0.1), g)["verdict"] == "CONDITIONAL PASS"
    assert AN.g3b_rule(_metrics(max_action_share=0.95), g)["verdict"] == "FAIL"
    assert AN.g3b_rule(_metrics(improvable_fraction=0.05), g)["verdict"] == "FAIL"
    assert AN.g3b_rule(_metrics(split_half_agreement=0.5), g)["verdict"] == "FAIL"
    assert AN.g3b_rule(_metrics(rule_gain_val=0.01), g)["verdict"] == "FAIL"
    assert AN.g3b_rule(_metrics(rule_failure_val=0.01), g)["verdict"] == "FAIL"


def test_test_split_is_sealed(tmp_path):
    with pytest.raises(AN.LockboxError):
        AN.load_split(tmp_path, "test")
    synth("val").to_parquet(tmp_path / "counterfactual_train.parquet", index=False)
    with pytest.raises(AN.LockboxError):
        AN.load_split(tmp_path, "train")  # content must match its declared split
