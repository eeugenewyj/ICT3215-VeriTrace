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


def finished():
    from veritrace.runtime.client import ModelTurn
    return ModelTurn(content="Evidence retrieved; finalize this claim.")


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
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {"target": "report.pdf"}, "cursor": None}), finished(), verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert result.assessments[0].status == "supported"
    assert not result.claim_errors
    assert [r.name for r in tools.ledger.entries] == ["extract_case", "search_records"]
    assert any(m["role"] == "tool" for m in client.requests[-1]["messages"])
    assert client.requests[-1]["schema"] and client.requests[-1]["tools"] is None
    tools.index.connection.close()


@pytest.mark.parametrize("status,cites", [("supported", ["f" * 64]), ("contradicted", []), ("inconclusive", [])])
def test_invalid_citations_become_operational_errors(tmp_path, status, cites):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), *[t for _ in range(3) for t in (finished(), verdict(status, cites))]])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.assessments
    assert "claim01" in result.claim_errors
    tools.index.connection.close()


def test_unverified_without_an_evidence_search_is_an_operational_error(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), *[verdict("unverified", [])] * 3])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.assessments
    assert result.claim_errors["claim01"]["code"] == "workflow_error"
    tools.index.connection.close()


def test_invalid_tool_calls_count_toward_twelve_call_limit(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), *[call("shell", {"command": "anything"})] * 13])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert len(tools.ledger.entries) == 13  # one extraction + twelve attempted tools
    assert result.claim_errors["claim01"]["code"] == "workflow_error"
    tools.index.connection.close()


def test_repeated_identical_search_stops_retrieval_and_still_assesses(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    search = call("search_records", {"case_id": "case01", "filters": {"target": "report.pdf"}, "cursor": None})
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), search, search, verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert result.assessments[0].status == "supported" and not result.claim_errors
    assert [r.name for r in tools.ledger.entries] == ["extract_case", "search_records"]
    assert any("repeated a search" in n for n in result.assessments[0].limitations)
    tools.index.connection.close()


@pytest.mark.parametrize("status,negated", [("supported", False), ("contradicted", True), ("contradicted", False)])
def test_cited_record_from_a_family_that_cannot_show_the_action_is_unverified(tmp_path, status, negated):
    # The only record is edge_history; a recycle_file claim needs recyclebin, so the verdict is withheld.
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    claim = make_claim(action="recycle_file", negated=negated)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict(status)])
    result = verify_claims(case, [claim], client, TestBudget(), tools)
    assert result.assessments[0].status == "unverified"
    assert "cannot show this action" in result.assessments[0].justification
    tools.index.connection.close()


def test_cited_record_from_a_family_that_can_show_the_action_keeps_its_verdict(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict("supported")])
    result = verify_claims(case, [make_claim(action="download_file")], client, TestBudget(), tools)
    assert result.assessments[0].status == "supported"
    tools.index.connection.close()


def lnk_record(tools):
    from tests.factories import make_record
    base = tools.index.get("case01", make_record().record_id)
    return make_record(record_id="1" * 64, family="lnk", raw_output_locator=base.raw_output_locator, target="report.pdf")


@pytest.mark.parametrize("negated,status", [(False, "supported"), (True, "contradicted")])
def test_model_is_asked_to_cite_the_retrieved_record_that_can_show_the_action(tmp_path, negated, status):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    claim = make_claim(action="open_document", negated=negated)
    edge_only, with_lnk = verdict(status), verdict(status, cites=["1" * 64])
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), edge_only, with_lnk])
    original = tools.dispatch
    def dispatch(name, arguments, *, claim_id):
        out = original(name, arguments, claim_id=claim_id)
        if name == "extract_case":
            tools.index.add([lnk_record(tools)])
        if name == "search_records":
            tools.ledger.entries[-1].returned_record_ids.append("1" * 64)
        return out
    tools.dispatch = dispatch
    result = verify_claims(case, [claim], client, TestBudget(), tools)
    assert result.assessments[0].status == status and result.assessments[0].cited_record_ids == ["1" * 64]
    # the retry request (not the final one, which is rebuilt) must have carried the instruction
    assert any("cannot show this action" in m["content"] for r in client.requests for m in r["messages"] if m["role"] == "user")
    tools.index.connection.close()


def add_download_record(tools, target="report.pdf"):
    """Index a record that shows a download and make the next search return it."""
    from datetime import datetime, timezone
    from tests.factories import make_record
    from veritrace.evidence.models import EvidenceTime
    stamp = EvidenceTime(role="download_started", raw_value=1, raw_encoding="x", raw_precision="us", normalized_utc=datetime(2026, 10, 16, 8, 25, 19, tzinfo=timezone.utc))
    original = tools.dispatch
    def dispatch(name, arguments, *, claim_id):
        out = original(name, arguments, claim_id=claim_id)
        if name == "extract_case":
            base = tools.index.get("case01", make_record().record_id)
            tools.index.add([make_record(record_id="2" * 64, times=[stamp], target=target, raw_output_locator=base.raw_output_locator)])
        if name == "search_records":
            tools.ledger.entries[-1].returned_record_ids.append("2" * 64)
        return out
    tools.dispatch = dispatch


