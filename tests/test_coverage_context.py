"""Large-case context regression and complete, bounded coverage access."""
import base64
import json

import pytest

from tests.test_tools import backend
from veritrace.agents.hints import coverage_view
from veritrace.agents.tools import model_view
from veritrace.errors import InputError
from veritrace.parsers.base import CoverageEntry


def entries(count=41):
    return [CoverageEntry(item_id=f"pf{i:04d}", family="prefetch", status="failed", reason="Invalid signature: " + "diagnostic " * 1000,
                          error_code="parser_error", companion_handling=["note " * 200] * 10) for i in range(count)]


def test_summary_keeps_all_statuses_without_scaling_with_source_diagnostics():
    coverage = entries(1000) + [
        CoverageEntry(item_id="parsed", family="prefetch", status="parsed", record_count=8),
        CoverageEntry(item_id="empty", family="jumplist", status="parsed-with-no-records"),
        CoverageEntry(family="edge_history", status="unavailable-in-input"),
        *[CoverageEntry(item_id=f"extra{i}", family="custom" + str(i), status="unsupported") for i in range(1000)]]
    before = coverage[0].model_dump()
    view = coverage_view(coverage)
    rows = {r['family']: r for r in view['families']}
    assert rows['prefetch'] == {'family': 'prefetch', 'items': 1001, 'records': 8, 'statuses': {'failed': 1000, 'parsed': 1}}
    assert rows['jumplist']['statuses'] == {'parsed-with-no-records': 1}
    assert rows['edge_history']['items'] == 0 and rows['edge_history']['statuses'] == {'unavailable-in-input': 1}
    assert rows['other']['items'] == rows['other']['family_count'] == 1000
    assert rows['other']['statuses'] == {'unsupported': 1000}
    assert len(json.dumps(view)) < 900
    assert 'Invalid signature' not in json.dumps(view)
    assert coverage[0].model_dump() == before


def test_filtered_pages_return_every_failure_once_and_leave_full_receipts(tmp_path):
    case, tools = backend(tmp_path)
    try:
        tools.dispatch('extract_case', {'case_id': 'case01'}, claim_id=None)
        tools.coverage = entries() + [CoverageEntry(item_id='good', family='prefetch', status='parsed', record_count=8)]
        args = {'case_id': 'case01', 'family': 'prefetch', 'status': 'failed'}
        summary = tools.dispatch('get_source_coverage', args, claim_id='claim01')
        assert summary['total'] == 41 and not summary['details'] and 'coverage' not in summary
        assert summary['families'][0]['statuses'] == {'failed': 41}
        seen, cursor = [], None
        while True:
            result = tools.dispatch('get_source_coverage', {**args, 'details': True, 'cursor': cursor}, claim_id='claim01')
            assert len(result['coverage']) <= 5 and result['total'] == 41
            shown = model_view('get_source_coverage', result)
            assert len(json.dumps(shown)) < 6000
            assert shown['next_cursor'] == result['next_cursor']
            assert shown['coverage'][0]['excerpted_fields'] == ['reason', 'companions']
            assert shown['coverage'][0]['full_details'] == 'coverage.json'
            assert len(tools.ledger.entries[-1].result['coverage'][0]['reason']) > 10000
            assert len(tools.ledger.entries[-1].result['coverage'][0]['companion_handling']) == 10
            seen.extend(c['item_id'] for c in result['coverage'])
            cursor = result['next_cursor']
            if cursor is None:
                break
        assert seen == [c.item_id for c in tools.coverage if c.status == 'failed']
        item = tools.dispatch('get_source_coverage', {'case_id': 'case01', 'details': True, 'item_id': 'pf0030'}, claim_id='claim01')
        assert item['total'] == 1 and item['coverage'][0]['item_id'] == 'pf0030'
        assert len(item['coverage'][0]['reason']) > 10000
    finally:
        tools.index.connection.close()


@pytest.mark.parametrize('change', [{'family': 'lnk'}, {'status': 'parsed'}, {'item_id': 'pf0001'}, {'case_id': 'other'}, {'details': False}, {'cursor': 'not-base64'}, {'cursor': 'W10='}])
def test_coverage_continuations_refuse_changed_scope_and_malformed_state(tmp_path, change):
    case, tools = backend(tmp_path)
    try:
        tools.extracted = True
        tools.coverage = entries(6)
        args = {'case_id': 'case01', 'family': 'prefetch', 'status': 'failed', 'details': True}
        first = tools.dispatch('get_source_coverage', args, claim_id='claim01')
        with pytest.raises(InputError):
            tools.dispatch('get_source_coverage', {**args, 'cursor': first['next_cursor'], **change}, claim_id='claim01')
        assert tools.ledger.entries[-1].error
        tools.coverage.append(CoverageEntry(item_id='new', family='prefetch', status='failed'))
        with pytest.raises(InputError, match='cursor'):
            tools.dispatch('get_source_coverage', {**args, 'cursor': first['next_cursor']}, claim_id='claim01')
    finally:
        tools.index.connection.close()


