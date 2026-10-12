"""Evaluation-panel interface only (O06 open).

Panel size, prevalence, sampling strategy, weighting and the number of panels
are deliberately NOT decided here. This module only fixes what any future
panel must satisfy: it comes from one allowed partition (never ``vqc_train``),
has unique row ids, optional positive weights, and a reproducible hash.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

import pandas as pd
from pydantic import BaseModel, ConfigDict, Field, model_validator

from qtrace.data.duplicates import row_ids_sha256
from qtrace.data.ingest import ROW_ID
from qtrace.data.partition import PARTITION
from qtrace.utils.hashing import stable_hash

PanelPartition = Literal["vqc_val", "ctrl_train", "ctrl_val", "ctrl_test"]


class PanelError(ValueError):
    pass


class Panel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    panel_id: str = Field(pattern=r"^[a-z0-9][a-z0-9_\-]*$")
    source_partition: PanelPartition
    row_ids: tuple[int, ...] = Field(min_length=1)
    weights: tuple[float, ...] | None = None
    sampling: dict[str, Any]  # free-form description of the (future) strategy; O06
    seed: int | None = None

    @model_validator(mode="after")
    def _check(self) -> Panel:
        if len(set(self.row_ids)) != len(self.row_ids):
            raise ValueError("panel row ids must be unique")
        if self.weights is not None:
            if len(self.weights) != len(self.row_ids):
                raise ValueError("weights must align with row ids")
            if any(not w > 0 for w in self.weights):
                raise ValueError("weights must be positive")
        return self

    def panel_hash(self) -> str:
        return stable_hash(
            {
                "source_partition": self.source_partition,
                "row_ids": row_ids_sha256(list(self.row_ids)),
                "weights": self.weights,
                "sampling": self.sampling,
                "seed": self.seed,
            }
        )


def validate_panel_membership(panel: Panel, assignment: pd.DataFrame) -> None:
    """Raise unless every panel row belongs to the panel's source partition."""
    lookup = assignment.set_index(ROW_ID)[PARTITION]
    missing = [i for i in panel.row_ids if i not in lookup.index]
    if missing:
        raise PanelError(f"{len(missing)} panel rows are not in the partition table")
    wrong = lookup.loc[list(panel.row_ids)] != panel.source_partition
    if wrong.any():
        raise PanelError(f"{int(wrong.sum())} panel rows lie outside {panel.source_partition!r}")


class PanelSampler(ABC):
    """Interface for future panel strategies (designed before Phase 6; O06)."""

    @abstractmethod
    def sample(
        self,
        frame: pd.DataFrame,
        assignment: pd.DataFrame,
        *,
        source_partition: PanelPartition,
        seed: int,
    ) -> Panel:
        """Return a panel drawn from ``source_partition`` only."""
