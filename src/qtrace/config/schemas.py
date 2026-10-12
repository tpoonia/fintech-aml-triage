"""Pydantic v2 schemas for every config family (E03).

All models are strict (unknown keys rejected) and frozen. Approved decisions
are encoded as constraints where possible (e.g. deduplication can only happen
before the split). Open research decisions are optional fields that default
to ``None``; the comment names the decision ID in docs/DECISIONS.md.
"""

from __future__ import annotations

import re
from typing import Annotated, Literal, get_args

from pydantic import BaseModel, ConfigDict, Field, model_validator

from qtrace.utils.hashing import stable_hash

Identifier = Annotated[str, Field(pattern=r"^[a-z0-9][a-z0-9_\-]*$", max_length=64)]
Probability = Annotated[float, Field(ge=0.0, le=1.0)]
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


# --------------------------------------------------------------------------- seeds


class SeedConfig(StrictModel):
    """Master seed per randomness stream [RR §Reproducibility structure] + E04."""

    split: int = Field(ge=0)
    model: int = Field(ge=0)
    undersample: int = Field(ge=0)
    noise: int = Field(ge=0)
    shots: int = Field(ge=0)
    policy: int = Field(ge=0)
    bootstrap: int = Field(ge=0)


# ------------------------------------------------------------------------- dataset

PartitionName = Literal["vqc_train", "vqc_val", "ctrl_train", "ctrl_val", "ctrl_test"]
PARTITION_NAMES: tuple[str, ...] = get_args(PartitionName)
# Partitions an evaluation panel may be drawn from: never the VQC training data.
PANEL_PARTITIONS: tuple[str, ...] = ("vqc_val", "ctrl_train", "ctrl_val", "ctrl_test")


class PartitionConfig(StrictModel):
    """Five disjoint transaction partitions (O21 = option B; A04), group-aware (O23).

    Rows sharing ``V1``-``V28`` + ``Amount`` (all features except ``Time``) form a
    group that is assigned to exactly one partition. A group's stratum is fraud
    if it contains any fraud row.
    """

    method: Literal["stratified_group_random"] = "stratified_group_random"
    stratify_on: Literal["target"] = "target"
    group_key: Literal["features_except_time"] = "features_except_time"  # O23
    group_stratum: Literal["any_fraud"] = "any_fraud"
    fractions: dict[PartitionName, float]

    @model_validator(mode="after")
    def _check(self) -> PartitionConfig:
        if set(self.fractions) != set(PARTITION_NAMES):
            raise ValueError(f"fractions must define exactly {PARTITION_NAMES}")
        if any(not 0 < f < 1 for f in self.fractions.values()):
            raise ValueError("each partition fraction must be in (0, 1)")
        if abs(sum(self.fractions.values()) - 1.0) > 1e-9:
            raise ValueError("partition fractions must sum to 1")
        return self


class DeduplicationConfig(StrictModel):
    """PI policy (Phase 1): audit first, then deduplicate before any split."""

    before_split: Literal[True] = True  # A04
    duplicate_key: Literal["all_feature_columns"] = "all_feature_columns"
    exact_duplicates: Literal["keep_lowest_row_id"] = "keep_lowest_row_id"
    conflicting_labels: Literal["exclude_group"] = "exclude_group"


class PreprocessingConfig(StrictModel):
    fit_on: Literal["vqc_train"] = "vqc_train"  # F15 / A04: never fitted on anything else
    fit_before_undersampling: Literal[True] = True
    amount_transform: Literal["log1p"] = "log1p"
    time_scaling: Literal["robust"] = "robust"
    amount_scaling: Literal["robust"] = "robust"  # applied after log1p
    quantile_range: tuple[float, float] = (25.0, 75.0)

    @model_validator(mode="after")
    def _range(self) -> PreprocessingConfig:
        low, high = self.quantile_range
        if not 0 <= low < high <= 100:
            raise ValueError("quantile_range must satisfy 0 <= low < high <= 100")
        return self


class ReductionConfig(StrictModel):
    method: Literal["pca", "supervised_selection"] | None = None  # O02 (Phase 3A)
    n_components: int = Field(4, ge=1, le=8)


class DatasetProvenance(StrictModel):
    source: Literal["kaggle"]
    kaggle_ref: str
    kaggle_dataset_id: int
    title: str
    license: str
    archive_name: str
    archive_sha256: str
    archive_bytes: int = Field(ge=1)
    file_name: str
    file_bytes: int = Field(ge=1)
    acquired_utc: str
    acquisition_tool: str
    acquisition_commands: tuple[str, ...]

    @model_validator(mode="after")
    def _hash(self) -> DatasetProvenance:
        if not _SHA256.match(self.archive_sha256):
            raise ValueError("archive_sha256 must be 64 lowercase hex characters")
        return self


class DatasetConfig(StrictModel):
    dataset_id: Identifier
    name: str
    source_url: str
    raw_path: str  # relative to the repository root; gitignored
    expected_sha256: str | None = None
    expected_rows: int = Field(ge=1)
    expected_frauds: int = Field(ge=1)
    target_column: str
    feature_columns: tuple[str, ...] = Field(min_length=1)
    provenance: DatasetProvenance | None = None
    deduplication: DeduplicationConfig
    partitions: PartitionConfig
    preprocessing: PreprocessingConfig
    reduction: ReductionConfig

    @model_validator(mode="after")
    def _check(self) -> DatasetConfig:
        if self.expected_sha256 is not None and not _SHA256.match(self.expected_sha256):
            raise ValueError("expected_sha256 must be 64 lowercase hex characters")
        if self.target_column in self.feature_columns:
            raise ValueError("target column must not be a feature column")
        if len(set(self.feature_columns)) != len(self.feature_columns):
            raise ValueError("duplicate feature columns")
        if self.expected_frauds > self.expected_rows:
            raise ValueError("expected_frauds exceeds expected_rows")
        for column in ("Time", "Amount"):
            if column not in self.feature_columns:
                raise ValueError(f"preprocessing requires a {column!r} feature column")
        return self


# ----------------------------------------------------------------------------- qml


class FeatureMapConfig(StrictModel):
    type: Literal["zz_feature_map"] = "zz_feature_map"
    reps: int = Field(1, ge=1)
    entanglement: Literal["linear", "full", "circular"] | None = None  # open (protocol §3.1)


class ArchitectureConfig(StrictModel):
    arch_id: Identifier
    ansatz: Literal["real_amplitudes", "efficient_su2"]
    reps: int = Field(ge=1)
    entanglement: Literal["linear", "reverse_linear", "full", "circular"] | None = None


class TrainingConfig(StrictModel):
    optimizer: Literal["COBYLA"] = "COBYLA"
    maxiter: int = Field(ge=1)  # provisional; O04
    loss: Literal["cross_entropy"] | None = None  # open (protocol §3.3)
    noise_during_training: Literal["none"] = "none"  # F05: train clean, freeze


