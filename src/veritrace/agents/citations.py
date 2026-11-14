from pathlib import PureWindowsPath

from ..cases.registry import check_ancestors, sha256_file
from ..errors import CitationError, InputError


def validate_citations(case, assessment, index, ledger):
    if assessment.status in ("supported", "contradicted", "inconclusive") and not assessment.cited_record_ids:
        raise CitationError("This assessment needs positive relevant evidence; missing evidence alone is insufficient")
    if len(set(assessment.cited_record_ids)) != len(assessment.cited_record_ids):
        raise CitationError("Duplicate citations")
    returned = ledger.returned_ids(assessment.claim_id)
    items = {i.item_id: i for i in case.manifest.items}
    for record_id in assessment.cited_record_ids:
        if record_id not in returned:
            raise CitationError("Citation was never returned for this claim")
        try:
            record = index.get(case.manifest.case_id, record_id)
            item = items.get(record.item_id)
            if item is None or item.calculated_sha256 != record.source_sha256:
                raise CitationError("Citation does not match the registered source")
            if record.locator.resolution != "resolved" or not record.locator.identifiers:
                raise CitationError("Citation lacks a resolved original-source locator")
            value = record.raw_output_locator.get("path", "")
            relative = PureWindowsPath(value)
            if not value or relative.is_absolute() or relative.drive or ".." in relative.parts or any(":" in p for p in relative.parts):
                raise CitationError("Invalid raw-output locator")
            path = case.working_root / value
            check_ancestors(path)
            if not path.resolve().is_relative_to(case.working_root) or not path.is_file():
                raise CitationError("Raw parser output is missing or outside the run")
            if sha256_file(path) != record.raw_output_locator.get("sha256"):
                raise CitationError("Raw parser output hash mismatch")
            line = record.raw_output_locator.get("line")
            if not isinstance(line, int) or isinstance(line, bool) or line < 1 or line > sum(1 for _ in path.open(encoding="utf-8")):
                raise CitationError("Raw-output line cannot be resolved")
        except (InputError, OSError, ValueError) as exc:
            raise CitationError(f"Citation cannot be resolved: {exc}") from exc
