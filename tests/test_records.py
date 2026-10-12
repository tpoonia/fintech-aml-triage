from __future__ import annotations

import copy
from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from qtrace.records import ActionOutcome, PolicyDecision, ResourceUsage, RunManifest

HEX = "a" * 64
NOW = datetime(2026, 10, 6, tzinfo=UTC)


def resources(**overrides) -> dict:
    base = {
        "probe_circuit_executions": 8,
        "probe_shots": 8 * 256,
        "task_circuit_executions": 100,
        "task_shots": 100 * 1024,
        "mitigation_circuit_executions": 200,
        "mitigation_shots": 200 * 1024,
        "calibration_circuit_executions": 2,
        "calibration_shots": 2 * 1024,
        "total_circuit_executions": 310,
        "total_shots": 8 * 256 + 302 * 1024,
        "wall_clock_seconds": 1.5,
    }
    return {**base, **overrides}


def outcome(**section_overrides) -> dict:
    row = {
        "observation_id": "obs-1",
        "context_id": "ctx-1",
        "provenance": {
            "experiment_id": "p6-counterfactual",
            "run_id": "20261006T000000Z-deadbeef",
            "protocol_version": "0.2",
            "git_commit": "0" * 40,
            "git_dirty": False,
            "config_hash": HEX,
            "timestamp_utc": NOW,
            "python_version": "3.12.11",
            "qiskit_version": "2.5.2",
            "qiskit_aer_version": "0.17.2",
            "numpy_version": "2.5.3",
            "platform": "macOS-arm64",
        },
        "data": {
            "dataset_sha256": HEX,
            "split_hash": "s",
            "panel_id": "p",
            "panel_hash": "h",
            "panel_partition": "ctrl_train",
            "panel_n": 1000,
            "panel_n_fraud": 49,
            "weighting_scheme": "inverse_probability",
        },
        "model": {
            "model_id": "ra-r1-s0",
            "architecture_id": "ra-r1",
            "meta_split": "meta_train",
            "model_seed": 1,
            "params_sha256": HEX,
            "observable": "parity",
            "score_link": "affine",
        },
        "circuit": {
            "n_qubits": 4,
            "depth": 30,
            "n_1q_noisy": 40,
            "n_2q": 9,
            "basis_gates": ["rz", "sx", "x", "cx"],
            "optimization_level": 1,
            "transpile_seed": 7,
        },
        "noise": {
            "noise_profile_id": "comb-medium",
            "noise_source": "anchor",
            "p1": 0.001,
            "p2": 0.01,
            "ro_p01": 0.02,
            "ro_p10": 0.02,
            "t1_us": 100.0,
            "t2_us": 150.0,
            "gate_time_1q_ns": 35.0,
            "gate_time_2q_ns": 300.0,
        },
        "execution": {
            "execution_mode": "finite_shot",
            "shots_per_circuit": 1024,
            "replicate_id": 0,
            "shot_seed": 123,
            "probe_enabled": True,
            "simulator_method": "density_matrix",
        },
        "action": {"action": "combined", "action_config_hash": "c", "zne_factors": [1, 3, 5]},
        "resources": resources(),
        "metrics": {"auprc": 0.61, "auroc": 0.93, "rank_spearman_vs_clean": 0.98, "brier": 0.01},
    }
    for section, update in section_overrides.items():
        row[section] = {**row[section], **update} if isinstance(update, dict) else update
    return row


def test_synthetic_observation_validates_and_flattens():
    record = ActionOutcome.model_validate(outcome())
    flat = record.to_flat_dict()
    assert flat["resources.total_shots"] == record.resources.total_shots
    assert all(not isinstance(v, dict) for v in flat.values())
    assert len(flat) == len(set(flat))


def test_raw_costs_are_never_collapsed():
    # User cost-model requirement: no single pre-aggregated "cost" field exists.
    fields = set(ResourceUsage.model_fields)
    assert not {"cost", "total_cost", "monetary_cost"} & fields
    assert {"probe_shots", "task_shots", "mitigation_shots", "calibration_shots"} <= fields
    assert "wall_clock_seconds" in fields and "qpu_execution_seconds" in fields


def test_resource_totals_must_add_up():
    with pytest.raises(ValidationError, match="total_shots"):
        ResourceUsage.model_validate(resources(total_shots=1))
    with pytest.raises(ValidationError, match="total_circuit_executions"):
        ResourceUsage.model_validate(resources(total_circuit_executions=1))


