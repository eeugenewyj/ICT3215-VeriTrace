import csv
import json
import struct

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

# Header rows copied from PECmd 2026.10.3.0 output (practice laptop Prefetch, 2026-11-09).
PECMD_2026_MAIN = "Note,SourceFilename,SourceCreated,SourceModified,SourceAccessed,ExecutableName,FullPath,PathValidated,Hash,Size,Version,RunCount,LastRun,PreviousRun0,PreviousRun1,PreviousRun2,PreviousRun3,PreviousRun4,PreviousRun5,PreviousRun6,Volume0Name,Volume0Serial,Volume0Created,Volume1Name,Volume1Serial,Volume1Created,Directories,FilesLoaded,ParsingError".split(",")


class PecmdRunner:
    """Writes the main export plus a timeline CSV, as PECmd does."""
    def __init__(self, timeline_headers):
        self.timeline_headers = timeline_headers
    def run(self, command, output_dir):
        output_dir.mkdir(parents=True)
        source = command[command.index("-f") + 1]
        main = dict.fromkeys(PECMD_2026_MAIN, "")
        main |= {"SourceFilename": source, "ExecutableName": "NOTEPAD.EXE", "RunCount": "12", "LastRun": "2026-11-01T17:26:02.9677786+00:00", "PreviousRun0": "2026-11-01T17:21:36.1438995+00:00", "ParsingError": "False"}
        with (output_dir / "export.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=PECMD_2026_MAIN)
            writer.writeheader()
            writer.writerow(main)
        timeline = {"RunTime": "2026-11-01T17:26:02.9677786+00:00", "ExecutableName": "NOTEPAD.EXE", "SourceFilename": source, "PathValidated": "False"}
        with (output_dir / "export_Timeline.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=self.timeline_headers)
            writer.writeheader()
            writer.writerow({k: timeline[k] for k in self.timeline_headers})


@pytest.mark.parametrize("timeline_headers", [["RunTime", "ExecutableName"], ["RunTime", "ExecutableName", "SourceFilename", "PathValidated"]])
def test_prefetch_timeline_is_skipped_for_old_and_2026_pecmd(tmp_path, timeline_headers):
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, "prefetch")
    result = WindowsCsvAdapter("prefetch", ["PECmd"], "2026.10.3.0", "0" * 64, runner=PecmdRunner(timeline_headers)).extract(case, case.manifest.items)
    assert result.coverage[0].status == "parsed", result.coverage[0].reason
    (record,) = result.records
    assert record.target == "NOTEPAD.EXE" and record.raw_output_locator["path"].endswith("export.csv")
    assert [t.role for t in record.times] == ["prefetch_LastRun", "prefetch_PreviousRun0"]
    assert record.times[0].normalized_utc.isoformat().startswith("2026-11-01T17:26:02")

def test_lnk_uses_embedded_path_and_excludes_working_copy_times(tmp_path):
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, "lnk")
    row = ROWS["lnk"] | {"TargetIDAbsolutePath": "This PC\\report", "SourceCreated": "2099-01-01T00:00:00Z"}
    result = WindowsCsvAdapter("lnk", ["tool"], "1", "0" * 64, runner=CsvRunner(row)).extract(case, case.manifest.items)
    record = result.records[0]
    assert record.target == row["LocalPath"]
    assert [stamp.role for stamp in record.times] == ["target_file_created"]
    assert record.raw_fields["SourceCreated"] == row["SourceCreated"]
    assert "working copy" in record.raw_fields["source_file_timestamps_scope"]


@pytest.mark.parametrize("invalid", [False, True])
def test_missing_jumplist_csv_requires_verified_empty_container(tmp_path, invalid):
    from veritrace.errors import ParserError
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, "jumplist")
    source = tmp_path / "empty.customDestinations-ms"
    source.write_bytes(struct.pack("<6I", 2, 1, 0, 1, 2, 0 if invalid else 0xBABFFBAB))
    output = tmp_path / "parser-output"
    output.mkdir()
    adapter = WindowsCsvAdapter("jumplist", ["tool"], "1", "0" * 64)
    if invalid:
        with pytest.raises(ParserError, match="missing"):
            adapter.read_exports(case, case.manifest.items[0], source, output)
    else:
        assert adapter.read_exports(case, case.manifest.items[0], source, output) == []


def test_jumplist_preserves_known_folder_identity_and_uuid_time_semantics(tmp_path):
    from veritrace.parsers.windows import WindowsCsvAdapter
    case = case_for(tmp_path, "jumplist")
    target = "knownfolder:{374DE290-123F-4565-9164-39C4925E467B}"
    row = ROWS["jumplist"] | {"Path": target + " ==> Downloads", "FileBirthDroid": "98669b4d-bdbb-11f1-8195-000c2952b6f5"}
    record = WindowsCsvAdapter("jumplist", ["tool"], "1", "0" * 64, runner=CsvRunner(row)).extract(case, case.manifest.items).records[0]
    assert record.target == target
    assert record.raw_fields["Path"] == row["Path"]
    assert record.times[0].role == "destlist_birth_object_id_created"
    assert "UUID" in record.times[0].normalization_basis
