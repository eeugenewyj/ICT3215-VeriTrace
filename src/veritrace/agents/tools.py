import json
import time
from typing import Any

from pydantic import Field, ValidationError

from ..cases.models import FrozenModel, SafeId
from ..errors import InputError, VeriTraceError, WorkflowError
from ..evidence.index import SearchFilters
from ..parsers.coverage import extract_case, extraction_key
from .claims import compact_schema


class ToolReceipt(FrozenModel):
    sequence: int
    claim_id: str | None
    name: str
    arguments: Any
    result: Any = None
    error: dict[str, str] | None = None
    returned_record_ids: list[str] = Field(default_factory=list)
    duration_s: float
    cache_hit: bool = False


class ToolLedger:
    def __init__(self, path):
        self.path, self.entries = path, []

    def append(self, receipt):
        self.entries.append(receipt)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self.path.open("a", encoding="utf-8") as stream:
            stream.write(receipt.model_dump_json() + "\n")

    def returned_ids(self, claim_id):
        return {record_id for r in self.entries if r.claim_id == claim_id and r.error is None for record_id in r.returned_record_ids}


class CaseArgs(FrozenModel):
    case_id: SafeId


class SearchArgs(CaseArgs):
    filters: SearchFilters
    cursor: str | None = None
    limit: int = Field(default=25, ge=1, le=25, strict=True)


class RecordArgs(CaseArgs):
    record_id: str = Field(pattern=r"^[0-9a-f]{64}$")


ARGUMENTS = {"extract_case": CaseArgs, "search_records": SearchArgs, "get_record": RecordArgs, "get_source_coverage": CaseArgs}


def tool_definitions(case_id, names=None):
    definitions = []
    for name in names or ARGUMENTS:
        schema = compact_schema(ARGUMENTS[name].model_json_schema())
        schema["properties"]["case_id"]["enum"] = [case_id]
        definitions.append({"type": "function", "function": {"name": name, "description": name.replace("_", " "), "parameters": schema}})
    return definitions


def compact_record(record):
    return {"record_id": record.record_id, "family": record.family, "target": record.target,
            "account": record.account, "original_path": record.original_path,
            "locator_resolution": record.locator.resolution,
            "times": [{"role": t.role, "utc": t.normalized_utc.isoformat() if t.normalized_utc else None, "uncertainty": t.uncertainty} for t in record.times],
            "limitations": record.limitations}


class ToolBackend:
    def __init__(self, case, index, adapters, ledger):
        self.case, self.index, self.adapters, self.ledger = case, index, adapters, ledger
        self.coverage, self.extracted = [], False

    def dispatch(self, name, arguments, *, claim_id):
        started, result, error, ids, cached = time.perf_counter(), None, None, [], False
        try:
            if name not in ARGUMENTS:
                raise InputError("Unknown tool")
            try:
                validated = ARGUMENTS[name].model_validate(arguments)
            except ValidationError as exc:
                raise InputError(f"Invalid tool arguments: {exc}") from exc
            if validated.case_id != self.case.manifest.case_id:
                raise InputError("Tool case ID does not match registered case")
            if name != "extract_case" and not self.extracted:
                raise WorkflowError("Extraction must run before evidence queries")
            if name == "extract_case":
                cached = (self.case.working_root / f"extraction-{extraction_key(self.case, self.adapters)}.json").exists()
                self.coverage = extract_case(self.case, self.adapters, self.index)
                self.extracted = True
                result = {"case_id": validated.case_id, "coverage": [c.model_dump(mode="json") for c in self.coverage], "cache_hit": cached}
            elif name == "get_source_coverage":
                result = {"coverage": [c.model_dump(mode="json") for c in self.coverage]}
            elif name == "get_record":
                record = self.index.get(validated.case_id, validated.record_id)
                ids = [record.record_id]
                result = record.model_dump(mode="json")
            else:
                page = self.index.search(validated.case_id, validated.filters, validated.cursor, validated.limit)
                ids = [r.record_id for r in page.records]
                result = {"records": [compact_record(r) for r in page.records], "total": page.total, "next_cursor": page.next_cursor}
            return result
        except VeriTraceError as exc:
            error = {"code": exc.code, "message": str(exc)}
            raise
        finally:
            self.ledger.append(ToolReceipt(sequence=len(self.ledger.entries) + 1, claim_id=claim_id, name=name, arguments=arguments, result=result, error=error, returned_record_ids=ids, duration_s=time.perf_counter() - started, cache_hit=cached))
