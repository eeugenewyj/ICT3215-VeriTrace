import json

import pytest

from tests.factories import make_claim, make_record
from tests.fakes import ReplayClient, TestBudget
from tests.test_tools import backend


def call(name, arguments):
    from veritrace.runtime.client import ModelTurn
    return ModelTurn(tool_calls=[{"function": {"name": name, "arguments": arguments}}])


def verdict(status="supported", cites=None):
    from veritrace.runtime.client import ModelTurn
    return ModelTurn(content=json.dumps({"claim_id": "claim01", "status": status, "cited_record_ids": [make_record().record_id] if cites is None else cites, "justification": "Available positive browser record", "alternative_explanations": ["Account activity does not identify the person"], "limitations": ["A download does not establish document reading"]}))


def test_extract_refusal_is_workflow_error(tmp_path):
    from veritrace.agents.verify import verify_claims
    from veritrace.errors import WorkflowError
    case, tools = backend(tmp_path)
    client = ReplayClient.from_contents(["No tools needed", "Still no tools"])
    with pytest.raises(WorkflowError):
        verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not tools.ledger.entries
    tools.index.connection.close()


def test_genuine_model_requested_extraction_and_retrieval(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {"target": "report.pdf"}, "cursor": None}), verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert result.assessments[0].status == "supported"
    assert not result.claim_errors
    assert [r.name for r in tools.ledger.entries] == ["extract_case", "search_records"]
    assert client.requests[-1]["messages"][-1]["role"] == "tool"
    tools.index.connection.close()


@pytest.mark.parametrize("status,cites", [("supported", ["f" * 64]), ("contradicted", []), ("inconclusive", [])])
def test_invalid_citations_become_operational_errors(tmp_path, status, cites):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), *[verdict(status, cites)] * 3])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.assessments
    assert "claim01" in result.claim_errors
    tools.index.connection.close()


def test_invalid_tool_calls_count_toward_twelve_call_limit(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), *[call("shell", {"command": "anything"})] * 13])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert len(tools.ledger.entries) == 13  # one extraction + twelve attempted tools
    assert result.claim_errors["claim01"]["code"] == "workflow_error"
    tools.index.connection.close()
