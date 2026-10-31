import json
import time
from typing import Any

from pydantic import Field, ValidationError

from ..cases.models import FrozenModel, SafeId
from ..errors import InputError, VeriTraceError, WorkflowError
from ..evidence.index import SearchFilters
from ..evidence.models import EvidenceRecord
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

# Regression: qwen3:8b was only told the tool is called "search records", so it invented an
# "action" filter, searched for the witness's words ("it", "the sample image") and put a clock
# time in time_role; every search returned nothing. The schema's descriptions are stripped by
# compact_schema, so the guidance lives here.
DESCRIPTIONS = {
    "extract_case": "Parse the registered case evidence into records. Already done before claims are assessed.",
    "search_records": "Search evidence records; filters are optional and combine with AND. family: for example edge_history. target: substring of the file name, path or URL (a distinctive word such as sample or .pdf, never a pronoun). account. start and end: ISO-8601 with timezone. time_role: an exact role such as download_started or visit_time, never a clock time. There is no action filter. Use limit 5. Times are UTC.",
    "get_record": "Fetch one full record by the record_id returned from a search.",
    "get_source_coverage": "List which evidence sources were parsed, unsupported or failed.",
}


def argument_error(name, exc):
    """Say what was wrong and what is allowed, so a small model can fix its own call."""
    parts = []
    for error in exc.errors():
        loc = ".".join(str(p) for p in error["loc"])
        if error["type"] == "extra_forbidden":
            allowed = SearchFilters.model_fields if loc.startswith("filters.") else ARGUMENTS[name].model_fields
            parts.append(f"unknown argument {loc!r} (allowed: {', '.join(allowed)})")
        else:
            parts.append(f"{loc}: {error['msg']}")
    return "Invalid tool arguments: " + "; ".join(parts)


def tool_definitions(case_id, names=None):
    definitions = []
    for name in names or ARGUMENTS:
        schema = compact_schema(ARGUMENTS[name].model_json_schema())
        schema["properties"]["case_id"]["enum"] = [case_id]
        definitions.append({"type": "function", "function": {"name": name, "description": DESCRIPTIONS[name], "parameters": schema}})
    return definitions


# Said about every browser record and already in the system prompt; repeating it per record wastes context.
GENERIC_LIMITATIONS = {"A browser record does not establish a human actor or that a PDF was read."}


def compact_record(record):
    # Regression: with num_ctx 4096 one 4-record search plus the full coverage table left no room
    # for a second search (context_limit). Fields the model cannot use are left out of its view;
    # the full record stays in the index and is returned by get_record.
    out = {"record_id": record.record_id, "family": record.family, "target": record.target,
           "times": [{"role": t.role, "utc": t.normalized_utc.isoformat() if t.normalized_utc else None, **({"uncertainty": t.uncertainty} if t.uncertainty else {})} for t in record.times]}
    notes = [n for n in record.limitations if n not in GENERIC_LIMITATIONS]
    if notes:
        out["limitations"] = notes
    if record.account:
        out["account"] = record.account
    return out


DETAIL_NOISE = {"source_short", "source_long", "parser", "profile", "source_item", "message", "data_type", "guid", "datetime", "timestamp_desc"}


def record_details(record):
    """The few raw parser fields worth reading: non-empty scalars, no duplicates of the target."""
    seen, out = {record.target}, {}
    for key, value in record.raw_fields.items():
        if key in DETAIL_NOISE or isinstance(value, bool) or not isinstance(value, (str, int, float)) or value in ("", 0) or str(value) in seen:
            continue
        out[key] = value[:160] + "..." if isinstance(value, str) and len(value) > 160 else value
        seen.add(str(value))
    return out


def model_view(name, result):
    """What the model reads. Regression: a full get_record result (~1,400 tokens of raw parser
    fields) overflowed the 4096-token budget. The ledger keeps the complete result for audit."""
    if name != "get_record" or "record_id" not in result:
        return result
    record = EvidenceRecord.model_validate(result)
    return {**compact_record(record), "original_path": record.original_path, "details": record_details(record)}


def compact_coverage(entries):
    """Coverage without null/empty fields, for the claim prompt; get_source_coverage returns it in full."""
    rows = []
    for c in entries:
        row = {"family": c.family, "status": c.status, "records": c.record_count}
        for key, value in (("item_id", c.item_id), ("reason", c.reason), ("error", c.error_code), ("companions", c.companion_handling)):
            if value:
                row[key] = value
        rows.append(row)
    return rows


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
                raise InputError(argument_error(name, exc)) from exc
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
                if not page.total and any(v is not None for v in validated.filters.model_dump().values()):
                    result["hint"] = "No records matched. Filters combine with AND; retry with fewer filters and limit 5 before concluding the source has nothing relevant."
            return result
        except VeriTraceError as exc:
            error = {"code": exc.code, "message": str(exc)}
            raise
        finally:
            self.ledger.append(ToolReceipt(sequence=len(self.ledger.entries) + 1, claim_id=claim_id, name=name, arguments=arguments, result=result, error=error, returned_record_ids=ids, duration_s=time.perf_counter() - started, cache_hit=cached))
