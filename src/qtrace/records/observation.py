"""Schema of one experimental observation: (context, action, replicate).

Resource usage is stored as raw counts per category (probe, task, mitigation,
calibration) and is never collapsed into a single cost number, so alternative
cost functions can be evaluated later (O08). Wall-clock time is stored
separately because it depends on the host.
"""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Sha256 = str
Unit = float  # value in [0, 1]

ACTIONS = ("none", "readout", "zne", "combined", "pec")
ExecutionMode = Literal["exact", "finite_shot", "hardware"]
MetaSplit = Literal["meta_train", "meta_val", "meta_test"]
# Controller (meta) split -> the only transaction partition its panels may come from.
META_SPLIT_PARTITION = {
    "meta_train": "ctrl_train",
    "meta_val": "ctrl_val",
    "meta_test": "ctrl_test",
}


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Provenance(_Record):
    experiment_id: str
    run_id: str
    protocol_version: str
    git_commit: str | None
    git_dirty: bool
    config_hash: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    stage_cache_key: str | None = None
    timestamp_utc: datetime
    python_version: str
    qiskit_version: str
    qiskit_aer_version: str
    numpy_version: str
    platform: str


class DataRef(_Record):
    dataset_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    split_hash: str
    panel_id: str
    panel_hash: str
    # Transaction partition the panel was drawn from (O21 option B). vqc_train is
    # deliberately not a legal value: QEM observations never use VQC training data.
    panel_partition: Literal["vqc_val", "ctrl_train", "ctrl_val", "ctrl_test"]
    panel_n: int = Field(ge=1)
    panel_n_fraud: int = Field(ge=0)
    weighting_scheme: Literal["none", "inverse_probability"]

    @model_validator(mode="after")
    def _counts(self) -> DataRef:
        if self.panel_n_fraud > self.panel_n:
            raise ValueError("panel_n_fraud exceeds panel_n")
        return self


class ModelRef(_Record):
    model_id: str
    architecture_id: str
    meta_split: MetaSplit | None  # None for pilot models not assigned to a meta split
    model_seed: int
    params_sha256: Sha256 = Field(pattern=r"^[0-9a-f]{64}$")
    observable: str
    score_link: str


class CircuitInfo(_Record):
    """Post-transpile counts of the scale-1 circuit (E09)."""

    n_qubits: int = Field(ge=1)
    depth: int = Field(ge=0)
    n_1q_noisy: int = Field(ge=0)
    n_2q: int = Field(ge=0)
    basis_gates: tuple[str, ...]
    optimization_level: int = Field(ge=0, le=3)
    transpile_seed: int


class NoiseInfo(_Record):
    noise_profile_id: str  # offline metadata only (A12)
    noise_source: Literal["anchor", "negative_control", "sampled", "backend_snapshot"]
    p1: float = Field(ge=0, le=1)
    p2: float = Field(ge=0, le=1)
    ro_p01: Unit = Field(ge=0, le=1)
    ro_p10: Unit = Field(ge=0, le=1)
    t1_us: float | None = Field(None, gt=0)
    t2_us: float | None = Field(None, gt=0)
    gate_time_1q_ns: float = Field(gt=0)
    gate_time_2q_ns: float = Field(gt=0)
    noise_seed: int | None = None
    backend_snapshot_id: str | None = None


class ExecutionInfo(_Record):
    execution_mode: ExecutionMode
    shots_per_circuit: int | None = Field(None, ge=1)
    replicate_id: int | None = Field(None, ge=0)
    shot_seed: int | None = None
    probe_enabled: bool
    simulator_method: str | None = None
    backend_name: str | None = None

    @model_validator(mode="after")
    def _mode(self) -> ExecutionInfo:
        sampled = (self.shots_per_circuit, self.replicate_id, self.shot_seed)
        if self.execution_mode == "exact" and any(v is not None for v in sampled):
            raise ValueError("exact-mode observations have no shots, replicate or shot seed")
        if self.execution_mode == "finite_shot" and any(v is None for v in sampled):
            raise ValueError("finite-shot observations need shots, replicate_id and shot_seed")
        return self


class ActionInfo(_Record):
    action: Literal["none", "readout", "zne", "combined", "pec"]
    action_config_hash: str
    zne_factors: tuple[int, ...] | None = None
    zne_extrapolator: str | None = None
    zne_shot_allocation: str | None = None
    readout_method: str | None = None
    clip_policy: str | None = None


