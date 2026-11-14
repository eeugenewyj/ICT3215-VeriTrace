import hashlib
import json

from ..cases.integrity import verify_originals
from ..errors import IntegrityError, VeriTraceError, ParserError
from ..settings import FAMILIES
from .base import CoverageEntry, ExtractionResult


def extraction_key(case, adapters):
    payload = {"case": case.manifest.case_id, "sources": case.source_hashes, "adapters": {f: a.identity for f, a in sorted(adapters.items())}, "normalization": "1"}
    return hashlib.sha256(json.dumps(payload, sort_keys=True, ensure_ascii=False, default=str).encode()).hexdigest()


def extract_case(case, adapters, index):
    verify_originals(case)
    key = extraction_key(case, adapters)
    cache = case.working_root / f"extraction-{key}.json"
    if cache.exists():
        result = ExtractionResult.model_validate_json(cache.read_bytes())
        index.add(result.records)
        return result.coverage
    records, coverage = [], []
    for family in (*FAMILIES, "unknown"):
        items = [i for i in case.manifest.items if i.family == family]
        adapter = adapters.get(family)
        if adapter is None:
            coverage.extend(CoverageEntry(item_id=i.item_id, family=family, status="unsupported", reason="No enabled validated adapter") for i in items)
            if not items and family != "unknown":
                coverage.append(CoverageEntry(family=family, status="unsupported", reason="Family outside enabled coverage"))
            continue
        if not items:
            coverage.append(CoverageEntry(family=family, status="unavailable-in-input", reason="No source supplied; this is not proof of absence on the victim"))
            continue
        try:
            result = adapter.extract(case, items)
            lookup = {i.item_id: i for i in items}
            for record in result.records:
                item = lookup.get(record.item_id)
                if record.case_id != case.manifest.case_id or item is None or record.source_sha256 != item.calculated_sha256 or record.family != family:
                    raise ParserError("Adapter produced inconsistent case/source provenance")
            records.extend(result.records)
            coverage.extend(result.coverage)
            processed = {c.item_id for c in result.coverage}
            coverage.extend(CoverageEntry(item_id=i.item_id, family=family, status="failed", error_code="missing_coverage", reason="Adapter did not report this supplied item") for i in items if i.item_id not in processed)
        except IntegrityError:
            raise
        except (VeriTraceError, ValueError, OSError) as exc:
            coverage.extend(CoverageEntry(item_id=i.item_id, family=family, status="failed", reason=str(exc), error_code=getattr(exc, "code", "parser_schema")) for i in items)
    # Inventory unknown family names as explicitly unsupported too.
    coverage.extend(CoverageEntry(item_id=i.item_id, family=i.family, status="unsupported", reason="Unknown source family") for i in case.manifest.items if i.family not in (*FAMILIES, "unknown"))
    verify_originals(case)
    result = ExtractionResult(records=records, coverage=coverage)
    index.add(records)
    cache.write_text(result.model_dump_json(indent=2), encoding="utf-8")
    return coverage