def test_exact_mode_has_no_shot_fields():
    bad = outcome(execution={"execution_mode": "exact"})
    with pytest.raises(ValidationError, match="exact-mode"):
        ActionOutcome.model_validate(bad)


@pytest.mark.parametrize(
    "meta_split, partition",
    [
        ("meta_test", "ctrl_train"),
        ("meta_test", "ctrl_val"),
        ("meta_train", "ctrl_test"),
        ("meta_train", "ctrl_val"),
        ("meta_val", "ctrl_train"),
        ("meta_val", "ctrl_test"),
    ],
)
def test_controller_splits_use_their_own_partition(meta_split, partition):  # A04 / O21
    bad = outcome(model={"meta_split": meta_split}, data={"panel_partition": partition})
    with pytest.raises(ValidationError, match="must use"):
        ActionOutcome.model_validate(bad)


def test_matching_controller_partitions_accepted():
    for meta_split, partition in [
        ("meta_train", "ctrl_train"),
        ("meta_val", "ctrl_val"),
        ("meta_test", "ctrl_test"),
    ]:
        ok = outcome(model={"meta_split": meta_split}, data={"panel_partition": partition})
        ActionOutcome.model_validate(ok)


def test_never_evaluated_on_training_partition():
    for partition in ("vqc_train", "train", "test"):
        with pytest.raises(ValidationError):
            ActionOutcome.model_validate(outcome(data={"panel_partition": partition}))


def test_none_action_cannot_consume_mitigation_resources():
    bad = outcome(action={"action": "none", "action_config_hash": "n"})
    with pytest.raises(ValidationError, match="'none'"):
        ActionOutcome.model_validate(bad)


def test_probe_resources_require_probe():
    with pytest.raises(ValidationError, match="probe disabled"):
        ActionOutcome.model_validate(outcome(execution={"probe_enabled": False}))


def test_metric_ranges_enforced():
    with pytest.raises(ValidationError):
        ActionOutcome.model_validate(outcome(metrics={"auprc": 1.2}))
    with pytest.raises(ValidationError):
        ActionOutcome.model_validate(outcome(metrics={"rank_spearman_vs_clean": -1.5}))


def decision(**overrides) -> dict:
    base = {
        "policy_id": "oracle",
        "policy_config_hash": "x",
        "is_oracle": True,
        "deployable": False,
        "evaluated_on": "meta_test",
        "context_id": "ctx-1",
        "chosen_action": "zne",
        "selection_replicate_id": 0,
        "evaluation_replicate_id": 1,
    }
    return {**base, **overrides}


def test_oracle_requires_independent_replicates():  # A08
    PolicyDecision.model_validate(decision())
    with pytest.raises(ValidationError, match="independent"):
        PolicyDecision.model_validate(decision(evaluation_replicate_id=0))
    with pytest.raises(ValidationError, match="never deployable"):
        PolicyDecision.model_validate(decision(deployable=True))


def test_non_oracle_cannot_select_on_outcomes():
    with pytest.raises(ValidationError, match="realized outcomes"):
        PolicyDecision.model_validate(
            decision(policy_id="threshold", is_oracle=False, deployable=True)
        )


def test_policies_cannot_be_tuned_on_meta_test():  # A11
    with pytest.raises(ValidationError):
        PolicyDecision.model_validate(
            decision(
                policy_id="threshold",
                is_oracle=False,
                deployable=True,
                selection_replicate_id=None,
                tuned_on=["meta_test"],
            )
        )


def manifest(**overrides) -> dict:
    base = {
        "run_id": "r",
        "experiment_id": "e",
        "protocol_version": "0.2",
        "reporting": "dev",
        "status": "completed",
        "command": ["x"],
        "resolved_config": {},
        "config_hash": HEX,
        "component_hashes": {},
        "git": {"commit": "0" * 40, "branch": "main", "dirty": True},
        "environment": {"python_version": "3.12", "platform": "p", "packages": {}},
        "hardware": {"machine": "arm64", "cpu_model": "m", "cpu_count": 1, "memory_bytes": 1},
        "seeds": {},
        "started_utc": NOW,
        "finished_utc": NOW,
    }
    return {**base, **overrides}


def test_reported_runs_require_clean_tree():
    RunManifest.model_validate(manifest())  # dev run on a dirty tree is allowed
    with pytest.raises(ValidationError, match="clean git tree"):
        RunManifest.model_validate(manifest(reporting="reported"))
    clean = copy.deepcopy(manifest(reporting="reported"))
    clean["git"]["dirty"] = False
    RunManifest.model_validate(clean)
