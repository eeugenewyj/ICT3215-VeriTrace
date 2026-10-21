from pathlib import Path
from typing import Annotated, Any
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator


SafeId = Annotated[str, Field(pattern=r"^[A-Za-z0-9][A-Za-z0-9_-]{0,63}$")]
Sha256 = Annotated[str, Field(pattern=r"^[0-9a-fA-F]{64}$")]


class FrozenModel(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)


class EvidenceItem(FrozenModel):
    item_id: SafeId
    acquired_path: str
    original_path: str | None = None
    family: str = "unknown"
    account: str | None = None
    sid: str | None = None
    supplied_sha256: Sha256 | None = None
    calculated_sha256: Sha256 | None = None
    companion_item_ids: list[str] = Field(default_factory=list)


class CaseManifest(FrozenModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    case_id: SafeId
    acquisition: dict[str, Any] | None = None
    windows: dict[str, Any] | None = None
    edge: dict[str, Any] | None = None
    security: dict[str, Any] | None = None
    testimony_reference_time: datetime | None = None
    source_timezone: str | None = None
    items: list[EvidenceItem]
    collection_omissions: list[str] = Field(default_factory=list)

    @model_validator(mode="after")
    def unique_items(self):
        ids = [i.item_id for i in self.items]
        paths = [i.acquired_path.replace("\\", "/").casefold() for i in self.items]
        if len(set(ids)) != len(ids) or len(set(paths)) != len(paths):
            raise ValueError("Duplicate item ID or acquired path")
        if any(c not in ids for i in self.items for c in i.companion_item_ids):
            raise ValueError("Companion ID is not declared")
        return self


class RegisteredCase(FrozenModel):
    manifest: CaseManifest
    testimony: str
    testimony_sha256: Sha256
    source_root: Path
    working_root: Path
    source_hashes: dict[str, str]
