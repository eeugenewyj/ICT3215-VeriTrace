import csv
import json

import pytest

from tests.factories import write_case


ROWS = {
    "lnk": {"SourceFile": "", "LocalPath": "C:\\Users\\Victim\\report.pdf", "TargetCreated": "2026-10-01T10:00:00+00:00", "TargetModified": "", "TargetAccessed": ""},
    "jumplist": {"SourceFile": "", "EntryNumber": "3", "Path": "C:\\Users\\Victim\\report.pdf", "CreationTime": "2026-10-01T10:00:00+00:00", "LastModified": "2026-10-01T11:00:00+00:00"},
    "prefetch": {"SourceFilename": "", "ExecutableName": "NOTEPAD.EXE", "LastRun": "2026-10-01T10:00:00+00:00", "PreviousRun0": "2026-09-30T10:00:00+00:00", "ParsingError": "False"},
    "recyclebin": {"SourceName": "", "FileName": "C:\\Users\\Victim\\report.pdf", "FileType": "$I", "DeletedOn": "2026-10-01T10:00:00+00:00", "FileSize": "120"},
}


class CsvRunner:
    def __init__(self, row, empty=False):
        self.row, self.empty = row, empty
    def run(self, command, output_dir):
        output_dir.mkdir(parents=True)
        row = dict(self.row)
        source = command[command.index("-f") + 1]
        for key in ("SourceFile", "SourceFilename", "SourceName"):
            if key in row:
                row[key] = source
        with (output_dir / "export.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=list(row))
            writer.writeheader()
            if not self.empty:
                writer.writerow(row)


def case_for(tmp_path, family):
    from veritrace.cases.registry import register_case
    root = write_case(tmp_path)
    path = root / "case.json"
    data = json.loads(path.read_text())
    data["items"][0]["family"] = family
    path.write_text(json.dumps(data))
    return register_case(root, tmp_path / "run")


@pytest.mark.parametrize("family", list(ROWS))
def test_family_mapping_keeps_source_provenance_and_time_roles(tmp_path, family):
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, family)
    adapter = WindowsCsvAdapter(family, ["tool"], "source-inspected", "0" * 64, runner=CsvRunner(ROWS[family]))
    result = adapter.extract(case, case.manifest.items)
    record = result.records[0]
    assert record.source_sha256 == case.manifest.items[0].calculated_sha256
    assert record.locator.resolution == "resolved"
    assert record.raw_output_locator["line"] == 2
    assert len(record.raw_output_locator["sha256"]) == 64
    if family == "prefetch":
        assert [t.role for t in record.times] == ["prefetch_LastRun", "prefetch_PreviousRun0"]
    elif family == "recyclebin":
        assert record.times[0].role == "recycle_bin_deletion"
        assert any("content companion" in limit for limit in record.limitations)


@pytest.mark.parametrize("family", list(ROWS))
def test_empty_and_unknown_csv_have_distinct_coverage(tmp_path, family):
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, family)
    empty = WindowsCsvAdapter(family, ["tool"], "1", "0" * 64, runner=CsvRunner(ROWS[family], empty=True)).extract(case, case.manifest.items)
    assert empty.coverage[0].status == "parsed-with-no-records"
    bad = WindowsCsvAdapter(family, ["tool"], "1", "0" * 64, runner=CsvRunner({"InventedField": "value"})).extract(case, case.manifest.items)
    assert bad.coverage[0].status == "failed"


def test_custom_jumplist_preserves_entry_name(tmp_path):
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, "jumplist")
    row = {"SourceFile": "", "EntryName": "0", "LocalPath": "C:\\report.pdf", "TargetCreated": "2026-10-01T10:00:00+00:00"}
    result = WindowsCsvAdapter("jumplist", ["tool"], "1", "0" * 64, runner=CsvRunner(row)).extract(case, case.manifest.items)
    assert result.records[0].locator.identifiers["entry_name"] == "0"
