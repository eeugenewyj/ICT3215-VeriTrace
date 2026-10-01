import json

from tests.factories import write_case, make_claim
from tests.fakes import ReplayClient, TestBudget
from tests.test_verification import call, verdict


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


def test_service_exports_genuine_dispatch_receipts_and_cited_records(tmp_path):
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
    client = Client([ModelTurn(content=json.dumps({"claims": [make_claim().model_dump(mode="json")]})), call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), verdict()])
    source = write_case(tmp_path)
    result = run_case(source, tmp_path / "output", Settings(), client=client, budget=TestBudget(), adapters={"edge_history": Adapter()})
    assert result.status == "complete"
    assert len(result.records) == 1
    assert len(result.tool_receipts) == 2
    stored = json.loads((tmp_path / "output/run.json").read_text())
    assert stored["testimony"] == source.joinpath("testimony.txt").read_text()
    assert stored["assessments"][0]["cited_record_ids"] == [make_record().record_id]
