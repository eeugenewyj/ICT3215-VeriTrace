import json
import shutil

import httpx
import pytest

from tests.factories import make_claim, write_case, draft_payload
from tests.fakes import ReplayClient, TestBudget
from tests.test_edge import ExportRunner, edge_case
from tests.test_tools import backend
from tests.test_verification import call, verdict


def edge_rows():
    return [{"data_type": "chrome:history:page_visited", "visit_id": 7, "url": "https://example.test/report.pdf", "datetime": "1970-01-01T00:00:00+00:00"}, {"data_type": "chrome:history:file_downloaded", "download_id": 2, "target_path": "C:\\Users\\Victim\\Downloads\\report.pdf", "datetime": "1970-01-01T00:00:00+00:00"}]


def test_tool_retrieval_and_constrained_finalization_are_separate(tmp_path):
    from veritrace.agents.verify import verify_claims
    from veritrace.runtime.client import ModelTurn
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), ModelTurn(content="Retrieved enough evidence; finalize."), verdict()])
    result = verify_claims(case, [make_claim()], client, TestBudget(), tools)
    assert result.assessments and not result.claim_errors
    assert all(not (request["tools"] and request["schema"]) for request in client.requests)
    assert client.requests[-1]["schema"] and client.requests[-1]["tools"] is None
    tools.index.connection.close()


def test_partial_edge_export_is_failed_even_when_both_event_types_exist(tmp_path):
    from veritrace.parsers.edge import EdgeAdapter
    case = edge_case(tmp_path, duplicate=True)
    result = EdgeAdapter(["hindsight"], "2026.06", "0" * 64, runner=ExportRunner(edge_rows())).extract(case, case.manifest.items)
    assert result.coverage[0].status == "failed"
    assert not result.records


def test_identical_profile_bytes_keep_distinct_account_records(tmp_path):
    from veritrace.cases.registry import register_case
    from veritrace.evidence.index import EvidenceIndex, SearchFilters
    from veritrace.parsers.edge import EdgeAdapter
    first = edge_case(tmp_path / "first")
    source = first.source_root
    shutil.copyfile(source / "evidence/History", source / "evidence/History2")
    manifest = json.loads((source / "case.json").read_text())
    manifest["items"][0]["account"] = "VictimA"
    manifest["items"].append({"item_id": "history02", "acquired_path": "History2", "family": "edge_history", "account": "VictimB", "original_path": "C:\\Users\\VictimB\\History"})
    (source / "case.json").write_text(json.dumps(manifest))
    case = register_case(source, tmp_path / "second-run")
    result = EdgeAdapter(["hindsight"], "2026.06", "0" * 64, runner=ExportRunner(edge_rows())).extract(case, case.manifest.items)
    with EvidenceIndex(tmp_path / "index.sqlite") as index:
        index.add(result.records)
        page = index.search("case01", SearchFilters(), None)
        assert len(page.records) == 4
        assert {r.account for r in page.records} == {"VictimA", "VictimB"}


def parser_settings(tmp_path, command, pins):
    from veritrace.cases.registry import sha256_file
    from veritrace.settings import Settings
    profile = tmp_path / "parser.json"
    profile.write_text(json.dumps({"version": "2026.06", "schema": "hindsight-history-2026.06-v1", "acquired_sample": {"verified": True, "source_sha256": "0" * 64, "comparison_record": "synthetic gate test"}, "command_hashes": {str(p.resolve()): sha256_file(p) for p in pins}}))
    return Settings(parser_commands={"edge_history": command}, parser_profiles={"edge_history": profile}, parser_versions={"edge_history": "2026.06"}, parser_config_hashes={"edge_history": sha256_file(profile)})


def test_unrelated_pin_cannot_authorize_missing_parser_command(tmp_path):
    from veritrace.service import build_adapters, UnavailableAdapter
    pin = tmp_path / "pin.txt"
    pin.write_text("unrelated")
    settings = parser_settings(tmp_path, ["unrelated-unpinned-command.exe"], [pin])
    assert isinstance(build_adapters(settings)["edge_history"], UnavailableAdapter)


def test_path_executable_and_relative_script_resolve_to_pinned_absolute_files(tmp_path, monkeypatch):
    from veritrace.service import build_adapters
    from veritrace.parsers.edge import EdgeAdapter
    exe = tmp_path / "parser.exe"
    exe.write_bytes(b"synthetic executable identity")
    script = tmp_path / "parser.py"
    script.write_text("synthetic script identity")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PATH", str(tmp_path))
    settings = parser_settings(tmp_path, ["parser.exe", "parser.py"], [exe, script])
    adapter = build_adapters(settings)["edge_history"]
    assert isinstance(adapter, EdgeAdapter)
    assert adapter.command == [str(exe.resolve()), str(script.resolve())]


