import copy
import json

import pytest

from veritrace.agents.context import deduplicate_record_messages


def tool(name, result):
    return {"role": "tool", "tool_name": name, "content": json.dumps(result)}


def test_repeated_search_projection_is_referenced_without_losing_pagination_or_full_details():
    record = {"record_id": "a", "target": "report.pdf", "times": [{"role": "activity", "utc": "time"}]}
    full = {**record, "details": {"AppId": "app", "Notes": "specific caveat"}}
    messages = [tool("search_records", {"records": [record], "total": 3, "next_cursor": "cursor"}), tool("get_record", full)]
    assert deduplicate_record_messages(messages) == 1
    result = json.loads(messages[0]["content"])
    assert result["total"] == 3 and result["next_cursor"] == "cursor"
    assert result["records"] == [{"record_id": "a", "details_in": "later get_record response"}]
    assert json.loads(messages[1]["content"]) == full
    assert deduplicate_record_messages(messages) == 0  # References are not rewritten repeatedly.


@pytest.mark.parametrize("original,later", [("first.pdf", "second.pdf"), (True, 1)])
def test_distinct_record_fields_are_never_dropped(original, later):
    messages = [tool("search_records", {"records": [{"record_id": "a", "target": original}], "total": 1}),
                tool("get_record", {"record_id": "a", "target": later, "details": {}})]
    before = copy.deepcopy(messages)
    assert deduplicate_record_messages(messages) == 0
    assert messages == before


def test_repeated_full_records_are_referenced_but_other_records_and_errors_remain():
    full = {"record_id": "a", "target": "report.pdf", "details": {"EntryNumber": "1"}}
    unrelated = tool("search_records", {"records": [{"record_id": "b", "target": "other.pdf"}], "total": 1})
    error = tool("get_record", {"error": {"code": "not_found"}})
    malformed = {"role": "tool", "tool_name": "get_record", "content": "not JSON"}
    messages = [tool("get_record", full), unrelated, error, malformed, tool("get_record", full)]
    assert deduplicate_record_messages(messages) == 1
    assert json.loads(messages[0]["content"])["record_id"] == "a"
    assert messages[1:4] == [unrelated, error, malformed]
    assert json.loads(messages[-1]["content"]) == full


def test_search_after_details_references_the_retained_earlier_record():
    record = {"record_id": "a", "target": "report.pdf", "application": "Notepad"}
    full = {**record, "details": {"PinStatus": "False"}}
    messages = [tool("get_record", full), tool("search_records", {"records": [record], "total": 1})]
    assert deduplicate_record_messages(messages) == 1
    assert json.loads(messages[0]["content"]) == full
    assert json.loads(messages[1]["content"])["records"] == [{"record_id": "a", "details_in": "earlier get_record response"}]
    assert deduplicate_record_messages(messages) == 0


def test_compaction_keeps_original_receipts_and_valid_citations(tmp_path):
    from tests.factories import make_claim, make_record
    from tests.fakes import ReplayClient, TestBudget
    from tests.test_tools import backend
    from tests.test_verification import call, finished, verdict
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}),
                           call("search_records", {"case_id": "case01", "filters": {}}),
                           call("get_record", {"case_id": "case01", "record_id": make_record().record_id}),
                           finished(), verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.claim_errors and result.assessments[0].status == "supported"
    assert tools.context_compactions == 1
    # The model sees a reference, while audit data keeps the complete search row.
    search = next(m for m in client.requests[-1]["messages"] if m.get("tool_name") == "search_records")
    assert "details_in" in json.loads(search["content"])["records"][0]
    receipt = next(r for r in tools.ledger.entries if r.name == "search_records")
    assert receipt.result["records"][0]["target"] == "report.pdf"
    assert make_record().record_id in tools.ledger.returned_ids("claim01")
    tools.index.connection.close()
