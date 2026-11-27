"""Source processing counts and provenance-bound diagnostic notes for reports."""
from collections import Counter
from pathlib import Path

from pydantic import Field, ValidationError, model_validator

from ..cases.models import FrozenModel, RegisteredCase, SafeId, Sha256
from ..cases.registry import check_ancestors, safe_acquired_path, sha256_file
from ..errors import InputError, IntegrityError
from ..settings import FAMILIES


LABELS = {
    "empty_input": "Empty exported input",
    "invalid_prefetch_header": "Unrecognized Prefetch header",
    "parser_failure": "Parser could not process this input",
    "source_integrity_unconfirmed": "Input integrity could not be confirmed",
    "stale_directory_name": "Historical directory-name remnant",
    "empty_short_name_alias_export": "Empty short-name alias export",
    "deleted_file_clusters_reused": "Deleted file: clusters reused",
    "deleted_file_invalid_remaining_content": "Deleted file: invalid remaining content",
}


class DiagnosticNote(FrozenModel):
    item_id: SafeId
    source_sha256: Sha256
    category: SafeId
    explanation: str = Field(min_length=1, max_length=8192)
    limitations: list[str] = Field(default_factory=list)
    related_item_ids: list[SafeId] = Field(default_factory=list)


class CoverageDiagnostics(FrozenModel):
    schema_version: int = Field(default=1, ge=1, le=1)
    case_id: SafeId
    method: str = Field(min_length=1, max_length=4096)
    supporting_report: str
    supporting_report_sha256: Sha256
    notes: list[DiagnosticNote]

    @model_validator(mode="after")
    def unique_notes(self):
        if len({n.item_id for n in self.notes}) != len(self.notes):
            raise ValueError("Duplicate source diagnostic note")
        return self


def read_registration(output_dir):
    path = output_dir / "registration.json"
    if not path.exists():
        return None
    check_ancestors(path)
    try:
        return RegisteredCase.model_validate_json(path.read_bytes())
    except (OSError, ValidationError) as exc:
        raise InputError(f"Cannot read report source registration: {exc}") from exc


def validate_diagnostics(diagnostics, result, case):
    if case is None or case.manifest.case_id != result.case_id or diagnostics.case_id != result.case_id:
        raise InputError("Source diagnostics must match the registered report case")
    items = {i.item_id: i for i in case.manifest.items}
    failed = {c.item_id for c in result.coverage if c.status == "failed"}
    for note in diagnostics.notes:
        item = items.get(note.item_id)
        if item is None or note.item_id not in failed:
            raise InputError("Diagnostics may explain only registered, unparsed inputs")
        if not item.calculated_sha256 or note.source_sha256.lower() != item.calculated_sha256.lower():
            raise IntegrityError(f"Diagnostic source hash mismatch: {note.item_id}")
        for item_id in {note.item_id, *note.related_item_ids}:
            related = items.get(item_id)
            if related is None:
                raise InputError("Diagnostic related item is not registered in this case")
            path = safe_acquired_path(case.working_root / "evidence", related.acquired_path)
            if sha256_file(path) != related.calculated_sha256:
                raise IntegrityError(f"Diagnostic working-source hash mismatch: {item_id}")


def load_diagnostics(path, result, case):
    path = Path(path).absolute()
    check_ancestors(path)
    try:
        diagnostics = CoverageDiagnostics.model_validate_json(path.read_bytes())
        supporting = safe_acquired_path(path.parent, diagnostics.supporting_report)
        if not supporting.is_file() or sha256_file(supporting) != diagnostics.supporting_report_sha256.lower():
            raise IntegrityError("Supporting diagnostic report hash mismatch")
        validate_diagnostics(diagnostics, result, case)
    except (OSError, ValidationError) as exc:
        raise InputError(f"Cannot load source diagnostics: {exc}") from exc
    return diagnostics, supporting