def run_claim(tmp_path, claim, answers, target="report.pdf"):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    add_download_record(tools, target)
    script = [call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None})]
    script.append(finished())
    script.extend(answers)  # after a correction request the host goes straight to the next answer
    client = ReplayClient(script)
    result = verify_claims(case, [claim], client, TestBudget(), tools)
    tools.index.connection.close()
    return result, client


def test_a_denial_marked_supported_by_the_record_that_shows_the_action_is_corrected(tmp_path):
    claim = make_claim(negated=True)
    result, client = run_claim(tmp_path, claim, [verdict("supported", ["2" * 64]), verdict("contradicted", ["2" * 64])])
    assert result.assessments[0].status == "contradicted"
    assert any("first answer was 'supported'" in l for l in result.assessments[0].limitations)  # the audit trail shows the revision
    assert any("denial" in m["content"] for r in client.requests for m in r["messages"] if m["role"] == "user")


def test_unverified_while_citing_a_record_that_shows_the_action_is_corrected(tmp_path):
    result, _ = run_claim(tmp_path, make_claim(), [verdict("unverified", ["2" * 64]), verdict("supported", ["2" * 64])])
    assert result.assessments[0].status == "supported"


def test_a_model_that_will_not_correct_itself_ends_inconclusive_not_wrong(tmp_path):
    claim = make_claim(negated=True)
    result, _ = run_claim(tmp_path, claim, [verdict("supported", ["2" * 64])] * 3)
    assessment = result.assessments[0]
    assert assessment.status == "inconclusive" and "does not fit that verdict" in assessment.limitations[-1]


def test_unverified_citing_a_record_for_another_file_is_left_alone(tmp_path):
    claim = make_claim(target="invoice.xlsx")
    result, _ = run_claim(tmp_path, claim, [verdict("unverified", ["2" * 64])], target="report.pdf")
    assert result.assessments[0].status == "unverified"


def test_correction_that_fits_in_no_form_ends_inconclusive_not_an_error(tmp_path):
    from veritrace.agents.verify import verify_claims
    from veritrace.errors import ContextOverflowError
    class TightBudget:
        finals = 0
        def ensure(self, messages, tools, schema):
            if schema is not None:
                self.finals += 1
                if self.finals >= 2:
                    raise ContextOverflowError("does not fit")
    case, tools = backend(tmp_path)
    add_download_record(tools)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict("supported", ["2" * 64])])
    result = verify_claims(case, [make_claim(negated=True)], client, TightBudget(), tools)
    assert not result.claim_errors
    assert result.assessments[0].status == "inconclusive" and "context budget" in result.assessments[0].limitations[-1]
    tools.index.connection.close()


def test_correction_request_does_not_resend_the_rejected_answer(tmp_path):
    claim = make_claim(negated=True)
    _, client = run_claim(tmp_path, claim, [verdict("supported", ["2" * 64]), verdict("contradicted", ["2" * 64])])
    last = client.requests[-1]["messages"]
    assert not any(m["role"] == "assistant" and "Available positive browser record" in str(m.get("content")) for m in last)
    assert last[-2]["content"].startswith("Your answer was rejected")


def test_correction_that_does_not_fit_with_the_transcript_is_asked_again_with_only_the_cited_records(tmp_path):
    from veritrace.agents.verify import verify_claims
    from veritrace.errors import ContextOverflowError
    class TranscriptTooBig:
        finals = 0
        def ensure(self, messages, tools, schema):
            if schema is not None:
                self.finals += 1
                if self.finals == 2 and any(m["role"] == "tool" for m in messages):
                    raise ContextOverflowError("does not fit")
    case, tools = backend(tmp_path)
    add_download_record(tools)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict("supported", ["2" * 64]), verdict("contradicted", ["2" * 64])])
    result = verify_claims(case, [make_claim(negated=True)], client, TranscriptTooBig(), tools)
    assessment = result.assessments[0]
    assert not result.claim_errors and assessment.status == "contradicted"
    last = client.requests[-1]["messages"]
    assert not any(m["role"] == "tool" for m in last) and any("2" * 64 in str(m["content"]) for m in last)
    assert any("first answer was 'supported'" in l for l in assessment.limitations)
    tools.index.connection.close()


def test_claim_outside_coverage_is_answered_unverified_by_the_host_without_asking_the_model(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"})])
    result = verify_claims(case, [make_claim(action="send_email", target="boss")], client, TestBudget(), tools)
    assert not result.claim_errors
    assessment = result.assessments[0]
    assert assessment.status == "unverified" and assessment.cited_record_ids == [] and "send_email" in assessment.justification
    assert [r.name for r in tools.ledger.entries] == ["extract_case"] and len(client.requests) == 1
    tools.index.connection.close()
