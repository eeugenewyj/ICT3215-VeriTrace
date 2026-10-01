from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from ..cases.models import FrozenModel, SafeId


class Claim(FrozenModel):
    claim_id: SafeId
    sentence: str
    start: int = Field(ge=0, strict=True)
    end: int = Field(ge=0, strict=True)
    action: str
    target: str | None
    actor: str | None
    negated: bool = Field(strict=True)
    time_expression: str | None
    resolved_start: datetime | None
    resolved_end: datetime | None
    uncertainty: list[str]
    interpretation_notes: list[str]

    @field_validator("resolved_start", "resolved_end")
    @classmethod
    def aware_bounds(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Resolved claim bounds must be timezone-aware")
        return value

    @model_validator(mode="after")
    def ordered_bounds(self):
        if self.end <= self.start or (self.resolved_start and self.resolved_end and self.resolved_end < self.resolved_start):
            raise ValueError("Claim spans/time bounds are invalid")
        return self


class Assessment(FrozenModel):
    claim_id: SafeId
    status: Literal["supported", "contradicted", "unverified", "inconclusive"]
    cited_record_ids: list[str]
    justification: str
    alternative_explanations: list[str]
    limitations: list[str]


class VerificationResult(FrozenModel):
    assessments: list[Assessment] = Field(default_factory=list)
    claim_errors: dict[str, dict[str, str]] = Field(default_factory=dict)
