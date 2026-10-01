import hashlib
import json
from datetime import datetime
from typing import Any, Literal

from pydantic import Field, field_validator

from ..cases.models import FrozenModel, SafeId, Sha256


class SourceLocator(FrozenModel):
    kind: str
    identifiers: dict[str, Any]
    resolution: Literal["resolved", "ambiguous", "unresolved"] = "resolved"


class EvidenceTime(FrozenModel):
    role: str
    raw_value: Any
    raw_encoding: str
    raw_precision: str
    normalized_utc: datetime | None = None
    normalization_basis: str | None = None
    uncertainty: str | None = None

    @field_validator("normalized_utc")
    @classmethod
    def aware_time(cls, value):
        if value is not None and value.utcoffset() is None:
            raise ValueError("Normalized evidence time must have timezone information")
        return value


class EvidenceRecord(FrozenModel):
    record_id: Sha256
    case_id: SafeId
    family: str
    item_id: SafeId
    source_sha256: Sha256
    original_path: str | None
    locator: SourceLocator
    times: list[EvidenceTime]
    account: str | None = None
    sid: str | None = None
    application: str | None = None
    target: str | None = None
    parser: dict[str, Any]
    raw_fields: dict[str, Any]
    raw_output_locator: dict[str, Any]
    limitations: list[str] = Field(default_factory=list)


def stable_record_id(case_id, family, source_sha256, locator):
    identity = {"case_id": case_id, "family": family, "source_sha256": source_sha256, "locator": locator.model_dump(mode="json")}
    return hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode()).hexdigest()
