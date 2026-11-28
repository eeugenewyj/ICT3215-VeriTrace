"""A searched claim must not lose its assessment merely because retrieval hit its cap."""
import json

from tests.factories import make_claim, make_record
from tests.fakes import TestBudget
from tests.test_tools import backend
from tests.test_verification import call, verdict


class ModeClient:
    def __init__(self, retrieval, finals):
        self.retrieval, self.finals, self.requests = list(retrieval), list(finals), []

    def chat(self, messages, *, tools=None, schema=None):
        self.requests.append(json.loads(json.dumps({'messages': messages, 'tools': tools, 'schema': schema})))
        return self.finals.pop(0) if schema else self.retrieval.pop(0)


def searches(count, *, empty=False):
    return [call('search_records', {'case_id': 'case01', 'filters': {} if i == 0 and not empty else {'target': f'absent{i}.pdf'}, 'cursor': None}) for i in range(count)]


def test_twelve_executed_calls_finalize_with_retrieved_evidence(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ModeClient([call('extract_case', {'case_id': 'case01'}), *searches(13)], [verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.claim_errors and len(result.assessments) == 1
    assessment = result.assessments[0]
    assert assessment.cited_record_ids == [make_record().record_id]
    assert assessment.status == 'supported'
    assert any('tool-call limit' in note for note in assessment.limitations)
    assert len([r for r in tools.ledger.entries if r.claim_id == 'claim01']) == 12
    assert sum(r['tools'] is not None for r in client.requests) == 13  # extraction plus twelve retrieval requests
    assert client.requests[-1]['tools'] is None and client.requests[-1]['schema']
    tools.index.connection.close()


def test_batch_that_would_exceed_the_remaining_allowance_is_not_executed(tmp_path):
    from veritrace.agents.verify import verify_claims
    from veritrace.runtime.client import ModelTurn
    case, tools = backend(tmp_path)
    extra = searches(2, empty=True)
    oversized = ModelTurn(tool_calls=[t.tool_calls[0] for t in extra])
    # Use new arguments so duplicate-call stopping is not what terminates retrieval.
    for i, part in enumerate(oversized.tool_calls):
        part['function']['arguments']['filters']['target'] = f'new{i}.pdf'
    client = ModeClient([call('extract_case', {'case_id': 'case01'}), *searches(11), oversized], [verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.claim_errors and result.assessments[0].status == 'supported'
    assert len([r for r in tools.ledger.entries if r.claim_id == 'claim01']) == 11
    assert any('tool-call limit' in note for note in result.assessments[0].limitations)
    tools.index.connection.close()


def test_successful_empty_searches_can_finalize_unverified_at_the_cap(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ModeClient([call('extract_case', {'case_id': 'case01'}), *searches(13, empty=True)], [verdict('unverified', [])])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.claim_errors and result.assessments[0].status == 'unverified'
    assert not result.assessments[0].cited_record_ids
    assert len([r for r in tools.ledger.entries if r.claim_id == 'claim01']) == 12
    tools.index.connection.close()


def test_cap_does_not_bypass_citation_validation_or_allow_more_retrieval(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ModeClient([call('extract_case', {'case_id': 'case01'}), *searches(13)], [verdict(cites=['f' * 64]), verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.claim_errors and result.assessments[0].cited_record_ids == [make_record().record_id]
    assert len([r for r in tools.ledger.entries if r.claim_id == 'claim01']) == 12
    assert sum(r['schema'] is not None for r in client.requests) == 2
    tools.index.connection.close()


def test_invalid_final_answers_still_exhaust_the_two_repair_budget(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ModeClient([call('extract_case', {'case_id': 'case01'}), *searches(13)], [verdict(cites=['f' * 64])] * 3)
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert not result.assessments and result.claim_errors['claim01']['code'] == 'model_error'
    assert len([r for r in tools.ledger.entries if r.claim_id == 'claim01']) == 12
    assert sum(r['schema'] is not None for r in client.requests) == 3
    tools.index.connection.close()
