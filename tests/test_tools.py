import hashlib
import json

import pytest

from tests.factories import write_case, make_record


def backend(tmp_path):
    from veritrace.cases.registry import register_case
    from veritrace.evidence.index import EvidenceIndex
    from veritrace.parsers.base import CoverageEntry, ExtractionResult
    from veritrace.agents.tools import ToolBackend, ToolLedger
    case = register_case(write_case(tmp_path), tmp_path / "run")
    class Adapter:
        identity = {"version": "unit-1"}
        def extract(self, case, items):
            raw = case.working_root / "raw/test.jsonl"
            raw.parent.mkdir(exist_ok=True)
            raw.write_text('{"id":7}\n', encoding="utf-8")
            record = make_record(raw_output_locator={"path": "raw/test.jsonl", "line": 1, "sha256": hashlib.sha256(raw.read_bytes()).hexdigest()})
            return ExtractionResult(records=[record], coverage=[CoverageEntry(item_id="history01", family="edge_history", status="parsed", record_count=1)])
    index = EvidenceIndex(case.working_root / "evidence.sqlite")
    return case, ToolBackend(case, index, {"edge_history": Adapter()}, ToolLedger(case.working_root / "tool_calls.jsonl"))


def test_actual_dispatch_and_cached_extraction(tmp_path):
    case, tools = backend(tmp_path)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    page = tools.dispatch("search_records", {"case_id": "case01", "filters": {}, "cursor": None}, claim_id="claim01")
    assert page["total"] == 1
    assert tools.ledger.entries[1].cache_hit is True
    assert make_record().record_id in tools.ledger.returned_ids("claim01")
    assert not tools.ledger.returned_ids("claim02")
    assert len((case.working_root / "tool_calls.jsonl").read_text().splitlines()) == 3
    tools.index.connection.close()


@pytest.mark.parametrize("name,args", [("shell", {"command": "whoami"}), ("extract_case", {"case_id": "other"}), ("extract_case", {"case_id": "case01", "path": "C:/"}), ("search_records", {"case_id": "case01", "filters": {}})])
def test_invalid_requests_are_recorded_without_execution(tmp_path, name, args):
    from veritrace.errors import VeriTraceError
    case, tools = backend(tmp_path)
    with pytest.raises(VeriTraceError):
        tools.dispatch(name, args, claim_id="claim01")
    assert tools.ledger.entries[-1].error is not None
    assert not tools.extracted
    tools.index.connection.close()


def test_citation_requires_retrieval_resolved_source_and_raw_hash(tmp_path):
    from veritrace.agents.citations import validate_citations
    from veritrace.agents.models import Assessment
    from veritrace.errors import CitationError
    case, tools = backend(tmp_path)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    assessment = Assessment(claim_id="claim01", status="supported", cited_record_ids=[make_record().record_id], justification="Download record", alternative_explanations=[], limitations=["Account attribution only"])
    with pytest.raises(CitationError):
        validate_citations(case, assessment, tools.index, tools.ledger)
    tools.dispatch("get_record", {"case_id": "case01", "record_id": make_record().record_id}, claim_id="claim01")
    validate_citations(case, assessment, tools.index, tools.ledger)
    (case.working_root / "raw/test.jsonl").write_text("tampered")
    with pytest.raises(CitationError):
        validate_citations(case, assessment, tools.index, tools.ledger)
    tools.index.connection.close()
