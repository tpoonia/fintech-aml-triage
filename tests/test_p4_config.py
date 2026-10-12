"""Phase 4 pre-registration: the study config is internally consistent and matches Phase 3B."""

from __future__ import annotations

import json

import pytest
from pydantic import ValidationError

from qtrace.config import load_component, load_experiment, repo_root
from qtrace.config.schemas import MitigationStudyConfig, ZNEStudyConfig

ROOT = repo_root()


@pytest.fixture(scope="module")
def study():
    return load_component("mitigation_study", "p4_v1")


def test_conditions_are_registered_phase3b_profiles_with_identical_parameters(study):
    p3b = {
        p.profile_id: p for sid in study.noise_sets for p in load_component("noise", sid).profiles
    }
    assert study.conditions[0] == "clean" and len(study.conditions) == 8
    assert set(study.conditions[1:]) <= set(p3b)
    required = {
        "ro-sym-high",
        "ar-020",
        "ar-050",
        "dep-high",
        "th-high",
        "comb-medium",
        "comb-high",
    }
    assert set(study.conditions[1:]) == required


def test_frozen_model_and_tau_match_phase3b(study):
    meta = json.loads((ROOT / "results" / "tables" / "p3b_metadata.json").read_text())
    p3b = load_component("noise_study", "p3b_v1")
    ref = next(m for m in p3b.models if m.model_id == "p3a_r")
    assert study.model == ref
    assert study.frozen_tau == meta["models"]["p3a_r"]["tau_frozen_clean"]


def test_actions_match_mitigation_configs(study):
    resolved = load_experiment("phase4_mitigation")
    assert study.actions == {"A0": "none", "A1": "readout", "A2": "zne", "A3": "combined"}
    assert [m.action_id for m in resolved.mitigation] == list(study.actions.values())
    zne = {m.action_id: m for m in resolved.mitigation}["zne"].zne
    assert tuple(zne.noise_factors) == study.zne.noise_factors == (1, 3, 5)
    assert zne.extrapolator == "linear" and zne.clip_to_physical_range is True
    assert study.zne.primary_extrapolator == "linear_least_squares"
    assert study.zne.diagnostic_extrapolators == ("richardson",)


def test_registered_design_choices(study):
    assert [(b.shots_per_circuit, b.role) for b in study.shot_budgets] == [
        (1024, "primary"),
        (4096, "secondary"),
    ]
    assert study.replicates == 20 and study.resource_matched_multipliers == (3, 9)
    assert study.applicability["ro-sym-high"]["A1"] == "applicable"
    assert study.applicability["clean"] == {
        "A1": "negative_control",
        "A2": "negative_control",
        "A3": "negative_control",
    }
    assert study.applicability["comb-high"]["A3"] == "applicable"
    assert study.g2.pass_min_auprc_cells == 2


def test_schema_rejects_unregistered_designs(study):
    data = study.model_dump()
    with pytest.raises(ValidationError):
        ZNEStudyConfig(noise_factors=(1, 2, 3))
    bad = dict(data, applicability={k: v for k, v in data["applicability"].items() if k != "clean"})
    with pytest.raises(ValidationError):
        MitigationStudyConfig.model_validate(bad)
    with pytest.raises(ValidationError):
        MitigationStudyConfig.model_validate(
            dict(data, model=dict(data["model"], role="exploratory_contrast"))
        )
    two_primary = [dict(b, role="primary") for b in data["shot_budgets"]]
    with pytest.raises(ValidationError):
        MitigationStudyConfig.model_validate(dict(data, shot_budgets=two_primary))
