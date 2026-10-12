"""Schema of one policy decision evaluated on one context."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator

Action = Literal["none", "readout", "zne", "combined", "pec"]


class PolicyDecision(BaseModel):
    model_config = ConfigDict(extra="forbid")

    policy_id: str
    policy_config_hash: str
    is_oracle: bool
    deployable: bool
    # A11: policies are tuned on meta_train/meta_val only; meta_test is not a legal value.
    tuned_on: tuple[Literal["meta_train", "meta_val"], ...] = ()
    evaluated_on: Literal["meta_train", "meta_val", "meta_test"]
    context_id: str
    chosen_action: Action
    predicted_benefit: dict[Action, float] | None = None
    lambda_cost: float | None = Field(None, ge=0)
    budget: float | None = Field(None, ge=0)
    # A08: replicate used to *select* (oracle only) and replicate used to *score*.
    selection_replicate_id: int | None = Field(None, ge=0)
    evaluation_replicate_id: int | None = Field(None, ge=0)

    @model_validator(mode="after")
    def _check(self) -> PolicyDecision:
        if self.is_oracle:
            if self.deployable:
                raise ValueError("the oracle is evaluation-only and never deployable")
            if self.selection_replicate_id is None or self.evaluation_replicate_id is None:
                raise ValueError("oracle decisions must record selection and evaluation replicates")
            if self.selection_replicate_id == self.evaluation_replicate_id:
                raise ValueError("oracle must select and be scored on independent replicates (A08)")
        elif self.selection_replicate_id is not None:
            raise ValueError("non-oracle policies cannot select using realized outcomes")
        if self.lambda_cost is not None and self.budget is not None:
            raise ValueError("specify either lambda_cost or budget, not both")
        return self
