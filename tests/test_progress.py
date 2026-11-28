import json

from tests.factories import write_case, make_claim, draft_payload
from tests.fakes import ReplayClient, TestBudget
from tests.test_verification import call, verdict, finished


def run_narrated(tmp_path, capsys):
    import hashlib
    from veritrace import progress
    from veritrace.runtime.client import ModelTurn
    from veritrace.service import run_case
    from veritrace.settings import Settings
    from veritrace.parsers.base import CoverageEntry, ExtractionResult
    from tests.factories import make_record
    class Client(ReplayClient):
        def metadata(self):
            return {"model": "synthetic test boundary"}
    class Adapter:
        identity = {"version": "test-1"}
        def extract(self, case, items):
            path = case.working_root / "raw/test.jsonl"
            path.parent.mkdir(exist_ok=True)
            path.write_text('{"id":7}\n')
            record = make_record(raw_output_locator={"path": "raw/test.jsonl", "line": 1, "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
            return ExtractionResult(records=[record], coverage=[CoverageEntry(item_id="history01", family="edge_history", status="parsed", record_count=1)])
    client = Client([ModelTurn(content=json.dumps({"claims": [draft_payload(make_claim())]})), call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {"target": "report.pdf"}, "cursor": None}), finished(), verdict()])
    source = write_case(tmp_path)
    result = run_case(source, tmp_path / "output", Settings(), client=client, budget=TestBudget(), adapters={"edge_history": Adapter()})
    progress.final(result)
    progress.warning()
    return result, capsys.readouterr()


def test_run_narrates_each_stage_on_stderr_and_leaves_stdout_alone(tmp_path, capsys):
    result, out = run_narrated(tmp_path, capsys)
    assert result.status == "complete"
    assert out.out == ""  # stdout is reserved for the JSON summary
    text = out.err
    order = ["Testimony in question:", "Agent 1 extracted 1 claim(s):", "passed to Agent 2", "Evidence parsed and searchable: edge_history (1 record(s))",
             "Agent 2 is assessing claim claim01", "search_records (target=report.pdf)", "Agent 2's own answer: supported", "Final LLM verdict: SUPPORTED",
             "Where to look for more detail:", "Final warning:"]
    positions = [text.index(marker) for marker in order]
    assert positions == sorted(positions)
    assert "I downloaded report.pdf." in text and "tool_calls.jsonl" in text and "not final" in text


def test_narration_names_the_cited_record_and_the_report_location(tmp_path, capsys):
    result, out = run_narrated(tmp_path, capsys)
    assert "Cited records:" in out.err and "edge_history: report.pdf" in out.err
    assert str(tmp_path / "output" / "report.html") in out.err


def test_narration_can_be_switched_off(tmp_path, capsys):
    from veritrace import progress
    progress.ENABLED = False
    try:
        _, out = run_narrated(tmp_path, capsys)
    finally:
        progress.ENABLED = True
    assert out.err == ""


def test_host_corrections_are_narrated(tmp_path, capsys):
    from tests.test_timecheck import run_supported
    run_supported(tmp_path, "5:10 pm", "2026-10-16T08:25:19")
    assert "Host check: time check" in capsys.readouterr().err


def test_a_broken_result_never_stops_the_narration():
    from veritrace import progress
    progress.tool_call("search_records", {"filters": None}, {"records": [{"times": [{}]}]})  # malformed on purpose
    progress.tool_call("get_record", {}, None)


def test_cli_run_keeps_stdout_as_json_and_ends_with_the_warning(tmp_path, capsys, monkeypatch):
    from veritrace import cli, service
    from veritrace.settings import Settings
    result, _ = run_narrated(tmp_path, capsys)
    monkeypatch.setattr(cli, "load_settings", lambda path: Settings())
    monkeypatch.setattr(service, "run_case", lambda *args, **kwargs: result)
    code = cli.main(["run", "--config", "x.toml", "--case", str(tmp_path), "--output", str(tmp_path / "o2")])
    out = capsys.readouterr()
    assert code == 0
    assert json.loads(out.out)["status"] == "complete"  # scripts still read this
    assert "Final LLM verdict: SUPPORTED" in out.err
    assert out.err.strip().splitlines()[-1].strip().endswith("before relying on any verdict.")


def test_cli_evaluate_stays_quiet(tmp_path, capsys, monkeypatch):
    from veritrace import cli, progress
    from veritrace.settings import Settings
    monkeypatch.setattr(cli, "load_settings", lambda path: Settings())
    monkeypatch.setattr("veritrace.evaluation.corpus.evaluate_corpus", lambda *a, **k: {"metrics": {"operational_failure_rate": 0}})
    try:
        assert cli.main(["evaluate", "--config", "x.toml", "--corpus", str(tmp_path), "--output", str(tmp_path / "o")]) == 0
        assert progress.ENABLED is False
    finally:
        progress.ENABLED = True