@pytest.mark.parametrize('value', [0, 26, True, '5'])
def test_coverage_page_size_is_strict_and_bounded(tmp_path, value):
    case, tools = backend(tmp_path)
    try:
        tools.extracted = True
        with pytest.raises(InputError):
            tools.dispatch('get_source_coverage', {'case_id': 'case01', 'details': True, 'limit': value}, claim_id='claim01')
    finally:
        tools.index.connection.close()


@pytest.mark.parametrize('offset', [-1, True, 1000000])
def test_coverage_cursor_offsets_are_validated(tmp_path, offset):
    case, tools = backend(tmp_path)
    try:
        tools.extracted = True
        tools.coverage = entries(6)
        args = {'case_id': 'case01', 'details': True}
        page = tools.dispatch('get_source_coverage', args, claim_id='claim01')
        state = json.loads(base64.urlsafe_b64decode(page['next_cursor']))
        state['offset'] = offset
        cursor = base64.urlsafe_b64encode(json.dumps(state).encode()).decode()
        with pytest.raises(InputError, match='cursor'):
            tools.dispatch('get_source_coverage', {**args, 'cursor': cursor}, claim_id='claim01')
    finally:
        tools.index.connection.close()


def test_unknown_sources_can_be_inspected_from_the_other_summary(tmp_path):
    case, tools = backend(tmp_path)
    try:
        tools.extracted = True
        tools.coverage = [CoverageEntry(item_id='extra', family='custom', status='unsupported'), CoverageEntry(item_id='pf', family='prefetch', status='parsed')]
        page = tools.dispatch('get_source_coverage', {'case_id': 'case01', 'family': 'other', 'details': True}, claim_id='claim01')
        assert page['total'] == 1 and page['coverage'][0]['family'] == 'custom'
    finally:
        tools.index.connection.close()


def test_large_coverage_allows_initial_search_and_preserves_full_extraction_receipt(tmp_path, monkeypatch):
    from tests.factories import make_claim, make_record
    from tests.fakes import ReplayClient
    from tests.test_verification import call, finished, verdict
    from veritrace.agents.verify import verify_claims
    from veritrace.runtime.budget import ContextBudget
    from veritrace.settings import Settings

    case, tools = backend(tmp_path)
    original = tools.adapters['edge_history'].extract
    def large_extraction(case, items):
        result = original(case, items)
        return result.model_copy(update={'coverage': [*result.coverage, *entries(245)]})
    monkeypatch.setattr(tools.adapters['edge_history'], 'extract', large_extraction)
    metadata = {'digest': 'test', 'template_sha256': 'test', 'runtime_version': 'test'}
    profile = tmp_path / 'budget.json'
    # UTF-8 accounting is deliberately stricter than the desktop tokenizer.
    profile.write_text(json.dumps({'verified': True, 'protocol': 'native-tools-then-json-v1', 'method': 'utf8-upper-bound-v1', 'num_ctx': 16384, **metadata}), encoding='utf-8')
    budget = ContextBudget(Settings(num_ctx=16384, budget_profile=profile), metadata)
    client = ReplayClient([call('extract_case', {'case_id': 'case01'}), call('search_records', {'case_id': 'case01', 'filters': {'target': 'report.pdf'}}), finished(), verdict()])
    try:
        result = verify_claims(case, [make_claim()], client, budget, tools)
        assert not result.claim_errors and result.assessments[0].status == 'supported'
        assert [r.name for r in tools.ledger.entries] == ['extract_case', 'search_records']
        assert len(tools.ledger.entries[0].result['coverage']) >= 246
        assert tools.ledger.entries[0].result['coverage'][1]['reason'].endswith('diagnostic ')
        claim_prompt = json.loads(client.requests[1]['messages'][1]['content'])
        prefetch = next(r for r in claim_prompt['coverage']['families'] if r['family'] == 'prefetch')
        assert prefetch['statuses']['failed'] == 245
        assert make_record().record_id in tools.ledger.returned_ids('claim01')
    finally:
        tools.index.connection.close()
