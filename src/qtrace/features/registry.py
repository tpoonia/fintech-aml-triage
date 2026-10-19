"""Feature registry: the single list of what Q-TRACE may see (PROJECT_SPEC rules R2/R3).

Every candidate input is declared in ``configs/features/registry.yaml`` with its
group, when it becomes available, and whether it is deployable. Identifiers,
labels and post-mitigation outcomes are ``offline_only`` (A12): they may appear
in offline analysis tables but never as predictor inputs.
"""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

from pydantic import Field, model_validator

from qtrace.config.loader import default_config_root, load_model
from qtrace.config.schemas import StrictModel

Controller = Literal["qtrace_s", "qtrace_a"]
NON_DEPLOYABLE_GROUPS = frozenset({"identifier", "label", "outcome"})


class LeakageError(ValueError):
    """A policy requested an input that is unknown or not deployable."""


class FeatureSpec(StrictModel):
    name: str = Field(pattern=r"^[a-z][a-z0-9_]*$")
    group: Literal[
        "noise",
        "circuit",
        "model",
        "execution",
        "probe",
        "history",
        "identifier",
        "label",
        "outcome",
    ]
    availability: Literal["pre_execution", "frozen_at_training", "probe", "history", "offline"]
    status: Literal["deployable", "offline_only"]
    controllers: tuple[Controller, ...] = ()
    description: str
    source: str
    constraint: str | None = None
    decisions: tuple[str, ...] = ()

    @model_validator(mode="after")
    def _consistent(self) -> FeatureSpec:
        if self.status == "deployable":
            if self.group in NON_DEPLOYABLE_GROUPS:
                raise ValueError(f"{self.name}: {self.group} features cannot be deployable (A12)")
            if self.availability == "offline":
                raise ValueError(f"{self.name}: offline-only availability cannot be deployable")
            if not self.controllers:
                raise ValueError(f"{self.name}: deployable features must list controllers")
            if self.availability == "history" and self.controllers != ("qtrace_a",):
                raise ValueError(f"{self.name}: labelled history is for Q-TRACE-A only (F19)")
        elif self.controllers:
            raise ValueError(f"{self.name}: offline_only features cannot list controllers")
        return self


class FeatureRegistry(StrictModel):
    version: str
    features: tuple[FeatureSpec, ...] = Field(min_length=1)

    @model_validator(mode="after")
    def _unique(self) -> FeatureRegistry:
        names = [f.name for f in self.features]
        if len(set(names)) != len(names):
            raise ValueError("duplicate feature names in registry")
        return self

    def get(self, name: str) -> FeatureSpec | None:
        return next((f for f in self.features if f.name == name), None)

    def deployable(self, controller: Controller = "qtrace_s") -> tuple[str, ...]:
        return tuple(
            f.name
            for f in self.features
            if f.status == "deployable" and controller in f.controllers
        )


def default_registry_path() -> Path:
    return default_config_root() / "features" / "registry.yaml"


def load_registry(path: str | Path | None = None) -> FeatureRegistry:
    return load_model(path or default_registry_path(), FeatureRegistry)


def assert_deployable(
    names: Iterable[str], registry: FeatureRegistry, controller: Controller = "qtrace_s"
) -> None:
    """Raise :class:`LeakageError` unless every name is a deployable input for ``controller``."""
    problems: list[str] = []
    for name in names:
        spec = registry.get(name)
        if spec is None:
            problems.append(f"{name}: not declared in the feature registry")
        elif spec.status != "deployable":
            problems.append(f"{name}: {spec.status} ({spec.group})")
        elif controller not in spec.controllers:
            problems.append(f"{name}: not available to {controller}")
    if problems:
        raise LeakageError("non-deployable Q-TRACE inputs:\n  " + "\n  ".join(problems))