@pytest.mark.parametrize("stage", ["extraction", "claim"])
def test_malformed_nested_tool_call_produces_error_report(tmp_path, stage):
    from veritrace.runtime.client import OllamaClient
    from veritrace.service import run_case
    from veritrace.settings import Settings
    turns = [{"role": "assistant", "content": json.dumps({"claims": [draft_payload(make_claim())]})}]
    if stage == "claim":
        turns.append({"role": "assistant", "content": "", "tool_calls": [{"function": {"name": "extract_case", "arguments": {"case_id": "case01"}}}]})
    turns.append({"role": "assistant", "content": "", "tool_calls": [{"function": None}]})
    def handler(request):
        if request.url.path == "/api/version":
            body = {"version": "test"}
        elif request.url.path == "/api/tags":
            body = {"models": [{"name": "qwen3:8b", "digest": "abc", "details": {}}]}
        elif request.url.path == "/api/show":
            body = {"capabilities": ["tools"], "template": "test"}
        else:
            body = {"message": turns.pop(0), "done": True}
        return httpx.Response(200, json=body)
    source = write_case(tmp_path)
    with OllamaClient(Settings(), transport=httpx.MockTransport(handler)) as client:
        result = run_case(source, tmp_path / "output", Settings(), client=client, budget=TestBudget(), adapters={})
    assert result.status in ("error", "partial")
    assert result.errors or result.claim_errors
    assert (tmp_path / "output/report.html").is_file()


@pytest.mark.parametrize("models", [None, [None], ["not a model"], [{"name": "qwen3:8b", "digest": "abc", "details": None}]])
def test_malformed_model_inventory_is_a_model_error(models):
    from veritrace.runtime.client import OllamaClient
    from veritrace.errors import ModelError
    from veritrace.settings import Settings
    def handler(request):
        body = {"version": "test"} if request.url.path == "/api/version" else {"models": models} if request.url.path == "/api/tags" else {"capabilities": ["tools"], "template": "test"}
        return httpx.Response(200, json=body)
    with OllamaClient(Settings(), transport=httpx.MockTransport(handler)) as client:
        with pytest.raises(ModelError):
            client.metadata()


def test_renamed_declared_wal_is_used_and_recorded(tmp_path):
    import sqlite3
    from veritrace.cases.registry import register_case
    from veritrace.parsers.edge import EdgeAdapter
    initial = edge_case(tmp_path / "initial")
    source = initial.source_root
    history = source / "evidence/History"
    db = sqlite3.connect(history)
    try:
        db.execute("PRAGMA journal_mode=WAL")
        db.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        db.execute("INSERT INTO visits VALUES(9,1,11644473600000001)")
        db.commit()
        shutil.copyfile(history, source / "evidence/history.bin")
        shutil.copyfile(str(history) + "-wal", source / "evidence/wal.bin")
    finally:
        db.close()
    history.unlink()
    original = initial.manifest.items[0].original_path
    manifest = {"case_id": "case01", "items": [{"item_id": "history01", "acquired_path": "history.bin", "family": "edge_history", "original_path": original, "companion_item_ids": ["wal01"]}, {"item_id": "wal01", "acquired_path": "wal.bin", "original_path": original + "-wal"}]}
    (source / "case.json").write_text(json.dumps(manifest))
    case = register_case(source, tmp_path / "new-run")
    class WalRunner(ExportRunner):
        def run(self, command, output_dir):
            profile = command[command.index("-i") + 1]
            with sqlite3.connect(str(profile) + "/History") as checked:
                assert checked.execute("SELECT count(*) FROM visits WHERE id=9").fetchone()[0] == 1
            super().run(command, output_dir)
    rows = edge_rows()
    rows.insert(1, dict(rows[0], visit_id=9))
    result = EdgeAdapter(["hindsight"], "2026.06", "0" * 64, runner=WalRunner(rows)).extract(case, [case.manifest.items[0]])
    assert result.coverage[0].status == "parsed", result.coverage[0].reason
    assert any(r.locator.identifiers.get("id") == 9 for r in result.records)
    assert result.records[0].raw_fields["companion_sources"][0]["item_id"] == "wal01"
    assert "wal01" in " ".join(result.coverage[0].companion_handling)


def test_renamed_registry_log_is_staged_beside_the_hive(tmp_path):
    from veritrace.cases.registry import register_case
    from veritrace.parsers.userassist import UserAssistAdapter
    from tests.test_userassist import RegistryRunner
    source = write_case(tmp_path)
    (source / "evidence/History").rename(source / "evidence/hive.bin")
    (source / "evidence/log.bin").write_bytes(b"synthetic registry log")
    original = "C:\\Users\\Victim\\NTUSER.DAT"
    (source / "case.json").write_text(json.dumps({"case_id": "case01", "items": [{"item_id": "hive01", "family": "userassist", "acquired_path": "hive.bin", "original_path": original, "companion_item_ids": ["log01"]}, {"item_id": "log01", "acquired_path": "log.bin", "original_path": original + ".LOG1"}]}))
    case = register_case(source, tmp_path / "run")
    batch = tmp_path / "batch.reb"
    batch.write_text("synthetic batch")
    class CheckedRunner(RegistryRunner):
        def run(self, command, output_dir):
            from pathlib import Path
            hive = Path(command[command.index("-f") + 1])
            assert hive.with_name(hive.name + ".LOG1").read_bytes() == b"synthetic registry log"
            super().run(command, output_dir)
    result = UserAssistAdapter(["RECmd"], "test", "0" * 64, batch, runner=CheckedRunner()).extract(case, [case.manifest.items[0]])
    assert result.coverage[0].status == "parsed", result.coverage[0].reason
    assert "log01" in " ".join(result.coverage[0].companion_handling)
