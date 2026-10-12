from __future__ import annotations

from pathlib import Path

import pytest
from pydantic import ValidationError

from qtrace.config import ConfigError, load_component, load_experiment, load_yaml
from qtrace.config.schemas import (
    DatasetConfig,
    ExecutionConfig,
    MitigationConfig,
    ModelPoolConfig,
    NoiseProfile,
    ZNEConfig,
)
from qtrace.utils.hashing import canonical_json, stable_hash

CONFIG_FILES = sorted(Path(__file__).resolve().parents[1].joinpath("configs").rglob("*.yaml"))


def test_all_shipped_component_configs_validate():
    for family, ids in {
        "dataset": ["ulb_v1"],
        "model_pool": ["pool_rr_v1"],
        "noise": ["anchors_rr_v1", "smoke"],
        "mitigation": ["none", "readout", "zne", "combined"],
    }.items():
        for component_id in ids:
            load_component(family, component_id)


def test_smoke_experiment_resolves():
    resolved = load_experiment("smoke_env")
    assert resolved.noise is not None and resolved.noise.profiles[0].family == "combined"
    assert [m.action for m in resolved.mitigation] == ["none"]


def test_rr_pool_is_40_models_and_scales_beyond():
    pool = load_component("model_pool", "pool_rr_v1")
    assert isinstance(pool, ModelPoolConfig) and pool.total_models == 40
    # A06: pool size is configuration, not code.
    bigger = {
        **pool.model_dump(),
        "seeds_per_architecture": 50,
        "meta_split_per_architecture": {"meta_train": 30, "meta_val": 10, "meta_test": 10},
    }
    assert ModelPoolConfig.model_validate(bigger).total_models == 200


def test_rr_anchor_grid_has_12_profiles_with_symmetric_negative_controls():
    anchors = load_component("noise", "anchors_rr_v1")
    assert len(anchors.profiles) == 12
    controls = [p for p in anchors.profiles if p.role == "negative_control"]
    assert len(controls) == 3 and all(
        p.family == "readout" and p.readout_symmetric for p in controls
    )


def test_unknown_keys_rejected():
    data = load_yaml(Path(__file__).resolve().parents[1] / "configs/datasets/ulb_v1.yaml")
    data["unexpected"] = 1
    with pytest.raises(ValidationError):
        DatasetConfig.model_validate(data)


def test_duplicate_yaml_keys_rejected(tmp_path):
    path = tmp_path / "dup.yaml"
    path.write_text("a: 1\na: 2\n")
    with pytest.raises(ConfigError, match="duplicate key"):
        load_yaml(path)


def test_component_id_must_match_file_name(tmp_path):
    (tmp_path / "mitigation").mkdir()
    (tmp_path / "mitigation" / "zne.yaml").write_text("action_id: other\naction: none\n")
    with pytest.raises(ConfigError, match="file name"):
        load_component("mitigation", "zne", root=tmp_path)


def test_dataset_decisions_are_enforced():
    data = load_yaml(Path(__file__).resolve().parents[1] / "configs/datasets/ulb_v1.yaml")
    DatasetConfig.model_validate(data)
    bad_variants = [
        {"deduplication": {**data["deduplication"], "before_split": False}},  # A04
        {"deduplication": {**data["deduplication"], "conflicting_labels": "keep_first"}},
        {"preprocessing": {**data["preprocessing"], "fit_on": "ctrl_train"}},  # A04
        {"partitions": {**data["partitions"], "fractions": {"train": 0.6, "test": 0.4}}},
        {
            "partitions": {
                **data["partitions"],
                "fractions": {**data["partitions"]["fractions"], "ctrl_test": 0.3},
            }
        },  # no longer sums to 1
        {"expected_sha256": "not-a-hash"},
        {"split": {"train": 0.6, "validation": 0.2, "test": 0.2}},  # superseded RR key
    ]
    for update in bad_variants:
        with pytest.raises(ValidationError):
            DatasetConfig.model_validate({**data, **update})


def test_option_b_partitions_and_recorded_checksum():  # O21, Phase 1
    dataset = load_component("dataset", "ulb_v1")
    assert dataset.partitions.fractions == {
        "vqc_train": 0.45,
        "vqc_val": 0.10,
        "ctrl_train": 0.15,
        "ctrl_val": 0.10,
        "ctrl_test": 0.20,
    }
    assert dataset.expected_sha256 is not None and dataset.provenance is not None
    assert dataset.provenance.license == "DbCL-1.0"


@pytest.mark.parametrize(
    "kwargs",
    [
        {"family": "readout", "readout_p01": 0.6, "readout_p10": 0.5},  # non-invertible
        {"family": "thermal", "thermal": {"t1_us": 50, "t2_us": 120}},  # T2 > 2 T1
        {"family": "depolarizing", "p1": 0.001, "readout_p01": 0.01},  # family mismatch
        {"family": "combined", "p1": 0.001},  # combined needs >= 2 sources
        {"family": "none", "p2": 0.01},
        {"family": "depolarizing", "p1": 1.5},
    ],
)
def test_invalid_noise_profiles(kwargs):
    with pytest.raises(ValidationError):
        NoiseProfile(profile_id="x", **kwargs)


def test_asymmetric_readout_supported():
    profile = NoiseProfile(
        profile_id="ro-asym", family="readout", readout_p01=0.01, readout_p10=0.04
    )
    assert not profile.readout_symmetric


@pytest.mark.parametrize("factors", [(3, 5), (1,), (1, 2, 3), (1, 5, 3)])
def test_invalid_zne_factors(factors):
    with pytest.raises(ValidationError):
        ZNEConfig(noise_factors=factors)


def test_mitigation_blocks_must_match_action():
    with pytest.raises(ValidationError):
        MitigationConfig(action_id="zne", action="zne")  # missing zne block
    with pytest.raises(ValidationError):
        MitigationConfig(action_id="pec", action="pec")  # PEC must be flagged exploratory
    MitigationConfig(action_id="pec", action="pec", exploratory=True)


def test_execution_mode_constraints_and_probe():
    with pytest.raises(ValidationError):
        ExecutionConfig(mode="finite_shot")
    with pytest.raises(ValidationError):
        ExecutionConfig(mode="exact", shots_per_circuit=1024)
    execution = ExecutionConfig(mode="exact")
    assert execution.probe.enabled and execution.probe.n_transactions is None  # O19 open
    with pytest.raises(ValidationError):
        ExecutionConfig(mode="exact", probe={"uses_labels": True})  # A01


def test_config_hash_is_stable_and_key_order_invariant():
    resolved = load_experiment("smoke_env")
    assert resolved.config_hash() == load_experiment("smoke_env").config_hash()
    assert canonical_json({"b": 1, "a": [1, 2]}) == canonical_json({"a": [1, 2], "b": 1})
    assert stable_hash({"b": 1, "a": 2}) == stable_hash({"a": 2, "b": 1})
    hashes = resolved.component_hashes()
    assert set(hashes) == {"experiment_spec", "noise", "mitigation/none"}


def test_config_hash_changes_with_content():
    resolved = load_experiment("smoke_env")
    changed = resolved.model_copy(
        update={"spec": resolved.spec.model_copy(update={"description": "changed"})}
    )
    assert changed.config_hash() != resolved.config_hash()


def test_nan_not_hashable():
    with pytest.raises(ValueError):
        canonical_json({"x": float("nan")})


def test_every_yaml_file_is_parseable():
    assert CONFIG_FILES, "no config files found"
    for path in CONFIG_FILES:
        load_yaml(path)
