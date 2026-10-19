"""Run manifest: one JSON document per run recording exactly what was executed."""

from __future__ import annotations

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class _Record(BaseModel):
    model_config = ConfigDict(extra="forbid")


class GitState(_Record):
    commit: str | None  # None only before the first commit
    branch: str | None = None
    dirty: bool


class EnvironmentInfo(_Record):
    python_version: str
    platform: str
    packages: dict[str, str]


class HardwareInfo(_Record):
    machine: str
    cpu_model: str
    cpu_count: int | None
    memory_bytes: int | None


class OutputRecord(_Record):
    path: str
    sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


class RunManifest(_Record):
    run_id: str
    experiment_id: str
    protocol_version: str
    reporting: Literal["dev", "reported"]
    status: Literal["running", "completed", "failed"]
    command: list[str]
    resolved_config: dict[str, Any]
    config_hash: str = Field(pattern=r"^[0-9a-f]{64}$")
    component_hashes: dict[str, str]
    git: GitState
    environment: EnvironmentInfo
    hardware: HardwareInfo
    seeds: dict[str, int]
    started_utc: datetime
    finished_utc: datetime | None = None
    outputs: list[OutputRecord] = Field(default_factory=list)
    notes: str = ""

    @model_validator(mode="after")
    def _reported_runs_are_traceable(self) -> RunManifest:
        # PROJECT_SPEC §12: reported numbers come only from a clean, committed tree.
        if self.reporting == "reported" and (self.git.commit is None or self.git.dirty):
            raise ValueError("reported runs require a committed, clean git tree")
        if self.status == "completed" and self.finished_utc is None:
            raise ValueError("completed runs need finished_utc")
        return self