def coverage_summary(coverage, notes=()):
    """Count files separately from records and family-level availability markers."""
    notes = {n.item_id for n in notes}
    groups = {}
    for entry in coverage:
        family = entry.family if entry.family in FAMILIES else "other"
        row = groups.setdefault(family, {"family": family, "items": 0, "parsed": 0, "empty": 0, "unparsed": 0, "unsupported": 0, "records": 0, "availability": set(), "with_diagnostic_notes": 0})
        row["records"] += entry.record_count
        if entry.item_id is None:
            row["availability"].add(entry.status)
            continue
        row["items"] += 1
        key = {"parsed": "parsed", "parsed-with-no-records": "empty", "failed": "unparsed", "unsupported": "unsupported"}.get(entry.status)
        if key:
            row[key] += 1
        else:
            row["availability"].add(entry.status)
        row["with_diagnostic_notes"] += entry.status == "failed" and entry.item_id in notes
    rows = []
    for family in (*FAMILIES, "other"):
        if family in groups:
            row = groups[family]
            row["availability"] = sorted(row["availability"])
            rows.append(row)
    return rows


def observed_failure(entry, item, case):
    """Describe bytes actually supplied; never guess deleted status from a name."""
    note = {"category": "parser_failure", "explanation": entry.reason or "The parser did not return usable records for this input.", "limitations": [], "basis": "Recorded parser result"}
    if item is None or case is None:
        return note
    try:
        path = safe_acquired_path(case.working_root / "evidence", item.acquired_path)
        if sha256_file(path) != item.calculated_sha256:
            raise IntegrityError("Working source differs from its registered hash")
        size = path.stat().st_size
        note["bytes"] = size
        if size == 0:
            note.update(category="empty_input", explanation="The supplied export contains zero bytes, so there is no file content for the parser to decode.", basis="Working-source size and registered SHA-256 checked", limitations=["An empty export does not establish why content is unavailable or whether the associated program executed."])
        elif item.family == "prefetch":
            with path.open("rb") as stream:
                header = stream.read(8)
            if not (header[:3] == b"MAM" or header[4:8] == b"SCCA"):
                note.update(category="invalid_prefetch_header", explanation=f"The supplied bytes have neither the supported raw Prefetch signature nor a MAM-compressed header. First bytes: {header.hex()}.", basis="Working-source header and registered SHA-256 checked", limitations=["A header check does not identify the cause of invalid content; image metadata or further examination is needed."])
    except (OSError, InputError, IntegrityError) as exc:
        note.update(category="source_integrity_unconfirmed", explanation=str(exc), basis="Source inspection failed", limitations=["Byte-based explanations are withheld because this working source could not be verified."])
    return note


def coverage_report(result, output_dir, diagnostics=None):
    case = read_registration(output_dir)
    if case is not None and case.manifest.case_id != result.case_id:
        raise InputError("Report registration belongs to a different case")
    if diagnostics is not None:
        validate_diagnostics(diagnostics, result, case)
    supplied = {n.item_id: n for n in diagnostics.notes} if diagnostics else {}
    items = {i.item_id: i for i in case.manifest.items} if case else {}
    failures = []
    for entry in result.coverage:
        if entry.status != "failed":
            continue
        item = items.get(entry.item_id)
        note = observed_failure(entry, item, case)
        if entry.item_id in supplied:
            reviewed = supplied[entry.item_id]
            note.update(category=reviewed.category, explanation=reviewed.explanation, limitations=reviewed.limitations, basis="Supplied diagnostic addendum; source identities checked", related_item_ids=reviewed.related_item_ids)
        failures.append({"item_id": entry.item_id, "family": entry.family, "path": item.original_path or item.acquired_path if item else None, "parser_status": entry.status, "parser_reason": entry.reason, "parser_error_code": entry.error_code, **note, "label": LABELS.get(note["category"], note["category"].replace("_", " "))})
    return {"families": coverage_summary(result.coverage, supplied.values()), "unparsed_inputs": failures, "reason_counts": [{"category": category, "label": LABELS.get(category, category.replace("_", " ")), "count": count} for category, count in sorted(Counter(r["category"] for r in failures).items())], "completed_claims": len({a.claim_id for a in result.assessments} & {c.claim_id for c in result.claims}), "claim_count": len(result.claims), "item_paths": {i.item_id: i.original_path or i.acquired_path for i in items.values()}, "diagnostics": diagnostics.model_dump(mode="json") if diagnostics else None, "scope": "Processing coverage and diagnostic notes; parser outcomes and claim assessments are unchanged. Checked hashes bind source identity, not diagnostic correctness."}
