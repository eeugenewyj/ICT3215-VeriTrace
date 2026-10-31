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


def test_search_tool_description_tells_the_model_which_filters_exist(tmp_path):
    """Regression: qwen3:8b invented an 'action' filter and searched the witness's words."""
    from veritrace.agents.tools import tool_definitions
    search = next(d for d in tool_definitions("case01") if d["function"]["name"] == "search_records")
    text = search["function"]["description"]
    for needle in ("family", "target", "time_role", "start", "end", "no action filter"):
        assert needle in text.lower() or needle in text


def test_unknown_filter_error_lists_the_allowed_filters(tmp_path):
    from veritrace.errors import InputError
    case, tools = backend(tmp_path)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    with pytest.raises(InputError) as raised:
        tools.dispatch("search_records", {"case_id": "case01", "filters": {"action": "download_file"}}, claim_id="claim01")
    message = str(raised.value)
    assert "unknown argument 'filters.action'" in message
    assert "family, target, account, start, end, time_role" in message
    assert "pydantic.dev" not in message
    tools.index.connection.close()


def test_empty_filtered_search_hints_at_broadening_but_unfiltered_does_not(tmp_path):
    case, tools = backend(tmp_path)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    missed = tools.dispatch("search_records", {"case_id": "case01", "filters": {"target": "no-such-file"}}, claim_id="claim01")
    assert missed["total"] == 0 and "retry with fewer filters" in missed["hint"]
    found = tools.dispatch("search_records", {"case_id": "case01", "filters": {}}, claim_id="claim01")
    assert found["total"] == 1 and "hint" not in found
    tools.index.connection.close()


def test_claim_prompt_coverage_drops_empty_fields_but_keeps_real_notes(tmp_path):
    """Regression: the full coverage table plus one search overflowed the 4096-token budget."""
    from veritrace.agents.tools import compact_coverage
    case, tools = backend(tmp_path)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    rows = compact_coverage(tools.coverage)
    assert rows and all({"family", "status", "records"} <= set(r) for r in rows)
    assert all(None not in r.values() and [] not in r.values() for r in rows)
    assert len(json.dumps(rows)) < len(json.dumps([c.model_dump(mode="json") for c in tools.coverage]))
    tools.index.connection.close()


def test_search_results_omit_boilerplate_but_keep_specific_limitations(tmp_path):
    from veritrace.agents.tools import GENERIC_LIMITATIONS, compact_record
    record = make_record()
    plain = compact_record(record.model_copy(update={"limitations": [*GENERIC_LIMITATIONS]}))
    assert "limitations" not in plain and "locator_resolution" not in plain
    flagged = compact_record(record.model_copy(update={"limitations": [*GENERIC_LIMITATIONS, "Row identity is ambiguous"]}))
    assert flagged["limitations"] == ["Row identity is ambiguous"]


def test_get_record_view_for_the_model_is_trimmed_but_the_ledger_keeps_everything(tmp_path):
    """Regression: a full get_record result (~1,400 tokens) overflowed the 4096-token budget."""
    from types import SimpleNamespace
    from veritrace.agents.verify import execute_request
    case, tools = backend(tmp_path)
    tools.dispatch("extract_case", {"case_id": "case01"}, claim_id=None)
    record = make_record()
    noisy = {"id": 7, "source_short": "WEBHIST", "guid": "x" * 40, "etag": "", "opened": 0, "state_friendly": "Complete", "target_path": record.target, "native_row": {"a": "b" * 500}, "tab_url": "https://example.test/" + "p" * 300}
    tools.index.connection.execute("UPDATE records SET record_json=? WHERE record_id=?", (record.model_copy(update={"raw_fields": noisy}).model_dump_json(), record.record_id))
    turn = SimpleNamespace(tool_calls=[{"function": {"name": "get_record", "arguments": {"case_id": "case01", "record_id": record.record_id}}}])
    (message,) = execute_request(turn, tools, claim_id="claim01")
    view = json.loads(message["content"])
    assert view["record_id"] == record.record_id and view["target"] == "report.pdf"
    assert view["details"]["state_friendly"] == "Complete" and view["details"]["id"] == 7
    assert not {"source_short", "guid", "etag", "opened", "native_row", "target_path"} & set(view["details"])
    assert view["details"]["tab_url"].endswith("...") and len(view["details"]["tab_url"]) < 200
    assert len(message["content"]) < 600
    assert "native_row" in tools.ledger.entries[-1].result["raw_fields"]
    tools.index.connection.close()
