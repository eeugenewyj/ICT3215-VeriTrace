import hashlib
import json

import pytest

from tests.factories import write_case
from tests.test_report import Links, result
from veritrace.cases.registry import register_case, sha256_file
from veritrace.errors import InputError, IntegrityError
from veritrace.parsers.base import CoverageEntry
from veritrace.report.coverage import coverage_summary
from veritrace.report.models import RunResult
from veritrace.report.render import render_report
from veritrace.report.review import regenerate_report


def recorded_run(tmp_path, bad_bytes=b''):
    source = write_case(tmp_path)
    manifest = json.loads((source / 'case.json').read_text())
    manifest['items'] = [
        {'item_id': 'bad01', 'family': 'prefetch', 'acquired_path': 'BAD~1.PF', 'original_path': r'C:\Windows\Prefetch\BAD~1.PF'},
        {'item_id': 'good01', 'family': 'prefetch', 'acquired_path': 'NOTEPAD.EXE-12345678.pf'}]
    (source / 'evidence/BAD~1.PF').write_bytes(bad_bytes)
    (source / 'evidence/NOTEPAD.EXE-12345678.pf').write_bytes(b'MAM\x04test')
    (source / 'case.json').write_text(json.dumps(manifest), encoding='utf-8')
    case = register_case(source, tmp_path / 'run')
    value = RunResult(run_id='run01', case_id='case01', testimony=case.testimony, testimony_sha256=case.testimony_sha256, status='partial', coverage=[
        CoverageEntry(item_id='bad01', family='prefetch', status='failed', reason='Expected main CSV export is missing', error_code='parser_error'),
        CoverageEntry(item_id='good01', family='prefetch', status='parsed', record_count=3)])
    (case.working_root / 'run.json').write_text(value.model_dump_json(indent=2), encoding='utf-8')
    render_report(value, case.working_root)
    return case, value


def addendum(tmp_path, case, **note_changes):
    support = tmp_path / 'diagnosis.json'
    support.write_text('{"scope":"synthetic source diagnosis for report tests"}', encoding='utf-8')
    note = {'item_id': 'bad01', 'source_sha256': next(i.calculated_sha256 for i in case.manifest.items if i.item_id == 'bad01'),
            'category': 'empty_short_name_alias_export', 'explanation': 'Alias maps to the related registered file.', 'limitations': ['Synthetic finding; identity checks do not establish its correctness.'], 'related_item_ids': ['good01'], **note_changes}
    payload = {'schema_version': 1, 'case_id': 'case01', 'method': 'Synthetic known-input report check', 'supporting_report': 'diagnosis.json', 'supporting_report_sha256': sha256_file(support), 'notes': [note]}
    path = tmp_path / 'coverage-diagnostics.json'
    path.write_text(json.dumps(payload), encoding='utf-8')
    return path, support, payload


def test_summary_counts_files_separately_from_records_and_missing_family_markers():
    entries = [CoverageEntry(item_id=f'pf{i}', family='prefetch', status='parsed', record_count=2) for i in range(143)]
    entries += [CoverageEntry(item_id=f'bad{i}', family='prefetch', status='failed', reason='Cannot parse') for i in range(41)]
    entries += [CoverageEntry(item_id='empty', family='jumplist', status='parsed-with-no-records'), CoverageEntry(family='edge_history', status='unavailable-in-input')]
    rows = {r['family']: r for r in coverage_summary(entries)}
    assert rows['prefetch']['items'] == 184 and rows['prefetch']['parsed'] == 143
    assert rows['prefetch']['unparsed'] == 41 and rows['prefetch']['records'] == 286
    assert rows['jumplist']['empty'] == 1 and rows['jumplist']['parsed'] == 0
    assert rows['edge_history']['items'] == 0 and rows['edge_history']['unparsed'] == 0
    assert rows['edge_history']['availability'] == ['unavailable-in-input']


def test_report_explains_143_parsed_and_41_unparsed_without_changing_assessments(tmp_path):
    entries = [CoverageEntry(item_id=f'pf{i}', family='prefetch', status='parsed', record_count=1) for i in range(143)]
    entries += [CoverageEntry(item_id=f'bad{i}', family='prefetch', status='failed', reason=f'Original parser reason {i}') for i in range(41)]
    value = result().model_copy(update={'status': 'partial', 'coverage': entries})
    before = value.model_dump()
    document = render_report(value, tmp_path).read_text(encoding='utf-8')
    assert '143 successfully parsed input files; 41 inputs could not be parsed.' in document
    assert '1 of 1 claims have recorded assessments' in document
    assert 'recorded run status remains partial' in document
    assert 'All 184 original coverage entries' in document
    for i in range(41):
        assert f'coverage-bad{i}' in document and f'Original parser reason {i}' in document
    assert value.model_dump() == before
    links = Links(); links.feed(document)
    assert all(link.startswith('#') and link[1:] in links.ids for link in links.links)