class ResourceUsage(_Record):
    """Raw quantum-resource counts (user cost-model requirement; O08).

    ``probe_*`` is the cost of the decision-time probe (A01). It is charged to
    policies that use a probe and to no other policy.
    """

    probe_circuit_executions: int = Field(ge=0)
    probe_shots: int = Field(ge=0)
    task_circuit_executions: int = Field(ge=0)
    task_shots: int = Field(ge=0)
    mitigation_circuit_executions: int = Field(ge=0)
    mitigation_shots: int = Field(ge=0)
    calibration_circuit_executions: int = Field(ge=0)
    calibration_shots: int = Field(ge=0)
    total_circuit_executions: int = Field(ge=0)
    total_shots: int = Field(ge=0)
    depth_weighted_shots: int | None = Field(None, ge=0)  # sum over circuits of shots x depth
    simulator_execution_seconds: float | None = Field(None, ge=0)
    qpu_execution_seconds: float | None = Field(None, ge=0)
    wall_clock_seconds: float = Field(ge=0)  # host-dependent; never a decision cost

    @model_validator(mode="after")
    def _totals(self) -> ResourceUsage:
        circuits = (
            self.probe_circuit_executions
            + self.task_circuit_executions
            + self.mitigation_circuit_executions
            + self.calibration_circuit_executions
        )
        shots = self.probe_shots + self.task_shots + self.mitigation_shots + self.calibration_shots
        if circuits != self.total_circuit_executions:
            raise ValueError("total_circuit_executions must equal the sum of its components")
        if shots != self.total_shots:
            raise ValueError("total_shots must equal the sum of its components")
        return self


class OutcomeMetrics(_Record):
    """Fraud and distortion metrics (A03, A13). All optional: not every stage computes all."""

    auprc: Unit | None = Field(None, ge=0, le=1)
    auroc: Unit | None = Field(None, ge=0, le=1)
    recall: Unit | None = Field(None, ge=0, le=1)
    precision: Unit | None = Field(None, ge=0, le=1)
    f1: Unit | None = Field(None, ge=0, le=1)
    f2: Unit | None = Field(None, ge=0, le=1)
    precision_at_k: Unit | None = Field(None, ge=0, le=1)
    recall_at_precision: Unit | None = Field(None, ge=0, le=1)
    brier: Unit | None = Field(None, ge=0, le=1)
    ece: Unit | None = Field(None, ge=0, le=1)
    tau: float | None = None
    tau_source: str | None = None
    # A13 distortion diagnostics, relative to the clean (noiseless) scores of the same model
    rank_spearman_vs_clean: float | None = Field(None, ge=-1, le=1)
    rank_kendall_vs_clean: float | None = Field(None, ge=-1, le=1)
    frac_threshold_crossings_vs_clean: Unit | None = Field(None, ge=0, le=1)
    mean_abs_score_shift_vs_clean: float | None = Field(None, ge=0)
    frac_scores_clipped: Unit | None = Field(None, ge=0, le=1)
    n_score_ties: int | None = Field(None, ge=0)


class ActionOutcome(_Record):
    """One experimental observation. Written only by ``qtrace.counterfactual``."""

    observation_id: str
    context_id: str
    provenance: Provenance
    data: DataRef
    model: ModelRef
    circuit: CircuitInfo
    noise: NoiseInfo
    execution: ExecutionInfo
    action: ActionInfo
    resources: ResourceUsage
    metrics: OutcomeMetrics
    predictions_path: str | None = None
    predictions_sha256: str | None = Field(None, pattern=r"^[0-9a-f]{64}$")

    @model_validator(mode="after")
    def _cross_checks(self) -> ActionOutcome:
        # A04 / O21: each controller split uses its own disjoint transaction partition.
        required = META_SPLIT_PARTITION.get(self.model.meta_split or "")
        if required is not None and self.data.panel_partition != required:
            raise ValueError(
                f"{self.model.meta_split} observations must use {required!r} panels, "
                f"not {self.data.panel_partition!r}"
            )
        if self.action.action == "none" and (
            self.resources.mitigation_circuit_executions or self.resources.calibration_shots
        ):
            raise ValueError("action 'none' cannot consume mitigation or calibration resources")
        if not self.execution.probe_enabled and (
            self.resources.probe_circuit_executions or self.resources.probe_shots
        ):
            raise ValueError("probe resources recorded but probe disabled")
        return self

    def to_flat_dict(self) -> dict[str, Any]:
        """Flatten to ``group.field`` columns for tabular storage."""
        flat: dict[str, Any] = {}
        for key, value in self.model_dump(mode="json").items():
            if isinstance(value, dict):
                for sub_key, sub_value in value.items():
                    flat[f"{key}.{sub_key}"] = sub_value
            else:
                flat[key] = value
        return flat
