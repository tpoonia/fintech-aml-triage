"""Leakage guards R2/R3 (PROJECT_SPEC §7; A01, A12)."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from qtrace.features import FeatureSpec, LeakageError, assert_deployable, load_registry

# Snapshot of the deployable Q-TRACE-S inputs. Changing it requires a DECISIONS.md entry.
# A15 (Phase 5B): true simulator noise parameters left this set; probe estimates and static
# circuit/model descriptors joined it.
EXPECTED_QTRACE_S = {
    "n_qubits",
    "circuit_depth",
    "noisy_depth",
    "n_1q_gates",
    "n_2q_gates",
    "trainable_parameters",
    "ansatz",
    "ansatz_reps",
    "readout_observable",
    "encoding_family",
    "feature_set",
    "shots_per_circuit",
    "probe_prediction_entropy",
    "probe_shot_variance",
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
    "clean_val_auprc_at_freeze",
    "clean_val_auroc_at_freeze",
    "clean_val_brier_at_freeze",
    "clean_val_ece_at_freeze",
    "frozen_tau",
}

# A12: these must never be Q-TRACE inputs.
MUST_BE_OFFLINE = {
    "model_id",
    "model_seed",
    "noise_seed",
    "shot_seed",
    "noise_profile_id",
    "noise_family",
    "noise_severity",
    "transaction_label",
    "current_batch_accuracy",
    "current_batch_auprc",
    "mitigated_scores",
    "zne_scaled_outputs",
    "realized_delta",
    "oracle_action",
    # A15: true simulator noise parameters and Phase 5B identifiers/outcomes
    "p1",
    "p2",
    "readout_p01",
    "readout_p10",
    "t1_us",
    "t2_us",
    "struct_id",
    "seed_index",
    # Phase 5C continuous-design truth (registry v0.4)
    "noise_point_id",
    "gate_plot_id",
    "noise_region",
    "severity_readout",
    "severity_depolarizing",
    "severity_thermal",
    "readout_asymmetry_true",
    "readout_mean_true",
    "preferred_action",
    "current_batch_brier",
    "oracle_confusion_matrix",
}


@pytest.fixture(scope="module")
def registry():
    return load_registry()


def test_deployable_snapshot(registry):
    assert set(registry.deployable("qtrace_s")) == EXPECTED_QTRACE_S
    assert set(registry.deployable("qtrace_a")) == EXPECTED_QTRACE_S | {
        "recent_labelled_batch_performance"
    }


def test_a12_forbidden_inputs_are_offline_only(registry):
    for name in MUST_BE_OFFLINE:
        spec = registry.get(name)
        assert spec is not None, f"{name} missing from registry"
        assert spec.status == "offline_only"


def test_no_identifier_like_name_is_deployable(registry):
    for name in registry.deployable("qtrace_a"):
        tokens = set(name.split("_"))
        assert not tokens & {"id", "seed", "label"}, name


def test_probe_features_are_label_free_and_marked(registry):
    probes = [f for f in registry.features if f.group == "probe"]
    assert len(probes) == 13
    for spec in probes:
        assert spec.availability == "probe" and "A01" in spec.decisions


def test_assert_deployable_accepts_valid_inputs(registry):
    assert_deployable(
        ["probe_readout_error_mean", "probe_gate_contraction", "clean_val_auprc_at_freeze"],
        registry,
    )


@pytest.mark.parametrize(
    "name",
    [
        "model_id",
        "noise_family",
        "current_batch_accuracy",
        "zne_scaled_outputs",
        "not_declared_anywhere",
        "p1",
        "readout_p01",
        "t1_us",
        "struct_id",
        "preferred_action",
    ],
)
def test_assert_deployable_rejects_leaky_inputs(registry, name):
    with pytest.raises(LeakageError):
        assert_deployable(["probe_readout_error_mean", name], registry)


def test_labelled_history_only_for_adaptive_controller(registry):
    with pytest.raises(LeakageError, match="not available to qtrace_s"):
        assert_deployable(["recent_labelled_batch_performance"], registry, "qtrace_s")
    assert_deployable(["recent_labelled_batch_performance"], registry, "qtrace_a")


def test_schema_refuses_deployable_identifiers():
    with pytest.raises(ValidationError, match="cannot be deployable"):
        FeatureSpec(
            name="model_id",
            group="identifier",
            availability="pre_execution",
            status="deployable",
            controllers=("qtrace_s",),
            description="d",
            source="s",
        )
    with pytest.raises(ValidationError, match="Q-TRACE-A only"):
        FeatureSpec(
            name="h",
            group="history",
            availability="history",
            status="deployable",
            controllers=("qtrace_s",),
            description="d",
            source="s",
        )