class MetaSplitCounts(StrictModel):
    meta_train: int = Field(ge=0)
    meta_val: int = Field(ge=0)
    meta_test: int = Field(ge=0)


class ModelPoolConfig(StrictModel):
    """A pool of frozen VQCs. Size is configuration, not code (A06)."""

    pool_id: Identifier
    n_qubits: int = Field(ge=1, le=8)
    feature_map: FeatureMapConfig
    architectures: tuple[ArchitectureConfig, ...] = Field(min_length=1)
    seeds_per_architecture: int = Field(ge=1)  # no upper bound: A06
    meta_split_per_architecture: MetaSplitCounts
    training: TrainingConfig
    observable: Literal["parity", "z0", "multi_z_head"] | None = None  # O01
    inclusion_min_clean_val_auprc: float | None = Field(None, ge=0, le=1)  # O04

    @model_validator(mode="after")
    def _check(self) -> ModelPoolConfig:
        ids = [a.arch_id for a in self.architectures]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate arch_id in pool")
        split = self.meta_split_per_architecture
        if split.meta_train + split.meta_val + split.meta_test != self.seeds_per_architecture:
            raise ValueError("meta split counts must sum to seeds_per_architecture")
        return self

    @property
    def total_models(self) -> int:
        return len(self.architectures) * self.seeds_per_architecture


# --------------------------------------------------------------------------- noise


class ThermalConfig(StrictModel):
    t1_us: float = Field(gt=0)
    t2_us: float = Field(gt=0)

    @model_validator(mode="after")
    def _physical(self) -> ThermalConfig:
        if self.t2_us > 2 * self.t1_us:
            raise ValueError("thermal relaxation requires T2 <= 2*T1")
        return self


class NoiseProfile(StrictModel):
    """One noise environment.

    ``p1``/``p2`` are Qiskit ``depolarizing_error`` parameters (channel
    (1-p)rho + p I/d), not average gate infidelities. ``readout_p01`` is
    P(read 1 | prepared 0); ``readout_p10`` is P(read 0 | prepared 1). They may
    differ (A07); the symmetric case is kept as a negative control.

    ``profile_id``, ``family`` and ``severity`` are offline metadata and are
    never Q-TRACE inputs (A12).
    """

    profile_id: Identifier
    family: Literal["none", "depolarizing", "readout", "thermal", "combined"]
    severity: Literal["low", "medium", "high"] | None = None
    role: Literal["anchor", "negative_control", "synthetic_stress", "smoke"] = "anchor"
    p1: float = Field(0.0, ge=0.0, le=1.0)
    p2: float = Field(0.0, ge=0.0, le=1.0)
    readout_p01: Probability = 0.0
    readout_p10: Probability = 0.0
    thermal: ThermalConfig | None = None
    gate_time_1q_ns: float = Field(35.0, gt=0)
    gate_time_2q_ns: float = Field(300.0, gt=0)

    @property
    def has_depolarizing(self) -> bool:
        return self.p1 > 0 or self.p2 > 0

    @property
    def has_readout(self) -> bool:
        return self.readout_p01 > 0 or self.readout_p10 > 0

    @property
    def readout_symmetric(self) -> bool:
        return self.readout_p01 == self.readout_p10

    @model_validator(mode="after")
    def _check(self) -> NoiseProfile:
        if self.readout_p01 + self.readout_p10 >= 1:
            raise ValueError("readout_p01 + readout_p10 must be < 1 (invertible confusion matrix)")
        active = {
            "depolarizing": self.has_depolarizing,
            "readout": self.has_readout,
            "thermal": self.thermal is not None,
        }
        n_active = sum(active.values())
        if self.family == "none" and n_active:
            raise ValueError("family 'none' must have no active noise")
        if self.family in active and (not active[self.family] or n_active != 1):
            raise ValueError(f"family {self.family!r} must activate exactly that noise source")
        if self.family == "combined" and n_active < 2:
            raise ValueError("family 'combined' needs at least two active noise sources")
        return self


