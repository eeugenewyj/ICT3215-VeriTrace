"""Regression: a PECmd 2026.10 Prefetch row made get_record overflow the 4096-token budget."""
import json

from veritrace.agents.tools import model_view
from veritrace.evidence.models import EvidenceRecord, SourceLocator
from veritrace.evidence.time import native_time

RUNS = ["LastRun", *[f"PreviousRun{i}" for i in range(7)]]
VOLUME = r"\VOLUME{01dbd0c7a7a5e1f2-5c3a1b2e}"


def prefetch_record():
    row = {"Note": "", "SourceFilename": r"C:\VeriTraceWork\runs\x\working\evidence\NOTEPAD.EXE-0D1583A9.pf",
           "SourceCreated": "2026-06-02T03:11:09.1234567+00:00", "SourceModified": "2026-11-01T17:26:13.1234567+00:00",
           "SourceAccessed": "2026-11-09T06:50:01.1234567+00:00", "ExecutableName": "NOTEPAD.EXE",
           "FullPath": VOLUME + r"\WINDOWS\SYSTEM32\NOTEPAD.EXE", "PathValidated": "False", "Hash": "0D1583A9",
           "Size": "88381", "Version": "Windows 10 or Windows 11", "RunCount": "12",
           **{name: f"2026-10-2{i}T10:0{i}:00.1234567+00:00" for i, name in enumerate(RUNS)},
           "Volume0Name": VOLUME, "Volume0Serial": "5C3A1B2E", "Volume0Created": "2025-06-14T09:12:44.0000000+00:00",
           "Directories": ", ".join([VOLUME + r"\WINDOWS\SYSTEM32"] * 20),
           "FilesLoaded": ", ".join([VOLUME + r"\WINDOWS\SYSTEM32\NTDLL.DLL"] * 60), "ParsingError": "False"}
    return EvidenceRecord(
        record_id="a" * 64, case_id="case01", family="prefetch", item_id="pf01", source_sha256="0" * 64,
        original_path=r"C:\Windows\Prefetch\NOTEPAD.EXE-0D1583A9.pf",
        locator=SourceLocator(kind="parser_item", identifiers={"source_file": "NOTEPAD.EXE-0D1583A9.pf", "parser_item": 1}),
        times=[native_time(row[name], "iso8601", "prefetch_" + name) for name in RUNS], account=None, sid=None,
        application="NOTEPAD.EXE", target="NOTEPAD.EXE", parser={"name": "PECmd"}, raw_fields=row,
        raw_output_locator={"path": "raw/prefetch/export.csv", "line": 2, "row": 1, "sha256": "0" * 64},
        limitations=["Prefetch is program-execution context; missing Prefetch does not prove non-execution."])


def test_prefetch_get_record_view_drops_bulky_and_duplicate_fields():
    view = model_view("get_record", prefetch_record().model_dump(mode="json"))
    assert set(view["details"]) == {"FullPath", "RunCount", "Version"}
    assert len(view["times"]) == 8  # run times stay, once, as normalized UTC
    assert len(json.dumps(view)) < 1500


def test_full_record_is_still_kept_for_audit():
    assert "FilesLoaded" in prefetch_record().model_dump(mode="json")["raw_fields"]
