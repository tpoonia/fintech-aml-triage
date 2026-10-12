"""Controller-input table (A12, A15): ONLY registry-deployable, pre-action observables.

Grouping keys (model, context, replicate, split) live in a separate key frame and are never
features. Every feature name is checked against the registry (``assert_deployable``) and
against the study's prohibited list before the table is returned.
"""

from __future__ import annotations

import pandas as pd

from qtrace.config.schemas import CounterfactualStudyConfig
from qtrace.features import FeatureRegistry, LeakageError, assert_deployable

KEY_COLUMNS = ("model_id", "struct_id", "split", "partition", "condition", "arm", "replicate")


def feature_names(study: CounterfactualStudyConfig) -> tuple[str, ...]:
    return (*study.static_features, *study.probe_features)


def check_features(names, study: CounterfactualStudyConfig, registry: FeatureRegistry) -> None:
    bad = set(names) & set(study.prohibited_features)
    if bad:
        raise LeakageError(f"prohibited controller features: {sorted(bad)}")
    assert_deployable(names, registry)


def controller_table(
    rep: pd.DataFrame,
    static: dict[str, dict],
    study: CounterfactualStudyConfig,
    registry: FeatureRegistry,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(keys, features) aligned row by row; one row per context replicate."""
    names = feature_names(study)
    check_features(names, study, registry)
    rep = rep.reset_index(drop=True)
    stat = pd.DataFrame([static[m] for m in rep.model_id])
    stat["shots_per_circuit"] = rep.shots_per_circuit.to_numpy()
    feats = pd.concat([stat, rep[list(study.probe_features)]], axis=1)[list(names)]
    keys = rep[list(KEY_COLUMNS)].copy()
    check_features(feats.columns, study, registry)
    return keys, feats


# ---------------------------------------------------------------- Phase 5C (same inputs)

MIXED_KEY_COLUMNS = (
    "model_id",
    "struct_id",
    "split",
    "partition",
    "point_id",
    "gate_plot",
    "arm",
    "replicate",
)


def mixed_prohibited(base: CounterfactualStudyConfig, study) -> tuple[str, ...]:
    """Phase 5B prohibited list plus the Phase 5C design truth (never controller inputs)."""
    return (*base.prohibited_features, *study.additional_prohibited_features)


def mixed_controller_table(
    rep: pd.DataFrame,
    static: dict[str, dict],
    base: CounterfactualStudyConfig,
    study,
    registry: FeatureRegistry,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """(keys, features) for Phase 5C: the Phase 5B static + probe inputs, nothing else."""
    names = feature_names(base)
    banned = set(mixed_prohibited(base, study))

    def check(cols) -> None:
        bad = set(cols) & banned
        if bad:
            raise LeakageError(f"prohibited controller features: {sorted(bad)}")
        assert_deployable(cols, registry)

    check(names)
    rep = rep.reset_index(drop=True)
    stat = pd.DataFrame([static[m] for m in rep.model_id])
    stat["shots_per_circuit"] = rep.shots_per_circuit.to_numpy()
    feats = pd.concat([stat, rep[list(base.probe_features)]], axis=1)[list(names)]
    check(feats.columns)
    return rep[list(MIXED_KEY_COLUMNS)].copy(), feats