class NoiseProfileSet(StrictModel):
    set_id: Identifier
    description: str = ""
    profiles: tuple[NoiseProfile, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> NoiseProfileSet:
        ids = [p.profile_id for p in self.profiles]
        if len(set(ids)) != len(ids):
            raise ValueError("duplicate profile_id in noise set")
        return self


# ---------------------------------------------------------------------- mitigation


class ZNEConfig(StrictModel):
    noise_factors: tuple[int, ...] = (1, 3, 5)
    extrapolator: Literal["linear", "richardson", "exponential"] = "linear"
    folding: Literal["global"] = "global"  # E10
    shot_allocation: Literal["equal"] = "equal"  # O09: only option implemented
    clip_to_physical_range: bool | None = None  # O09

    @model_validator(mode="after")
    def _factors(self) -> ZNEConfig:
        f = self.noise_factors
        if len(f) < 2 or f[0] != 1:
            raise ValueError("noise_factors must start at 1 and contain at least two factors")
        if any(b <= a for a, b in zip(f, f[1:], strict=False)):
            raise ValueError("noise_factors must be strictly increasing")
        if any(x % 2 == 0 for x in f):
            raise ValueError("global unitary folding supports odd noise factors only")
        return self


class ReadoutMitigationConfig(StrictModel):
    method: Literal["tensored", "full"] = "tensored"  # E11
    calibration_shots_per_circuit: int | None = Field(None, ge=1)  # O07/O08


class MitigationConfig(StrictModel):
    action_id: Identifier
    action: Literal["none", "readout", "zne", "combined", "pec"]
    readout: ReadoutMitigationConfig | None = None
    zne: ZNEConfig | None = None
    exploratory: bool = False

    @model_validator(mode="after")
    def _blocks_match_action(self) -> MitigationConfig:
        needs = {
            "none": (False, False),
            "readout": (True, False),
            "zne": (False, True),
            "combined": (True, True),
            "pec": (False, False),
        }[self.action]
        if (self.readout is not None, self.zne is not None) != needs:
            raise ValueError(f"action {self.action!r} has the wrong readout/zne config blocks")
        if self.action == "pec" and not self.exploratory:
            raise ValueError("PEC is exploratory only (F03): set exploratory: true")
        return self


# ----------------------------------------------------------------------- execution


class ProbeConfig(StrictModel):
    """Probe-before-decision (A01). Size and reuse are deliberately not frozen (O19)."""

    enabled: bool = True
    n_transactions: int | None = Field(None, ge=1)  # O19
    shots_per_circuit: int | None = Field(None, ge=1)  # O19
    reuse_outputs_in_task: bool | None = None  # O19
    uses_labels: Literal[False] = False  # A01: the probe never sees ground truth


class ExecutionConfig(StrictModel):
    mode: Literal["exact", "finite_shot", "hardware"]
    simulator_method: Literal["density_matrix", "statevector"] = "density_matrix"  # E07
    shots_per_circuit: int | None = Field(None, ge=1)
    replicates: int = Field(1, ge=1)
    basis_gates: tuple[str, ...] = ("rz", "sx", "x", "cx")  # E09
    optimization_level: int = Field(1, ge=0, le=3)
    probe: ProbeConfig = Field(default_factory=ProbeConfig)

    @model_validator(mode="after")
    def _shots(self) -> ExecutionConfig:
        if self.mode == "exact" and (self.shots_per_circuit is not None or self.replicates != 1):
            raise ValueError("exact mode has no shots and exactly one replicate")
        if self.mode != "exact" and self.shots_per_circuit is None:
            raise ValueError(f"{self.mode} mode requires shots_per_circuit")
        return self


# ------------------------------------------------------------- classical baselines


class RepresentationConfig(StrictModel):
    """A candidate input representation (evidence for O02; never the final VQC choice)."""

    rep_id: Identifier
    kind: Literal["full", "pca", "select_k_best"]
    n_components: int | None = Field(None, ge=1, le=8)
    standardize: bool = False  # pca only
    score_func: Literal["f_classif"] | None = None  # select_k_best only

    @model_validator(mode="after")
    def _check(self) -> RepresentationConfig:
        if self.kind == "full" and (self.n_components or self.standardize or self.score_func):
            raise ValueError("'full' takes no parameters")
        if self.kind in {"pca", "select_k_best"} and self.n_components is None:
            raise ValueError(f"{self.kind} needs n_components")
        if (self.kind == "select_k_best") != (self.score_func is not None):
            raise ValueError("score_func is required for, and only for, select_k_best")
        if self.standardize and self.kind != "pca":
            raise ValueError("standardize applies to pca only")
        return self


class ClassicalModelConfig(StrictModel):
    model_id: Identifier
    kind: Literal["logistic_regression", "random_forest", "hist_gradient_boosting"]
    params: dict[str, float | int | str | bool | None] = Field(default_factory=dict)


class RegimeConfig(StrictModel):
    """Training regime: the full vqc_train partition (A) or a VQC-scale subset (B; O17 open)."""

    regime_id: Identifier
    kind: Literal["full_partition", "subset"]
    class_weight: Literal["balanced"] | None = None
    legit_per_fraud: float | None = Field(None, gt=0)
    draws: int = Field(1, ge=1)

    @model_validator(mode="after")
    def _check(self) -> RegimeConfig:
        if (self.kind == "subset") != (self.legit_per_fraud is not None):
            raise ValueError("legit_per_fraud is required for, and only for, subset regimes")
        if self.kind == "full_partition" and self.draws != 1:
            raise ValueError("the full partition has exactly one draw")
        return self


class ThresholdConfig(StrictModel):
    criterion: Literal["max_f1"] = "max_f1"
    tie_break: Literal["highest_threshold"] = "highest_threshold"
    rule: Literal["score_ge_threshold"] = "score_ge_threshold"
    crossfit_folds: int = Field(2, ge=2)


class BootstrapConfig(StrictModel):
    scheme: Literal["stratified_fixed_class_counts"] = "stratified_fixed_class_counts"
    n_resamples: int = Field(ge=50)
    confidence: float = Field(0.95, gt=0, lt=1)
    interval: Literal["percentile"] = "percentile"


class CalibrationConfig(StrictModel):
    n_bins: int = Field(10, ge=2)
    strategy: Literal["uniform"] = "uniform"  # primary ECE convention
    sensitivity_strategy: Literal["quantile"] = "quantile"


class ClassicalBaselineConfig(StrictModel):
    """Phase 2 classical sanity baselines. Only VQC partitions are legal (E26)."""

    baseline_id: Identifier
    fit_partition: Literal["vqc_train"] = "vqc_train"
    eval_partition: Literal["vqc_val"] = "vqc_val"
    representations: tuple[RepresentationConfig, ...] = Field(min_length=1)
    models: tuple[ClassicalModelConfig, ...] = Field(min_length=1)
    regimes: tuple[RegimeConfig, ...] = Field(min_length=1)
    threshold: ThresholdConfig
    precision_targets: tuple[float, ...] = (0.8, 0.5)
    top_k: tuple[int, ...] = (100,)
    bootstrap: BootstrapConfig
    calibration: CalibrationConfig
    pr_recall_grid_points: int = Field(51, ge=2)

    @model_validator(mode="after")
    def _unique(self) -> ClassicalBaselineConfig:
        for name, items, key in (
            ("representation", self.representations, "rep_id"),
            ("model", self.models, "model_id"),
            ("regime", self.regimes, "regime_id"),
        ):
            ids = [getattr(i, key) for i in items]
            if len(set(ids)) != len(ids):
                raise ValueError(f"duplicate {name} ids")
        if not any(r.rep_id == "full" and r.kind == "full" for r in self.representations):
            raise ValueError("a 'full' reference representation is required")
        return self


# ---------------------------------------------------------------------- clean VQC (3A)


class AngleEncodingConfig(StrictModel):
    """Robust symmetric angle encoding (O03, PI Phase 3A).

    r = (x - median) / IQR  (fitted on vqc_train); r_c = clip(r, -clip, clip);
    theta = (pi / clip) * r_c, so theta lies in [-pi, pi].
    """

    kind: Literal["robust_symmetric"] = "robust_symmetric"
    fit_partition: Literal["vqc_train"] = "vqc_train"
    quantile_range: tuple[float, float] = (25.0, 75.0)
    clip: float = Field(3.0, gt=0)  # in IQR units; provisional (may become an ablation)


class ReadoutConfig(StrictModel):
    """O01: four-qubit parity; orientation fixed BEFORE any validation evaluation."""

    observable: Literal["parity"] = "parity"
    orientation: Literal["p_fraud_eq_1_minus_z_over_2"] = "p_fraud_eq_1_minus_z_over_2"


class VQCTrainingConfig(StrictModel):
    loss: Literal["binary_cross_entropy"] = "binary_cross_entropy"
    bce_epsilon: float = Field(1e-7, gt=0, lt=0.01)  # p clipped to [eps, 1 - eps] before log
    class_weighting: Literal["none"] = "none"  # the 4:1 subset is the imbalance handling
    simulation: Literal["exact_statevector"] = "exact_statevector"  # no shots, no noise


class OptimizerConfig(StrictModel):
    name: Literal["COBYLA"] = "COBYLA"
    max_evaluations: int = Field(ge=10, le=100_000)
    rhobeg: float = Field(1.0, gt=0)
    tol: float = Field(1e-4, gt=0)
    init: Literal["uniform_minus_pi_pi"] = "uniform_minus_pi_pi"


class SanityConfig(StrictModel):
    """Pre-registered Phase 3A pass conditions (fixed before any validation result was seen)."""

    min_auprc_ci_low_over_prevalence: float = Field(10.0, gt=0)
    min_auroc_ci_low: float = Field(0.5, ge=0.5, lt=1)
    min_relative_loss_reduction: float = Field(0.05, gt=0, lt=1)
    min_distinct_scores: int = Field(100, ge=2)


class VQCSubsetConfig(StrictModel):
    subset_id: Identifier
    legit_per_fraud: float = Field(gt=0)
    expected_rows: int | None = Field(None, ge=1)


class VQCConfig(StrictModel):
    """One clean VQC (Phase 3A). Only VQC partitions are legal (E26)."""

    vqc_id: Identifier
    fit_partition: Literal["vqc_train"] = "vqc_train"
    eval_partition: Literal["vqc_val"] = "vqc_val"
    representation: RepresentationConfig
    expected_features: tuple[str, ...]  # the selection must reproduce exactly
    encoding: AngleEncodingConfig
    subset: VQCSubsetConfig
    n_qubits: int = Field(ge=1, le=8)
    feature_map: FeatureMapConfig
    ansatz: ArchitectureConfig
    readout: ReadoutConfig
    training: VQCTrainingConfig
    optimizer: OptimizerConfig
    basis_gates: tuple[str, ...] = ("rz", "sx", "x", "cx")
    optimization_level: int = Field(1, ge=0, le=3)
    reproducibility_param_tolerance: float = Field(1e-10, gt=0)
    sanity: SanityConfig = Field(default_factory=SanityConfig)
    aer_crosscheck_examples: int = Field(1024, ge=1)
    comparison_baseline: Identifier  # classical models reused for the equal-data comparison

    @model_validator(mode="after")
    def _check(self) -> VQCConfig:
        if self.representation.n_components != self.n_qubits:
            raise ValueError("one input feature per qubit is required")
        if len(self.expected_features) != self.n_qubits:
            raise ValueError("expected_features must list one feature per qubit")
        if self.feature_map.entanglement is None or self.ansatz.entanglement is None:
            raise ValueError("entanglement must be explicit for a trained VQC")
        return self


# ------------------------------------------------------------- Phase 3A-R (repair)


class EncodingCandidateConfig(StrictModel):
    """theta = (half_width / clip) * clip((x - median) / IQR, -clip, clip), in [-hw, hw]."""

    enc_id: Identifier
    role: Literal["control", "candidate"]
    clip: float = Field(gt=0)
    half_width: float = Field(gt=0, le=3.1415926535897932)
    rationale: str


class RepairCandidateConfig(StrictModel):
    cand_id: Identifier
    encoding: Identifier
    ansatz_reps: int = Field(ge=1, le=4)
    observable: Literal["parity", "z_qubit0"]
    purpose: str


class FoldCVConfig(StrictModel):
    n_folds: int = Field(ge=2, le=10)
    grouping: Literal["features_except_time"] = "features_except_time"
    stratify: Literal["any_fraud"] = "any_fraud"
    seed_key: Identifier
    training_legit_per_fraud: float = Field(gt=0)
    evaluation: Literal["held_out_fold_natural_prevalence"] = "held_out_fold_natural_prevalence"


class RestartConfig(StrictModel):
    n_restarts: int = Field(ge=1, le=10)
    seed_key: Identifier
    rule: Literal["lowest_final_training_bce"] = "lowest_final_training_bce"


class SelectionRuleConfig(StrictModel):
    primary: Literal["mean_cv_auprc"] = "mean_cv_auprc"
    tie_tolerance: float = Field(ge=0, lt=0.1)
    tie_breakers: tuple[
        Literal["lower_cv_std", "fewer_ansatz_reps", "fewer_trainable_parameters", "matrix_order"],
        ...,
    ]
    eligibility: tuple[
        Literal["single_qubit_phase_injective", "fewer_shared_fraud_vectors_than_control"], ...
    ]


class RepairStudyConfig(StrictModel):
    """Pre-registered Phase 3A-R candidate matrix and rules (fixed before any CV run)."""

    study_id: Identifier
    base_vqc: Identifier  # the immutable P3A-original configuration
    selection_partition: Literal["vqc_train"] = "vqc_train"
    evaluation_partition: Literal["vqc_val"] = "vqc_val"
    features: tuple[str, ...]
    control_encoding: Identifier
    encodings: tuple[EncodingCandidateConfig, ...]
    candidates: tuple[RepairCandidateConfig, ...]
    cv: FoldCVConfig
    restarts: RestartConfig
    optimizer: OptimizerConfig
    selection: SelectionRuleConfig
    final_training: Literal["base_3a_subset_restarts_lowest_bce"] = (
        "base_3a_subset_restarts_lowest_bce"
    )
    collision_probe_legit_sample: int = Field(3000, ge=100)
    collision_probe_min_input_separation_iqr: float = Field(1.0, gt=0)
    collision_probe_fidelity: float = Field(0.999, gt=0.9, lt=1)

    @model_validator(mode="after")
    def _check(self) -> RepairStudyConfig:
        enc_ids = [e.enc_id for e in self.encodings]
        cand_ids = [c.cand_id for c in self.candidates]
        if len(set(enc_ids)) != len(enc_ids) or len(set(cand_ids)) != len(cand_ids):
            raise ValueError("duplicate encoding or candidate ids")
        if not 1 <= len(self.candidates) <= 12:
            raise ValueError("the primary candidate matrix is capped at 12 configurations")
        if any(c.encoding not in enc_ids for c in self.candidates):
            raise ValueError("candidate references an unknown encoding")
        roles = {e.enc_id: e.role for e in self.encodings}
        if roles.get(self.control_encoding) != "control":
            raise ValueError("control_encoding must name an encoding with role 'control'")
        if len(self.features) != 4:
            raise ValueError("Phase 3A-R keeps exactly the four 3A features")
        return self


# ------------------------------------------------------- Phase 3B (noise study)


class FrozenModelRef(StrictModel):
    model_id: Identifier
    kind: Literal["p3a_original", "p3a_r"]
    role: Literal["primary", "exploratory_contrast"]
    artifact: str
    artifact_sha256: str
    transpile_seed: int = Field(ge=0)


class A13RulesConfig(StrictModel):
    """Pre-registered, pilot-indicative label rules (NOT publication thresholds)."""

    spearman_monotonic: float = 0.999
    kendall_monotonic: float = 0.995
    topk_overlap_min: float = 0.95
    topk_for_overlap_rule: int = Field(47, ge=1)
    calibration_spearman_min: float = 0.99
    brier_relative_change: float = 0.10
    ece_abs_change: float = 0.01
    threshold_crossing_fraction: float = 0.01
    fraud_crossing_rate: float = 0.05


class E08ValidationConfig(StrictModel):
    n_rows: int = Field(ge=16)
    profiles: tuple[Identifier, ...]
    shots: int = Field(ge=64)
    seed_key: Identifier
    residual_mean_abs_max: float = 0.25
    residual_var_range: tuple[float, float] = (0.7, 1.3)
    chi2_p_min: float = 0.001
    min_expected_count: float = 5.0
    mean_score_se_multiple: float = 4.0
    tvd_ratio_range: tuple[float, float] = (0.9, 1.1)
    ks_p_min: float = 0.001


class FiniteShotConfig(StrictModel):
    shots: int = Field(ge=1)
    replicates: int = Field(ge=1)
    seed_key: Identifier
    models: tuple[Identifier, ...]


class G1RulesConfig(StrictModel):
    pass_labels: tuple[str, ...] = ("discrimination_degradation", "ranking_distortion")
    conditional_labels: tuple[str, ...] = ("calibration_distortion", "threshold_distortion")
    excluded_roles: tuple[str, ...] = ("negative_control",)
    require_severity_trend: bool = True


class NoiseStudyConfig(StrictModel):
    """Pre-registered Phase 3B controlled-noise characterization (frozen models only)."""

    study_id: Identifier
    partition: Literal["vqc_val"] = "vqc_val"
    models: tuple[FrozenModelRef, ...]
    noise_sets: tuple[Identifier, ...]
    basis_gates: tuple[str, ...] = ("rz", "sx", "x", "cx")
    optimization_level: int = Field(1, ge=0, le=3)
    one_qubit_noisy_gates: tuple[str, ...] = ("sx", "x")
    two_qubit_noisy_gates: tuple[str, ...] = ("cx",)
    gate_error_composition: Literal["depolarizing_then_thermal"] = "depolarizing_then_thermal"
    readout_application: Literal["classical_confusion_on_exact_distribution"] = (
        "classical_confusion_on_exact_distribution"
    )
    threshold_rule: Literal["max_f1_on_exact_clean_scores"] = "max_f1_on_exact_clean_scores"
    top_k: tuple[int, ...] = (47, 100, 284)
    ece_bins: int = 10
    bootstrap_resamples: int = Field(1000, ge=100)
    a13: A13RulesConfig = Field(default_factory=A13RulesConfig)
    e08: E08ValidationConfig
    finite_shot: FiniteShotConfig
    g1: G1RulesConfig = Field(default_factory=G1RulesConfig)
    representative_conditions: tuple[Identifier, ...]

    @model_validator(mode="after")
    def _check(self) -> NoiseStudyConfig:
        if sum(m.role == "primary" for m in self.models) != 1:
            raise ValueError("exactly one primary model")
        ids = [m.model_id for m in self.models]
        if not set(self.finite_shot.models) <= set(ids):
            raise ValueError("finite-shot models must be study models")
        return self


Applicability = Literal["applicable", "partial", "negative_control"]
ActionLabel = Literal["A0", "A1", "A2", "A3"]


class ReadoutCalibrationStudyConfig(StrictModel):
    """Phase 4 readout mitigation (E11): observable calibration only, no simulator parameters."""

    method: Literal["tensored"] = "tensored"
    calibration_states: tuple[str, ...] = ("all_zeros", "all_ones")
    shots_per_calibration_circuit: Literal["same_as_arm"] = "same_as_arm"
    calibration_frequency: Literal["per_context_replicate"] = "per_context_replicate"
    amortization: Literal["per_vqc_val_batch"] = "per_vqc_val_batch"
    inversion: Literal["tensored_per_qubit_inverse"] = "tensored_per_qubit_inverse"
    projection: Literal["nearest_probability_l2"] = "nearest_probability_l2"
    min_assignment_determinant: float = Field(0.5, gt=0, lt=1)


class ZNEStudyConfig(StrictModel):
    """Phase 4 ZNE (E10): global unitary folding of the transpiled circuit."""

    noise_factors: tuple[int, ...] = (1, 3, 5)
    folding: Literal["global_transpiled_unitary"] = "global_transpiled_unitary"
    inverse_translation: Literal["transpile_optimization_level_0"] = (
        "transpile_optimization_level_0"
    )
    shot_allocation: Literal["equal_per_circuit"] = "equal_per_circuit"
    primary_extrapolator: Literal["linear_least_squares"] = "linear_least_squares"
    diagnostic_extrapolators: tuple[Literal["richardson"], ...] = ("richardson",)
    clip_parity_to_physical_range: bool = True
    observable: Literal["parity"] = "parity"

    @model_validator(mode="after")
    def _factors(self) -> ZNEStudyConfig:
        f = self.noise_factors
        if f[0] != 1 or any(x % 2 == 0 for x in f) or list(f) != sorted(set(f)) or len(f) < 2:
            raise ValueError("noise factors must be odd, strictly increasing and start at 1")
        return self


class ShotBudgetConfig(StrictModel):
    arm_id: Identifier
    shots_per_circuit: int = Field(ge=1)
    role: Literal["primary", "secondary"]


class G2RulesConfig(StrictModel):
    """Pre-registered, pilot-indicative G2 rule (PREREG_P4 §13)."""

    min_delta_auprc: float = 0.01
    min_relative_brier: float = 0.10
    min_delta_f1_at_tau: float = 0.05
    min_delta_ece: float = 0.01
    min_delta_precision_recall: float = 0.05
    pass_min_auprc_cells: int = Field(2, ge=1)
    confidence: float = 0.95


class MitigationValidationConfig(StrictModel):
    ideal_unitary_tol: float = 1e-10
    phase3b_crosscheck_tol: float = 1e-9
    negative_control_score_tol: float = 1e-10
    negative_control_metric_tol: float = 1e-9
    e08_noise_factors: tuple[int, ...] = (3, 5)  # folded circuits; profiles from ``e08``
    calibration_check_profiles: tuple[Identifier, ...] = ("comb-high", "ar-050")
    calibration_check_shots: int = Field(100_000, ge=1000)
    calibration_chi2_p_min: float = 0.001


class MitigationStudyConfig(StrictModel):
    """Pre-registered Phase 4 mitigation characterization (frozen P3A-R only; PREREG_P4)."""

    study_id: Identifier
    partition: Literal["vqc_val"] = "vqc_val"
    model: FrozenModelRef
    frozen_tau: float
    noise_sets: tuple[Identifier, ...]
    conditions: tuple[Identifier, ...]
    actions: dict[ActionLabel, Identifier]  # A0..A3 -> configs/mitigation/<id>
    applicability: dict[Identifier, dict[ActionLabel, Applicability]]
    readout: ReadoutCalibrationStudyConfig = Field(default_factory=ReadoutCalibrationStudyConfig)
    zne: ZNEStudyConfig = Field(default_factory=ZNEStudyConfig)
    shot_budgets: tuple[ShotBudgetConfig, ...]
    replicates: int = Field(ge=2)
    resource_matched_multipliers: tuple[int, ...] = (3, 9)
    seed_key: Identifier
    e08: E08ValidationConfig
    validation: MitigationValidationConfig = Field(default_factory=MitigationValidationConfig)
    primary_cost: Literal["total_shots_per_logical_inference"] = "total_shots_per_logical_inference"
    top_k: tuple[int, ...] = (47, 100, 284)
    ece_bins: int = 10
    bootstrap_resamples: int = Field(1000, ge=100)
    bootstrap_scheme: Literal["two_stage_transactions_and_replicate"] = (
        "two_stage_transactions_and_replicate"
    )
    g2: G2RulesConfig = Field(default_factory=G2RulesConfig)
    representative_conditions: tuple[Identifier, ...]

    @model_validator(mode="after")
    def _check(self) -> MitigationStudyConfig:
        if self.model.role != "primary" or self.model.kind != "p3a_r":
            raise ValueError("Phase 4 uses the frozen primary P3A-R model only")
        if self.conditions[0] != "clean" or len(set(self.conditions)) != len(self.conditions):
            raise ValueError("conditions must start with clean and be unique")
        if list(self.actions) != ["A0", "A1", "A2", "A3"]:
            raise ValueError("actions must be exactly A0 (none), A1, A2, A3")
        if set(self.applicability) != set(self.conditions):
            raise ValueError("applicability must cover every condition")
        for cond, row in self.applicability.items():
            if set(row) != {"A1", "A2", "A3"}:
                raise ValueError(f"applicability of {cond} must label A1, A2 and A3")
        if [b.role for b in self.shot_budgets].count("primary") != 1:
            raise ValueError("exactly one primary shot budget")
        if not set(self.representative_conditions) <= set(self.conditions):
            raise ValueError("representative conditions must be study conditions")
        return self


class PoolFeatureSetConfig(StrictModel):
    """A train-only input representation for the Phase 5A pool (4 outputs = 4 qubits)."""

    feat_id: Identifier
    kind: Literal["anova_ranks", "pca"]
    ranks: tuple[int, int] | None = None  # 1-based inclusive ANOVA-F ranks (anova_ranks)
    standardize: bool = False  # pca only
    expected_features: tuple[str, ...] | None = None  # anova_ranks: must reproduce exactly

    @model_validator(mode="after")
    def _check(self) -> PoolFeatureSetConfig:
        if self.kind == "anova_ranks":
            if self.ranks is None or self.ranks[1] - self.ranks[0] != 3 or self.ranks[0] < 1:
                raise ValueError("anova_ranks needs exactly four consecutive 1-based ranks")
        elif self.ranks is not None or self.expected_features is not None:
            raise ValueError("pca takes no ranks or expected features")
        return self


class PoolEncodingConfig(StrictModel):
    """r = (x - median)/IQR on vqc_train; theta in [-hw, hw] by clipping or tanh (alias-safe)."""

    enc_id: Identifier
    kind: Literal["clip_linear", "tanh"]
    scale: float = Field(gt=0)  # clip level (clip_linear) or tanh scale, in IQR units
    half_width: float = Field(gt=0)

    @model_validator(mode="after")
    def _alias_safe(self) -> PoolEncodingConfig:
        if self.half_width >= 1.5707963267948966:
            raise ValueError("primary-pool encodings must be alias-safe (half-width < pi/2)")
        return self


class PoolAnsatzConfig(StrictModel):
    ans_id: Identifier
    family: Literal["real_amplitudes", "efficient_su2"]
    reps: int = Field(ge=0, le=4)
    entanglement: Literal["linear"] = "linear"


class PoolStructureConfig(StrictModel):
    struct_id: Identifier
    features: Identifier
    encoding: Identifier
    ansatz: Identifier
    readout: Literal["parity", "mean_z"]


class PoolControlConfig(StrictModel):
    """Diagnostic controls: never part of the primary pool."""

    control_id: Identifier
    kind: Literal["existing_artifact", "structure"]
    artifact: str | None = None
    artifact_sha256: str | None = None
    transpile_seed: int | None = None
    structure: PoolStructureConfig | None = None
    seed_index: int | None = None
    reason: str


class PoolQualificationConfig(StrictModel):
    """Pre-registered clean-validity criteria (PREREG_P5A §8); broad by design."""

    min_auprc_ci_low_over_prevalence: float = 10.0
    min_auroc_ci_low: float = 0.5
    min_relative_loss_reduction: float = 0.05
    min_distinct_scores: int = 100
    max_shared_fraud_vector_fraction: float = 0.5
    aer_crosscheck_rows: int = Field(256, ge=16)
    aer_crosscheck_tol: float = 1e-10
    require_bitwise_retrain: bool = True
    near_duplicate_spearman: float = 0.9999  # reported, not an exclusion


class G3ARulesConfig(StrictModel):
    min_qualified: int = 40
    min_models_per_level: int = 3
    pass_max_median_between_structure_spearman: float = 0.95
    fail_min_median_between_structure_spearman: float = 0.99
    identical_spearman: float = 0.999
    pass_max_identical_pair_fraction: float = 0.05
    fail_min_identical_pair_fraction: float = 0.5
    max_family_share: float = 0.75
    max_seed_share: float = 0.40
    max_structure_share: float = 0.15
    pass_max_projected_wall_hours: float = 48.0
    fail_min_projected_wall_hours: float = 168.0


class PoolPowerConfig(StrictModel):
    alpha: float = 0.05
    power: float = 0.80
    model_counts: tuple[int, ...] = (20, 30, 40, 50, 60)
    replicate_counts: tuple[int, ...] = (5, 10, 20)
    meta_test_fraction: float = 0.25


class PoolBenchmarkConfig(StrictModel):
    rows: int = Field(256, ge=16)
    noise_profile: Identifier = "comb-high"
    noise_factors: tuple[int, ...] = (1, 3, 5)
    cores: int = Field(15, ge=1)


class PoolStudyConfig(StrictModel):
    """Pre-registered Phase 5A independent VQC pool (PREREG_P5A)."""

    study_id: Identifier
    fit_partition: Literal["vqc_train"] = "vqc_train"
    qualify_partition: Literal["vqc_val"] = "vqc_val"
    n_qubits: Literal[4] = 4
    feature_map: FeatureMapConfig
    feature_sets: tuple[PoolFeatureSetConfig, ...]
    encodings: tuple[PoolEncodingConfig, ...]
    ansatze: tuple[PoolAnsatzConfig, ...]
    structures: tuple[PoolStructureConfig, ...]
    seeds_per_structure: int = Field(ge=1, le=10)
    subset_legit_per_fraud: float = Field(gt=0)
    subset_id_prefix: Identifier
    optimizer: OptimizerConfig
    restarts: int = Field(ge=1, le=10)
    restart_rule: Literal["lowest_final_training_bce"] = "lowest_final_training_bce"
    bce_epsilon: float = Field(1e-7, gt=0)
    basis_gates: tuple[str, ...] = ("rz", "sx", "x", "cx")
    optimization_level: int = Field(1, ge=0, le=3)
    seed_keys: dict[str, Identifier]
    qualification: PoolQualificationConfig = Field(default_factory=PoolQualificationConfig)
    threshold_rule: Literal["max_f1_on_clean_vqc_val"] = "max_f1_on_clean_vqc_val"
    bootstrap_resamples: int = Field(1000, ge=100)
    anchor: FrozenModelRef
    controls: tuple[PoolControlConfig, ...] = ()
    g3a: G3ARulesConfig = Field(default_factory=G3ARulesConfig)
    power: PoolPowerConfig = Field(default_factory=PoolPowerConfig)
    benchmark: PoolBenchmarkConfig = Field(default_factory=PoolBenchmarkConfig)

    @model_validator(mode="after")
    def _check(self) -> PoolStudyConfig:
        for name, items, key in (
            ("feature_sets", self.feature_sets, "feat_id"),
            ("encodings", self.encodings, "enc_id"),
            ("ansatze", self.ansatze, "ans_id"),
            ("structures", self.structures, "struct_id"),
        ):
            ids = [getattr(i, key) for i in items]
            if len(set(ids)) != len(ids):
                raise ValueError(f"duplicate id in {name}")
        feats = {f.feat_id for f in self.feature_sets}
        encs = {e.enc_id for e in self.encodings}
        ans = {a.ans_id for a in self.ansatze}
        for st in self.structures:
            if st.features not in feats or st.encoding not in encs or st.ansatz not in ans:
                raise ValueError(f"structure {st.struct_id} references an unknown component")
            expected = f"{st.features}-{st.encoding}-{st.ansatz}-{st.readout}"
            if st.struct_id != expected:
                raise ValueError(f"struct_id must be {expected!r}")
        keys = {"subset", "init", "transpile"}
        if set(self.seed_keys) != keys:
            raise ValueError(f"seed_keys must be exactly {sorted(keys)}")
        return self


class StructureSplitConfig(StrictModel):
    """Primary model split by STRUCTURE (all seeds of a structure stay together)."""

    train: tuple[Identifier, ...]
    val: tuple[Identifier, ...]
    test: tuple[Identifier, ...]

    @model_validator(mode="after")
    def _disjoint(self) -> StructureSplitConfig:
        all_ = [*self.train, *self.val, *self.test]
        if len(set(all_)) != len(all_):
            raise ValueError("a structure may belong to exactly one split")
        return self


class GateProbeConfig(StrictModel):
    bindings: int = Field(32, ge=4, le=256)
    angle_half_width: float = Field(gt=0, lt=1.5707963267948966)
    noise_factors: tuple[int, ...] = (1, 3)
    seed_key: Identifier


class ProbeCategoryConfig(StrictModel):
    """A priori probe categories for the DESCRIPTIVE Q6 analysis (not a fitted rule)."""

    readout_error_min: float = Field(gt=0)
    gate_contraction_max: float = Field(gt=0, lt=1)


class HeterogeneityConfig(StrictModel):
    alpha: float = 0.05
    correction: Literal["holm"] = "holm"
    icc_min: float = 0.10
    permutations: int = Field(2000, ge=200)
    permutation_seed_key: Identifier


class G3BRulesConfig(StrictModel):
    fail_dominance_share: float = 0.90
    fail_min_improvable_fraction: float = 0.10
    improvable_relative_brier: float = 0.10
    fail_min_split_half_agreement: float = 0.60
    fail_min_rule_gain: float = 0.05
    fail_max_rule_failure: float = 0.05
    pass_min_action_share: float = 0.10
    pass_min_actions_useful: int = 2
    pass_min_universal_failure: float = 0.25
    pass_min_rule_gain: float = 0.20
    pass_min_rule_failure: float = 0.15
    pass_min_heterogeneous_cell_fraction: float = 0.25
    pass_max_structure_association_p: float = 0.05


class CounterfactualStudyConfig(StrictModel):
    """Pre-registered Phase 5B cross-model counterfactual study (PREREG_P5B)."""

    study_id: Identifier
    pool_study: Identifier
    pool_manifest: str
    pool_manifest_sha256: str
    mitigation_study: Identifier
    conditions: tuple[Identifier, ...]
    shot_budgets: tuple[ShotBudgetConfig, ...]
    replicates: int = Field(ge=2)
    actions: dict[Literal["A0", "A1", "A2", "A3", "A4"], Identifier]
    extra_shots_multiplier: int = Field(3, ge=2)
    diagnostic_vectors: tuple[Literal["RM9"], ...] = ("RM9",)
    cost_order: tuple[Literal["A0", "A1", "A2", "A3", "A4"], ...]
    structure_split: StructureSplitConfig
    partition_of: dict[
        Literal["train", "val", "test"], Literal["ctrl_train", "ctrl_val", "ctrl_test"]
    ]
    secondary_split_holdout_seed: int = Field(3, ge=0)
    panel_kind: Literal["full_partition"] = "full_partition"
    gate_probe: GateProbeConfig
    readout_probe_reused_by: tuple[Literal["A1", "A3"], ...] = ("A1", "A3")
    static_features: tuple[str, ...]
    probe_features: tuple[str, ...]
    prohibited_features: tuple[str, ...]
    preferred_endpoint: Literal["brier"] = "brier"
    preferred_relative_tolerance: float = 0.10
    secondary_endpoint: Literal["f1"] = "f1"
    secondary_tolerance: float = 0.05
    probe_categories: ProbeCategoryConfig
    heterogeneity: HeterogeneityConfig
    g3b: G3BRulesConfig = Field(default_factory=G3BRulesConfig)
    seed_key: Identifier
    validation_head_rows: int = Field(256, ge=16)
    validation_tol: float = 1e-10
    processed_dir: str
    lockbox_dir: str

    @model_validator(mode="after")
    def _check(self) -> CounterfactualStudyConfig:
        if list(self.actions) != ["A0", "A1", "A2", "A3", "A4"]:
            raise ValueError("actions must be exactly A0..A4")
        if sorted(self.cost_order) != ["A0", "A1", "A2", "A3", "A4"]:
            raise ValueError("cost_order must list every action once")
        if (
            set(self.partition_of) != {"train", "val", "test"}
            or len(set(self.partition_of.values())) != 3
        ):
            raise ValueError("each split maps to its own controller partition (A04)")
        clash = set(self.prohibited_features) & (
            set(self.static_features) | set(self.probe_features)
        )
        if clash:
            raise ValueError(f"prohibited features listed as inputs: {sorted(clash)}")
        if not self.lockbox_dir.startswith("results/lockbox/"):
            raise ValueError("test-partition outputs must live under results/lockbox/")
        return self


class MixedNoiseAnchors(StrictModel):
    """Physical values at anchor severities 0 (absent), 1, 2, 3 ([RR] low/medium/high)."""

    readout_mean: tuple[float, float, float, float]
    depolarizing_p1: tuple[float, float, float, float]
    depolarizing_p2: tuple[float, float, float, float]
    thermal_rate1_per_us: tuple[float, float, float, float]  # 1/T1
    thermal_rate2_per_us: tuple[float, float, float, float]  # 1/T2

    @model_validator(mode="after")
    def _check(self) -> MixedNoiseAnchors:
        for name in type(self).model_fields:
            v = getattr(self, name)
            if v[0] != 0 or any(b <= a for a, b in zip(v, v[1:], strict=False)):
                raise ValueError(f"{name} must start at 0 and increase strictly")
        for g1, g2 in zip(self.thermal_rate1_per_us, self.thermal_rate2_per_us, strict=True):
            if g2 < g1 / 2:  # T2 <= 2 T1 at every anchor (and so on every segment)
                raise ValueError("thermal anchors violate T2 <= 2*T1")
        return self


class MixedNoiseDesignConfig(StrictModel):
    """Split-plot space-filling design over anchor severities (PREREG_P5C §4)."""

    anchors: MixedNoiseAnchors
    severity_max: float = Field(3.0, gt=0, le=3.0)  # never beyond the "high" anchor
    asymmetry_max: float = Field(0.5, ge=0, le=0.5)  # the validated synthetic split
    gate_plots: int = Field(ge=4)
    gate_free_plot: bool = True
    readout_points_per_plot: int = Field(ge=2)
    lhs_candidates: int = Field(ge=1)
    region_cut: float = Field(1.0, gt=0)
    seed_key: Identifier
    design_sha256: str


class PolicyRuleConfig(StrictModel):
    """Simple probe rules fitted on TRAIN replicates (PREREG_P5C §9)."""

    threshold_quantiles: tuple[float, ...]
    readout_feature: str = "probe_readout_error_mean"
    gate_feature: str = "probe_gate_contraction"
    group_descriptor: str = "readout_observable"


class G3CRulesConfig(StrictModel):
    fail_dominance_share: float = 0.90
    fail_max_rule_failure: float = 0.05
    fail_max_rule_material_failure: float = 0.05
    fail_min_split_half_agreement: float = 0.60
    pass_min_action_share: float = 0.10
    pass_min_actions_useful: int = 2
    pass_min_rule_failure: float = 0.15
    pass_min_noise_only_failure: float = 0.10
    pass_min_structure_noise_only_failure: float = 0.05
    pass_min_structures_val: int = 2
    pass_min_structures_train: int = 3
    pass_min_failure_above_label_noise: float = 0.10
    pass_min_material_failure: float = 0.10
    pass_min_action_structures_train: int = 3
    pass_min_action_structures_val: int = 2
    pass_max_single_structure_failure_share: float = 0.60


class MixedNoiseStudyConfig(StrictModel):
    """Pre-registered Phase 5C continuous mixed-noise study (PREREG_P5C).

    Pool, structure split, controller panels, actions, cost order, probes, static and
    probe features are INHERITED from ``base_study`` (Phase 5B) and must not change.
    """

    study_id: Identifier
    base_study: Identifier
    design: MixedNoiseDesignConfig
    shot_budgets: tuple[ShotBudgetConfig, ...]
    replicates: int = Field(ge=4)
    outcome_metrics: tuple[Literal["brier", "ece", "auprc", "auroc", "threshold"], ...]
    preferred_relative_tolerance: float = Field(0.10, gt=0)
    tolerance_sensitivity: tuple[float, ...] = (0.05, 0.20)
    material_reliability_multiple: float = Field(2.0, gt=1)
    material_overspend_shots_fraction: float = Field(1.0, gt=0)
    rules: PolicyRuleConfig
    label_bootstrap: int = Field(200, ge=50)
    cluster_bootstrap: int = Field(2000, ge=200)
    bootstrap_seed_key: Identifier
    permutations: int = Field(2000, ge=200)
    permutation_seed_key: Identifier
    g3c: G3CRulesConfig = Field(default_factory=G3CRulesConfig)
    additional_prohibited_features: tuple[str, ...]
    seed_key: Identifier
    validation_head_rows: int = Field(256, ge=16)
    validation_tol: float = 1e-10
    processed_dir: str
    lockbox_dir: str

    @model_validator(mode="after")
    def _check(self) -> MixedNoiseStudyConfig:
        if not self.lockbox_dir.startswith("results/lockbox/"):
            raise ValueError("test-partition outputs must live under results/lockbox/")
        if len({b.arm_id for b in self.shot_budgets}) != len(self.shot_budgets):
            raise ValueError("duplicate shot-budget arm")
        if self.preferred_relative_tolerance in self.tolerance_sensitivity:
            raise ValueError("sensitivity tolerances must differ from the primary tolerance")
        q = self.rules.threshold_quantiles
        if any(not 0 < x < 1 for x in q) or list(q) != sorted(set(q)):
            raise ValueError("threshold quantiles must be strictly increasing in (0, 1)")
        return self


# ---------------------------------------------------------------------- experiment


class ExperimentSpec(StrictModel):
    """An experiment file as written: components are referenced by id."""

    experiment_id: Identifier
    protocol_version: str
    description: str = ""
    reporting: Literal["dev", "reported"] = "dev"
    dataset: Identifier | None = None
    model_pool: Identifier | None = None
    noise: Identifier | None = None
    mitigation: tuple[Identifier, ...] = ()
    baseline: Identifier | None = None
    vqc: Identifier | None = None
    execution: ExecutionConfig | None = None  # absent for data-preparation runs
    seeds: SeedConfig


class ResolvedExperiment(StrictModel):
    """An experiment with every referenced component loaded and validated."""

    spec: ExperimentSpec
    dataset: DatasetConfig | None = None
    model_pool: ModelPoolConfig | None = None
    noise: NoiseProfileSet | None = None
    mitigation: tuple[MitigationConfig, ...] = ()
    baseline: ClassicalBaselineConfig | None = None
    vqc: VQCConfig | None = None

    def config_hash(self) -> str:
        return stable_hash(self)

    def component_hashes(self) -> dict[str, str]:
        out = {"experiment_spec": stable_hash(self.spec)}
        if self.dataset is not None:
            out["dataset"] = stable_hash(self.dataset)
        if self.model_pool is not None:
            out["model_pool"] = stable_hash(self.model_pool)
        if self.noise is not None:
            out["noise"] = stable_hash(self.noise)
        for m in self.mitigation:
            out[f"mitigation/{m.action_id}"] = stable_hash(m)
        if self.baseline is not None:
            out["baseline"] = stable_hash(self.baseline)
        if self.vqc is not None:
            out["vqc"] = stable_hash(self.vqc)
        return out
