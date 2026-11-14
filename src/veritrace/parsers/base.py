from pathlib import Path
from typing import Any, Literal, Protocol

from pydantic import Field

from ..cases.models import FrozenModel
from ..evidence.models import EvidenceRecord


class CoverageEntry(FrozenModel):
    item_id: str | None = None
    family: str
    status: Literal["parsed", "parsed-with-no-records", "failed", "unavailable-in-input", "unsupported"]
    record_count: int = Field(default=0, ge=0)
    companion_handling: list[str] = Field(default_factory=list)
    reason: str | None = None
    error_code: str | None = None


class ExtractionResult(FrozenModel):
    records: list[EvidenceRecord] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)


class ParserRun(FrozenModel):
    command: list[str]
    version: str | None = None
    config_sha256: str | None = None
    exit_code: int | None = None
    duration_s: float
    stdout_path: Path
    stderr_path: Path
    output_hashes: dict[str, str]
    error_code: str | None = None


class ParserAdapter(Protocol):
    identity: dict[str, Any]
    def extract(self, case, items) -> ExtractionResult: ...
