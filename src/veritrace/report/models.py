from typing import Any, Literal

from pydantic import Field

from ..cases.models import FrozenModel, SafeId, Sha256
from ..agents.models import Claim, Assessment
from ..agents.tools import ToolReceipt
from ..evidence.models import EvidenceRecord
from ..parsers.base import CoverageEntry


class RunResult(FrozenModel):
    run_id: SafeId
    case_id: SafeId
    testimony: str
    testimony_sha256: Sha256
    status: Literal["complete", "partial", "error"]
    claims: list[Claim] = Field(default_factory=list)
    assessments: list[Assessment] = Field(default_factory=list)
    claim_errors: dict[str, dict[str, str]] = Field(default_factory=dict)
    errors: list[dict[str, str]] = Field(default_factory=list)
    coverage: list[CoverageEntry] = Field(default_factory=list)
    records: list[EvidenceRecord] = Field(default_factory=list)
    tool_receipts: list[ToolReceipt] = Field(default_factory=list)
    runtime_metadata: dict[str, Any] = Field(default_factory=dict)
    output_paths: dict[str, str] = Field(default_factory=dict)
