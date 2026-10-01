import hashlib
import json
from pathlib import Path


def write_case(tmp_path, testimony="I downloaded report.pdf.", case_id="case01"):
    root = tmp_path / "input"
    (root / "evidence").mkdir(parents=True)
    (root / "testimony.txt").write_bytes(testimony.encode("utf-8"))
    (root / "evidence" / "History").write_bytes(b"synthetic SQLite placeholder")
    manifest = {"schema_version": 1, "case_id": case_id, "items": [{"item_id": "history01", "acquired_path": "History", "original_path": "C:\\Users\\Victim\\AppData\\Local\\Microsoft\\Edge\\User Data\\Default\\History", "family": "edge_history"}]}
    (root / "case.json").write_text(json.dumps(manifest), encoding="utf-8")
    return root


def make_claim(sentence="I downloaded report.pdf.", start=0, **overrides):
    from veritrace.agents.models import Claim
    values = {"claim_id": "claim01", "sentence": sentence, "start": start, "end": start + len(sentence), "action": "download_file", "target": "report.pdf", "actor": "I", "negated": False, "time_expression": None, "resolved_start": None, "resolved_end": None, "uncertainty": [], "interpretation_notes": []}
    return Claim(**(values | overrides))


def make_record(case_id="case01", **overrides):
    from veritrace.evidence.models import EvidenceRecord, SourceLocator
    values = {"record_id": hashlib.sha256(b"synthetic-record").hexdigest(), "case_id": case_id, "family": "edge_history", "item_id": "history01", "source_sha256": hashlib.sha256(b"synthetic SQLite placeholder").hexdigest(), "original_path": "C:\\Users\\Victim\\History", "locator": SourceLocator(kind="sqlite", identifiers={"table": "downloads", "id": 7}), "times": [], "application": "Edge", "target": "report.pdf", "parser": {"name": "synthetic", "version": "1", "config_sha256": "0" * 64}, "raw_fields": {"id": 7}, "raw_output_locator": {"path": "raw/test.jsonl", "line": 1, "sha256": "0" * 64}, "limitations": []}
    return EvidenceRecord(**(values | overrides))
