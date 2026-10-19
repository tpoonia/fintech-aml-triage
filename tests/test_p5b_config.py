"""Phase 5B pre-registration: the counterfactual study config is complete and consistent."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qtrace.config import load_component, load_experiment
from qtrace.config.schemas import CounterfactualStudyConfig
from qtrace.data.access import PartitionAccessError, check_access
from qtrace.features import load_registry


@pytest.fixture(scope="module")
def study():
    return load_component("counterfactual_study", "p5b_v1")


def test_registered_design(study):
    p4 = load_component("mitigation_study", "p4_v1")
    assert study.conditions == p4.conditions  # exactly the Phase 4 conditions
    assert [b.shots_per_circuit for b in study.shot_budgets] == [1024, 4096]
    assert study.replicates == 20 and study.extra_shots_multiplier == 3
    assert study.actions["A4"] == "extra_shots" and study.cost_order[0] == "A0"
    assert study.partition_of == {"train": "ctrl_train", "val": "ctrl_val", "test": "ctrl_test"}
    assert study.lockbox_dir.startswith("results/lockbox/")
    assert load_experiment("phase5b_counterfactual").spec.protocol_version == "0.11"


def test_features_are_deployable_and_prohibited_list_is_offline(study):
    reg = load_registry()
    deployable = set(reg.deployable("qtrace_s"))
    assert set(study.static_features) | set(study.probe_features) <= deployable
    for name in study.prohibited_features:
        spec = reg.get(name)
        assert spec is not None and spec.status == "offline_only", name


def test_phase5b_access_is_controller_only():
    assert check_access("phase5b", ["ctrl_train"]) == ("ctrl_train",)
    for bad in ("vqc_train", "vqc_val"):
        with pytest.raises(PartitionAccessError):
            check_access("phase5b", [bad])


def test_schema_rejects_leaky_or_unsealed_designs(study):
    data = study.model_dump()
    with pytest.raises(ValidationError):
        CounterfactualStudyConfig.model_validate(
            dict(data, probe_features=[*data["probe_features"], "p1"])
        )
    with pytest.raises(ValidationError):
        CounterfactualStudyConfig.model_validate(dict(data, lockbox_dir="results/processed/x"))
    split = dict(data["structure_split"])
    split["val"] = [*split["val"], split["train"][0]]
    with pytest.raises(ValidationError):
        CounterfactualStudyConfig.model_validate(dict(data, structure_split=split))
    with pytest.raises(ValidationError):
        CounterfactualStudyConfig.model_validate(
            dict(
                data, partition_of={"train": "ctrl_train", "val": "ctrl_train", "test": "ctrl_test"}
            )
        )
