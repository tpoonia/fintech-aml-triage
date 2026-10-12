"""Load, validate and resolve YAML configs.

Experiment files reference components by id; ``load_experiment`` resolves each
reference to ``configs/<family dir>/<id>.yaml`` and validates it. The id inside
a component file must match its file name, so a reference can never silently
load a different config.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel

from qtrace.config.schemas import (
    ClassicalBaselineConfig,
    CounterfactualStudyConfig,
    DatasetConfig,
    ExperimentSpec,
    MitigationConfig,
    MitigationStudyConfig,
    MixedNoiseStudyConfig,
    ModelPoolConfig,
    NoiseProfileSet,
    NoiseStudyConfig,
    PoolStudyConfig,
    RepairStudyConfig,
    ResolvedExperiment,
    VQCConfig,
)

# family -> (directory under configs/, schema, id field inside the file)
FAMILIES: dict[str, tuple[str, type[BaseModel], str]] = {
    "dataset": ("datasets", DatasetConfig, "dataset_id"),
    "model_pool": ("qml", ModelPoolConfig, "pool_id"),
    "noise": ("noise", NoiseProfileSet, "set_id"),
    "mitigation": ("mitigation", MitigationConfig, "action_id"),
    "baseline": ("baselines", ClassicalBaselineConfig, "baseline_id"),
    "vqc": ("vqc", VQCConfig, "vqc_id"),
    "repair": ("repair", RepairStudyConfig, "study_id"),
    "noise_study": ("noise_study", NoiseStudyConfig, "study_id"),
    "mitigation_study": ("mitigation_study", MitigationStudyConfig, "study_id"),
    "pool_study": ("model_pool", PoolStudyConfig, "study_id"),
    "counterfactual_study": ("counterfactual_study", CounterfactualStudyConfig, "study_id"),
    "mixed_noise_study": ("mixed_noise_study", MixedNoiseStudyConfig, "study_id"),
    "experiment": ("experiments", ExperimentSpec, "experiment_id"),
}


class ConfigError(ValueError):
    """Raised for malformed or inconsistent config files."""


class _UniqueKeyLoader(yaml.SafeLoader):
    """SafeLoader that rejects duplicate mapping keys instead of silently overwriting."""


def _construct_mapping(loader: _UniqueKeyLoader, node: yaml.MappingNode, deep: bool = False):
    seen: set[Any] = set()
    for key_node, _ in node.value:
        key = loader.construct_object(key_node, deep=deep)
        if key in seen:
            raise ConfigError(f"duplicate key {key!r} at line {key_node.start_mark.line + 1}")
        seen.add(key)
    return loader.construct_mapping(node, deep=deep)


_UniqueKeyLoader.add_constructor(yaml.resolver.BaseResolver.DEFAULT_MAPPING_TAG, _construct_mapping)


def repo_root() -> Path:
    # src/qtrace/config/loader.py -> repository root
    return Path(__file__).resolve().parents[3]


def default_config_root() -> Path:
    env = os.environ.get("QTRACE_CONFIG_ROOT")
    return Path(env) if env else repo_root() / "configs"


def load_yaml(path: str | Path) -> dict[str, Any]:
    with Path(path).open(encoding="utf-8") as handle:
        data = yaml.load(handle, Loader=_UniqueKeyLoader)  # noqa: S506 - safe loader subclass
    if not isinstance(data, dict):
        raise ConfigError(f"{path}: top level must be a mapping")
    return data


def load_model[M: BaseModel](path: str | Path, schema: type[M]) -> M:
    return schema.model_validate(load_yaml(path))


def load_component(family: str, component_id: str, root: str | Path | None = None) -> BaseModel:
    if family not in FAMILIES:
        raise ConfigError(f"unknown config family {family!r}")
    directory, schema, id_field = FAMILIES[family]
    path = Path(root or default_config_root()) / directory / f"{component_id}.yaml"
    if not path.is_file():
        raise ConfigError(f"{family} config {component_id!r} not found at {path}")
    model = load_model(path, schema)
    if getattr(model, id_field) != component_id:
        raise ConfigError(f"{path}: {id_field}={getattr(model, id_field)!r} != file name")
    return model


def resolve_experiment(spec: ExperimentSpec, root: str | Path | None = None) -> ResolvedExperiment:
    def opt(family: str, ref: str | None) -> Any:
        return None if ref is None else load_component(family, ref, root)

    return ResolvedExperiment(
        spec=spec,
        dataset=opt("dataset", spec.dataset),
        model_pool=opt("model_pool", spec.model_pool),
        noise=opt("noise", spec.noise),
        mitigation=tuple(load_component("mitigation", m, root) for m in spec.mitigation),
        baseline=opt("baseline", spec.baseline),
        vqc=opt("vqc", spec.vqc),
    )


def load_experiment(experiment_id: str, root: str | Path | None = None) -> ResolvedExperiment:
    spec = load_component("experiment", experiment_id, root)
    assert isinstance(spec, ExperimentSpec)
    return resolve_experiment(spec, root)
