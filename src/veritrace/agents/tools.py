import base64
import hashlib
import json
import time
from datetime import timezone
from typing import Any, Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from pydantic import Field, ValidationError

from ..cases.models import FrozenModel, SafeId
from ..errors import InputError, VeriTraceError, WorkflowError
from ..evidence.index import SearchFilters
from ..evidence.models import EvidenceRecord
from ..parsers.base import CoverageEntry
from ..parsers.coverage import extract_case, extraction_key
from ..settings import FAMILIES as SOURCE_FAMILIES
from .claims import compact_schema
from .hints import coverage_view


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


class CoverageArgs(CaseArgs):
    family: str | None = Field(default=None, min_length=1, max_length=64)
    status: Literal["parsed", "parsed-with-no-records", "failed", "unavailable-in-input", "unsupported"] | None = None
    item_id: SafeId | None = None
    details: bool = Field(default=False, strict=True)
    cursor: str | None = Field(default=None, min_length=1, max_length=2048)
    limit: int = Field(default=5, ge=1, le=25, strict=True)


ARGUMENTS = {"extract_case": CaseArgs, "search_records": SearchArgs, "get_record": RecordArgs, "get_source_coverage": CoverageArgs}

# Regression: qwen3:8b was only told the tool is called "search records", so it invented an
# "action" filter, searched for the witness's words ("it", "the sample image") and put a clock
# time in time_role; every search returned nothing. The schema's descriptions are stripped by
# compact_schema, so the guidance lives here.
DESCRIPTIONS = {
    "extract_case": "Parse the registered case evidence into records. Already done before claims are assessed.",
    "search_records": "Search evidence records; filters are optional and combine with AND. family: edge_history (downloads, page visits), lnk (file-target context), recyclebin (files deleted), jumplist (application-associated destinations/tasks), prefetch or userassist (program activity). target: substring of the file name, path or URL (a distinctive word such as sample or .pdf, never a pronoun). account. start and end: ISO-8601 with timezone. time_role: an exact role such as download_started, visit_time, destlist_entry_modified or recycle_bin_deletion, never a clock time. There is no action filter. Use limit 5. Record times are shown in the witness's local time.",
    "get_record": "Fetch additional selected parser details by the record_id returned from a search.",
    "get_source_coverage": "Coverage summary by family/status/count, not activity evidence. For source details set details=true; filter by family, status or item_id, use limit 5 and follow next_cursor with the same filters. family=other covers unknown/undeclared families. Long diagnostics are excerpted; complete details stay in coverage.json.",
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
JUMPLIST_GENERIC_LIMITATIONS = {
    "Parser item identifies the source file and export row; compare acquired samples before enabling this mapping.",
    "Artefact activity does not identify a human actor.",
    "Target-file timestamps are distinct from interaction times; recent-item traces alone do not prove a PDF was read.",
    "Parser SourceCreated/SourceModified/SourceAccessed are working-copy metadata; excluded from victim evidence timestamps.",
}


def compact_record(record, source_timezone=None, *, detailed=False):
    # Regression: with num_ctx 4096 one 4-record search plus the full coverage table left no room
    # for a second search (context_limit). Fields the model cannot use are left out of its view;
    # the full record stays in the index and is returned by get_record.
    times, omitted = record.times, []
    zone, zone_error = None, False
    if record.family == "jumplist":
        # Target-file and UUID dates are not document-interaction clocks. Keep
        # them in the full record, explicitly naming omitted roles in this view.
        times = [t for t in record.times if t.role == "destlist_entry_modified"]
        omitted = sorted({t.role for t in record.times if t.role != "destlist_entry_modified"})
    if source_timezone:
        try:
            zone = ZoneInfo(source_timezone)
        except (ZoneInfoNotFoundError, ValueError):
            zone_error = True
    # Regression (acquired LNK/Recycle Bin run): the model was shown UTC and the witness spoke in local time,
    # so it reasoned "21:01 UTC" against "3 pm" and got the arithmetic wrong. Clock conversion is code's job:
    # every family shows the witness's local time. Jump Lists keep UTC beside it (existing, tested view).
    def shown(t):
        if not t.normalized_utc:
            return {"role": t.role, "utc": None}
        stamp = t.normalized_utc.astimezone(timezone.utc)
        if zone and record.family != "jumplist":
            return {"role": t.role, "local": stamp.astimezone(zone).isoformat(timespec="seconds")}
        return {"role": t.role, "utc": stamp.strftime("%Y-%m-%dT%H:%M:%SZ"), **({"local": stamp.astimezone(zone).isoformat(timespec="seconds")} if zone else {})}
    out = {"record_id": record.record_id, "family": record.family, "target": record.target,
           "times": [{**shown(t), **({"uncertainty": t.uncertainty} if t.uncertainty else {})} for t in times]}
    if record.family == "jumplist":
        # The same target can occur in Quick Access and Notepad lists. Keep its
        # application association visible before the model chooses a record.
        if record.application:
            out["application"] = record.application
        source = (record.original_path or "").casefold()
        if source.endswith(".automaticdestinations-ms"):
            out["jumplist_type"] = "automatic"
        elif source.endswith(".customdestinations-ms"):
            out["jumplist_type"] = "custom"
        if omitted and detailed:
            out["omitted_noninteraction_time_roles"] = omitted
        if zone:
            out["source_timezone"] = source_timezone
    if zone_error:
        out["local_time_note"] = "Source timezone unavailable; local time was not inferred."
    generic = GENERIC_LIMITATIONS | (JUMPLIST_GENERIC_LIMITATIONS if record.family == "jumplist" else set())
    notes = [n for n in record.limitations if n not in generic]
    if notes:
        out["limitations"] = notes
    if record.account:
        out["account"] = record.account
    return out


DETAIL_NOISE = {"source_short", "source_long", "parser", "profile", "source_item", "message", "data_type", "guid", "datetime", "timestamp_desc"}


# Regression: a PECmd 2026.10 Prefetch row (~29 columns, incl. long Directories/FilesLoaded
# lists and all 8 run times again) made get_record exceed the 4096-token budget for every claim.
FAMILY_DETAIL_NOISE = {
    "prefetch": {"Note", "SourceFilename", "SourceCreated", "SourceModified", "SourceAccessed", "Hash", "Size",
                 "Directories", "FilesLoaded", "PathValidated", "ParsingError",
                 "Volume0Name", "Volume0Serial", "Volume0Created", "Volume1Name", "Volume1Serial", "Volume1Created"},
    # Keep application/entry identity, interaction count, pin status, arguments
    # and notes. Times are already represented with their semantic roles above.
    "jumplist": {"SourceFile", "SourceCreated", "SourceModified", "SourceAccessed", "source_file_timestamps_scope",
                 "AppIdDescription", "CreationTime", "LastModified", "TargetCreated", "TargetModified", "TargetAccessed",
                 "FileBirthDroid", "FileDroid", "VolumeBirthDroid", "VolumeDroid", "Hostname", "MacAddress",
                 "MachineID", "MachineMACAddress", "TrackerCreatedOn", "TargetMFTEntryNumber", "TargetMFTSequenceNumber",
                 "HasSps", "DestListVersion", "LastUsedEntryNumber", "ExtraBlocksPresent", "HeaderFlags"},
}
JUMPLIST_DETAIL_FIELDS = {"AppId", "EntryNumber", "EntryName", "InteractionCount", "PinStatus", "MRU",
                         "Arguments", "WorkingDirectory", "Notes", "FileSize"}


def record_details(record):
    """The few raw parser fields worth reading: non-empty scalars, no duplicates of the target."""
    seen, out = {record.target}, {}
    noise = DETAIL_NOISE | FAMILY_DETAIL_NOISE.get(record.family, set())
    as_times = {t.role for t in record.times}
    for key, value in record.raw_fields.items():
        if record.family == "jumplist" and key not in JUMPLIST_DETAIL_FIELDS:
            continue
        if key in noise or f"{record.family}_{key}" in as_times or isinstance(value, bool) or not isinstance(value, (str, int, float)) or value in ("", 0) or str(value) in seen:
            continue
        out[key] = value[:160] + "..." if isinstance(value, str) and len(value) > 160 else value
        seen.add(str(value))
    return out


def model_view(name, result, *, source_timezone=None):
    """What the model reads. Regression: a full get_record result (~1,400 tokens of raw parser
    fields) overflowed the 4096-token budget. The ledger keeps the complete result for audit."""
    if name in ("extract_case", "get_source_coverage") and "coverage" in result:
        entries = [CoverageEntry.model_validate(c) for c in result["coverage"]]
        rest = {k: v for k, v in result.items() if k != "coverage"}
        if result.get("details"):
            rows = compact_coverage(entries)
            for row in rows:
                excerpts = []
                for key, size in (("family", 64), ("reason", 240), ("error", 80)):
                    if isinstance(row.get(key), str) and len(row[key]) > size:
                        row[key] = row[key][:size] + "..."
                        excerpts.append(key)
                notes = row.get("companions", [])
                if notes:
                    row["companions"] = [note[:160] + "..." if len(note) > 160 else note for note in notes[:2]]
                    if len(notes) > 2 or any(len(note) > 160 for note in notes):
                        excerpts.append("companions")
                if excerpts:
                    row["excerpted_fields"] = excerpts
                    row["full_details"] = "coverage.json"
            return {**rest, "coverage": rows}
        return {**rest, **coverage_view(entries)}
    if name != "get_record" or "record_id" not in result:
        return result
    record = EvidenceRecord.model_validate(result)
    return {**compact_record(record, source_timezone, detailed=True), "original_path": record.original_path, "details": record_details(record)}


def compact_coverage(entries):
    """Per-item fields without empty values; model_view bounds diagnostic excerpts."""
    rows = []
    for c in entries:
        row = {"family": c.family, "status": c.status, "records": c.record_count}
        for key, value in (("item_id", c.item_id), ("reason", c.reason), ("error", c.error_code), ("companions", c.companion_handling)):
            if value:
                row[key] = value
        rows.append(row)
    return rows


def coverage_result(case_id, coverage, args):
    """Filter and page diagnostics without losing the complete extraction ledger."""
    entries = [c for c in coverage if
               (args.family is None or (c.family not in SOURCE_FAMILIES if args.family == "other" else c.family == args.family)) and
               (args.status is None or c.status == args.status) and
               (args.item_id is None or c.item_id == args.item_id)]
    if not args.details:
        if args.cursor is not None:
            raise InputError("Coverage continuation requires details=true and the same filters")
        return {**coverage_view(entries), "total": len(entries), "details": False}
    filters = {"family": args.family, "status": args.status, "item_id": args.item_id}
    fingerprint = hashlib.sha256(json.dumps({"filters": filters, "coverage": [c.model_dump(mode="json") for c in coverage]}, sort_keys=True).encode()).hexdigest()
    offset = 0
    if args.cursor is not None:
        try:
            state = json.loads(base64.b64decode(args.cursor, altchars=b"-_", validate=True))
            offset = state["offset"]
            if state["case_id"] != case_id or state["fingerprint"] != fingerprint or type(offset) is not int or not 0 <= offset < len(entries):
                raise ValueError("Mismatched coverage cursor")
        except (ValueError, KeyError, TypeError, UnicodeError) as exc:
            raise InputError("Invalid coverage cursor; keep the same case, coverage and filters") from exc
    page = entries[offset:offset + args.limit]
    next_cursor = None
    if offset + len(page) < len(entries):
        state = {"case_id": case_id, "fingerprint": fingerprint, "offset": offset + len(page)}
        next_cursor = base64.urlsafe_b64encode(json.dumps(state).encode()).decode()
    return {"coverage": [c.model_dump(mode="json") for c in page], "total": len(entries), "next_cursor": next_cursor, "details": True}


class ToolBackend:
    def __init__(self, case, index, adapters, ledger):
        self.case, self.index, self.adapters, self.ledger = case, index, adapters, ledger
        self.coverage, self.extracted = [], False
        self.context_compactions = 0

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
                result = coverage_result(validated.case_id, self.coverage, validated)
            elif name == "get_record":
                record = self.index.get(validated.case_id, validated.record_id)
                ids = [record.record_id]
                result = record.model_dump(mode="json")
            else:
                page = self.index.search(validated.case_id, validated.filters, validated.cursor, validated.limit)
                ids = [r.record_id for r in page.records]
                result = {"records": [compact_record(r, self.case.manifest.source_timezone) for r in page.records], "total": page.total, "next_cursor": page.next_cursor}
                if not page.total and any(v is not None for v in validated.filters.model_dump().values()):
                    result["hint"] = "No records matched. Filters combine with AND; retry with fewer filters and limit 5 before concluding the source has nothing relevant."
            return result
        except VeriTraceError as exc:
            error = {"code": exc.code, "message": str(exc)}
            raise
        finally:
            self.ledger.append(ToolReceipt(sequence=len(self.ledger.entries) + 1, claim_id=claim_id, name=name, arguments=arguments, result=result, error=error, returned_record_ids=ids, duration_s=time.perf_counter() - started, cache_hit=cached))
