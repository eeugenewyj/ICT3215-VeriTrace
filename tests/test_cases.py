import hashlib
import json

import pytest

from tests.factories import write_case


def alter_manifest(root, change):
    path = root / "case.json"
    data = json.loads(path.read_text())
    change(data)
    path.write_text(json.dumps(data))


def test_registration_preserves_bytes_and_inventory(tmp_path):
    from veritrace.cases.registry import register_case
    from veritrace.cases.integrity import verify_originals
    text = "I opened résumé.pdf.\r\nI did not delete it."
    source = write_case(tmp_path, text)
    (source / "evidence" / "History-wal").write_bytes(b"sidecar")
    original = (source / "case.json").read_bytes()
    case = register_case(source, tmp_path / "run")
    assert case.testimony == text
    assert case.testimony_sha256 == hashlib.sha256(text.encode()).hexdigest()
    assert len(case.manifest.items) == 2
    assert next(i for i in case.manifest.items if i.acquired_path == "History-wal").family == "unknown"
    assert (case.working_root / "evidence" / "History-wal").read_bytes() == b"sidecar"
    assert (source / "case.json").read_bytes() == original
    verify_originals(case)


@pytest.mark.parametrize("problem", ["bad_utf8", "duplicate", "hash", "missing", "traversal"])
def test_invalid_evidence_rejected_before_creating_run(tmp_path, problem):
    from veritrace.cases.registry import register_case
    from veritrace.errors import VeriTraceError
    source = write_case(tmp_path)
    if problem == "bad_utf8":
        (source / "testimony.txt").write_bytes(b"\xff")
    elif problem == "duplicate":
        alter_manifest(source, lambda d: d["items"].append(d["items"][0]))
    elif problem == "hash":
        alter_manifest(source, lambda d: d["items"][0].update(supplied_sha256="0" * 64))
    elif problem == "missing":
        alter_manifest(source, lambda d: d["items"][0].update(acquired_path="Absent"))
    else:
        alter_manifest(source, lambda d: d["items"][0].update(acquired_path="../case.json"))
    output = tmp_path / "run"
    with pytest.raises(VeriTraceError):
        register_case(source, output)
    assert not output.exists()


def test_overlapping_existing_and_reparse_paths_rejected(tmp_path, monkeypatch):
    from veritrace.cases import registry
    from veritrace.errors import InputError
    source = write_case(tmp_path)
    for output in (source / "run", tmp_path):
        with pytest.raises(InputError):
            registry.register_case(source, output)
    monkeypatch.setattr(registry, "is_reparse", lambda p: p.name == "History")
    with pytest.raises(InputError):
        registry.register_case(source, tmp_path / "run")


def test_changed_original_or_metadata_detected(tmp_path):
    from veritrace.cases.registry import register_case
    from veritrace.cases.integrity import verify_originals
    from veritrace.errors import IntegrityError, InputError
    source = write_case(tmp_path)
    case = register_case(source, tmp_path / "run")
    with pytest.raises(InputError):
        register_case(source, tmp_path / "run")
    (source / "evidence" / "History").write_bytes(b"changed")
    with pytest.raises(IntegrityError):
        verify_originals(case)


def test_stable_id_uses_case_source_and_locator():
    from veritrace.evidence.models import SourceLocator, stable_record_id
    locator = SourceLocator(kind="sqlite", identifiers={"table": "visits", "id": 1})
    first = stable_record_id("case01", "edge_history", "0" * 64, locator)
    assert first == stable_record_id("case01", "edge_history", "0" * 64, locator)
    assert first != stable_record_id("case02", "edge_history", "0" * 64, locator)
    assert first != stable_record_id("case01", "edge_history", "1" * 64, locator)