@pytest.mark.parametrize('data,category', [(b'', 'empty_input'), (b'not a prefetch file', 'invalid_prefetch_header')])
def test_default_byte_explanations_do_not_guess_alias_or_deleted_status(tmp_path, data, category):
    case, value = recorded_run(tmp_path, data)
    summary = json.loads((case.working_root / 'coverage-summary.json').read_text())
    note = summary['unparsed_inputs'][0]
    assert note['category'] == category and note['bytes'] == len(data)
    assert note['parser_reason'] == 'Expected main CSV export is missing'
    assert note['path'] == r'C:\Windows\Prefetch\BAD~1.PF'
    assert summary['diagnostics'] is None and note['limitations']
    assert value.coverage[0].status == 'failed'


def test_report_regeneration_retains_original_run_and_attaches_source_bound_notes(tmp_path):
    case, value = recorded_run(tmp_path)
    path, support, payload = addendum(tmp_path, case)
    before = {p.relative_to(case.working_root): sha256_file(p) for p in case.working_root.rglob('*') if p.is_file()}
    receipt = regenerate_report(case.working_root, tmp_path / 'review', path)
    output = tmp_path / 'review'
    assert not receipt['model_inference_performed'] and not receipt['assessments_changed'] and not receipt['parser_outcomes_changed']
    assert (output / 'run.json').read_bytes() == (case.working_root / 'run.json').read_bytes()
    assert (output / 'coverage-diagnostics-evidence.json').read_bytes() == support.read_bytes()
    summary = json.loads((output / 'coverage-summary.json').read_text())
    assert summary['families'][0]['with_diagnostic_notes'] == 1
    assert summary['unparsed_inputs'][0]['category'] == 'empty_short_name_alias_export'
    assert summary['unparsed_inputs'][0]['parser_status'] == 'failed'
    assert summary['diagnostics']['supporting_report_sha256'] == sha256_file(support)
    assert before == {p.relative_to(case.working_root): sha256_file(p) for p in case.working_root.rglob('*') if p.is_file()}


@pytest.mark.parametrize('changes,exception', [
    ({'case_id': 'other'}, InputError),
    ({'item_id': 'missing'}, InputError),
    ({'item_id': 'good01'}, InputError),
    ({'source_sha256': 'f' * 64}, IntegrityError),
    ({'related_item_ids': ['notregistered']}, InputError),
    ({'supporting_report': '../diagnosis.json'}, InputError),
    ({'supporting_report_sha256': 'f' * 64}, IntegrityError),
])
def test_report_diagnostics_reject_mismatched_case_source_and_provenance(tmp_path, changes, exception):
    case, value = recorded_run(tmp_path)
    path, support, payload = addendum(tmp_path, case)
    for key, val in changes.items():
        (payload if key in ('case_id', 'supporting_report', 'supporting_report_sha256') else payload['notes'][0])[key] = val
    path.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(exception):
        regenerate_report(case.working_root, tmp_path / 'review', path)
    assert not (tmp_path / 'review').exists()


def test_changed_working_source_blocks_a_supplied_diagnosis(tmp_path):
    case, value = recorded_run(tmp_path)
    path, support, payload = addendum(tmp_path, case)
    (case.working_root / 'evidence/BAD~1.PF').write_bytes(b'changed')
    with pytest.raises(IntegrityError, match='working-source hash'):
        regenerate_report(case.working_root, tmp_path / 'review', path)
    assert not (tmp_path / 'review').exists()


def test_duplicate_notes_are_refused_and_untrusted_explanations_are_escaped(tmp_path):
    case, value = recorded_run(tmp_path)
    path, support, payload = addendum(tmp_path, case, explanation='<script>alert("diagnosis")</script>')
    regenerate_report(case.working_root, tmp_path / 'review', path)
    document = (tmp_path / 'review/report.html').read_text(encoding='utf-8')
    assert '<script>' not in document and '&lt;script&gt;' in document
    assert 'source hashes are checked' in document
    payload['notes'] *= 2
    path.write_text(json.dumps(payload), encoding='utf-8')
    with pytest.raises(InputError, match='Duplicate source diagnostic'):
        regenerate_report(case.working_root, tmp_path / 'duplicate', path)


@pytest.mark.parametrize('destination', ['run/child', 'input/child', 'run'])
def test_report_output_cannot_overwrite_evidence_or_previous_run(tmp_path, destination):
    case, value = recorded_run(tmp_path)
    with pytest.raises(InputError):
        regenerate_report(case.working_root, tmp_path / destination)


def test_report_cli_does_not_load_config_or_call_a_model(tmp_path, monkeypatch, capsys):
    from veritrace import cli
    case, value = recorded_run(tmp_path)
    def unexpected(*args, **kwargs):
        pytest.fail('Report generation must not load model configuration')
    monkeypatch.setattr(cli, 'load_settings', unexpected)
    assert cli.main(['report', '--run', str(case.working_root), '--output', str(tmp_path / 'review')]) == 0
    receipt = json.loads(capsys.readouterr().out)
    assert receipt['recorded_status'] == 'partial' and receipt['model_inference_performed'] is False
