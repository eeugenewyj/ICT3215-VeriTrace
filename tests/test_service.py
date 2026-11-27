import json

import pytest

from tests.factories import write_case, make_claim, draft_payload
from tests.fakes import ReplayClient, TestBudget
from tests.test_verification import call, verdict, finished


def test_model_failure_still_produces_explicit_error_report(tmp_path):
    from veritrace.service import run_case
    from veritrace.settings import Settings
    from veritrace.errors import ModelError
    class Offline:
        def metadata(self):
            raise ModelError("offline")
    source = write_case(tmp_path)
    result = run_case(source, tmp_path / "output", Settings(), client=Offline())
    assert result.status == "error"
    assert not result.assessments
    assert result.errors[0]["code"] == "model_error"
    for name in ("report.html", "run.json", "claims.json", "assessments.json", "coverage.json", "evidence.sqlite", "tool_calls.jsonl"):
        assert (tmp_path / "output" / name).is_file()


@pytest.mark.parametrize("testimony,action,negated,status", [
    ("I downloaded report.pdf.", "download_file", False, "supported"),
    ("I did not download report.pdf.", "did not download", True, "contradicted"),
    ("I never downloaded report.pdf.", "never_downloaded", False, "contradicted"),
])
def test_service_exports_genuine_dispatch_receipts_and_cited_records(tmp_path, testimony, action, negated, status):
    import hashlib
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
    from veritrace.runtime.client import ModelTurn
    client = Client([ModelTurn(content=json.dumps({"claims": [draft_payload(make_claim(testimony, action=action, negated=negated))]})), call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict(status)])
    source = write_case(tmp_path, testimony)
    result = run_case(source, tmp_path / "output", Settings(), client=client, budget=TestBudget(), adapters={"edge_history": Adapter()})
    assert result.status == "complete"
    assert len(result.records) == 1
    assert len(result.tool_receipts) == 2
    assert [r.name for r in result.tool_receipts] == ["extract_case", "search_records"]
    assert (result.claims[0].action, result.claims[0].negated) == ("download_file", status == "contradicted")
    stored = json.loads((tmp_path / "output/run.json").read_text())
    assert stored["testimony"] == source.joinpath("testimony.txt").read_text()
    assert stored["assessments"][0]["cited_record_ids"] == [make_record().record_id]
    assert stored["assessments"][0]["status"] == status


def test_placeholder_denial_exhausting_repairs_is_reported_as_model_error(tmp_path):
    from veritrace.runtime.client import ModelTurn
    from veritrace.service import run_case
    from veritrace.settings import Settings
    class Client(ReplayClient):
        def metadata(self):
            return {"model": "synthetic test boundary"}
    testimony = "I have never used Notepad."
    body = json.dumps({"claims": [draft_payload(make_claim(testimony, action="null", target="Notepad"))]})
    client = Client([ModelTurn(content=body)] * 3)
    result = run_case(write_case(tmp_path, testimony), tmp_path / "output", Settings(), client=client, budget=TestBudget(), adapters={})
    assert result.status == "error"
    assert result.errors[0]["code"] == "model_error"
    assert "action" in result.errors[0]["message"]
    assert not result.assessments and not result.tool_receipts
