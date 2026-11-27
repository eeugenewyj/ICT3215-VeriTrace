import csv
import json

from tests.test_windows_adapters import case_for


class RegistryRunner:
    def __init__(self, decoded=True):
        self.decoded = decoded
    def run(self, command, output_dir):
        output_dir.mkdir(parents=True)
        fields = ["HivePath", "KeyPath", "ValueName", "ValueData", "ValueData2", "ValueData3", "PluginDetailFile"]
        row = {"HivePath": command[command.index("-f") + 1], "KeyPath": "Software\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist\\{TEST}\\Count", "ValueName": "ABGRCNQ.RKR", "ValueData": "NOTEPAD.EXE", "ValueData2": "Last executed: 2026-10-01 10:00:00.0000000", "ValueData3": "Run count: 3", "PluginDetailFile": "export_UserAssist.csv" if self.decoded else ""}
        with (output_dir / "export.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerow(row)
        (output_dir / "export_UserAssist.csv").write_text("ProgramName,RunCounter,LastExecuted\nNOTEPAD.EXE,3,2026-10-01 10:00:00.0000000\n")


def test_decoded_userassist_keeps_encoded_name_and_key_identity(tmp_path):
    from veritrace.parsers.userassist import UserAssistAdapter
    case = case_for(tmp_path, "userassist")
    batch = tmp_path / "UserAssist.reb"
    batch.write_text("test batch")
    result = UserAssistAdapter(["RECmd"], "source-inspected", "0" * 64, batch, runner=RegistryRunner()).extract(case, case.manifest.items)
    record = result.records[0]
    assert record.target == "NOTEPAD.EXE"
    assert record.locator.identifiers["value_name"] == "ABGRCNQ.RKR"
    assert record.times[0].role == "userassist_last_execution"
    assert record.times[0].normalized_utc.isoformat() == "2026-10-01T10:00:00+00:00"
    assert record.account is None


def test_missing_userassist_decoder_is_failure_not_empty(tmp_path):
    from veritrace.parsers.userassist import UserAssistAdapter
    case = case_for(tmp_path, "userassist")
    batch = tmp_path / "UserAssist.reb"
    batch.write_text("test batch")
    result = UserAssistAdapter(["RECmd"], "1", "0" * 64, batch, runner=RegistryRunner(decoded=False)).extract(case, case.manifest.items)
    assert result.coverage[0].status == "failed"
    assert not result.records


UA = "ROOT\\SOFTWARE\\Microsoft\\Windows\\CurrentVersion\\Explorer\\UserAssist"
COUNT = UA + "\\{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}\\Count"
ENTRIES = [
    ("{PNYP}\\abgrcnq.rkr", "{System}\\notepad.exe", "Last executed: 2026-11-27 07:14:30.5300000", "Run count: 4"),
    ("HRZR_PGYFRFFVBA", "UEME_CTLSESSION", "Last executed: ", "Run count: 102"),
]


class RealShapeRunner:
    """Mirrors RECmd 2026.11 batch output for a recursive UserAssist batch: parent-key echoes, a valueless
    {GUID} row, the real Count rows, and a plugin detail file inside a timestamp sub-folder."""
    def __init__(self, extra_parent=None, drop_count=False, extra_guid=None):
        self.extra_parent, self.drop_count, self.extra_guid = extra_parent, drop_count, extra_guid
    def run(self, command, output_dir):
        output_dir.mkdir(parents=True)
        hive = command[command.index("-f") + 1]
        detail_dir = output_dir / "20261127081122"
        detail_dir.mkdir()
        detail = detail_dir / "export_UserAssist.csv"
        detail.write_text("BatchKeyPath,BatchValueName,ProgramName,RunCounter,LastExecuted\n" + "".join(f"{COUNT},{n},{p},{c.removeprefix('Run count: ')},{t.removeprefix('Last executed: ')}\n" for n, p, t, c in ENTRIES), encoding="utf-8")
        fields = ["HivePath", "HiveType", "Description", "Category", "KeyPath", "ValueName", "ValueType", "ValueData", "ValueData2", "ValueData3", "Comment", "Recursive", "Deleted", "LastWriteTimestamp", "PluginDetailFile"]
        def row(key, name="", data="", data2="", data3=""):
            return {"HivePath": hive, "HiveType": "NTUSER", "Description": "UserAssist", "Category": "Execution", "KeyPath": key, "ValueName": name, "ValueType": "", "ValueData": data, "ValueData2": data2, "ValueData3": data3, "Comment": "user assist", "Recursive": "True", "Deleted": "False", "LastWriteTimestamp": "2026-11-27T07:15:13+00:00", "PluginDetailFile": str(detail)}
        guid_key = UA + "\\{CEBFF5CD-ACE2-4F4F-9178-9926F41749EA}"
        rows = [row(UA, *e) for e in ENTRIES] + [row(guid_key, "Version", "5")]
        if self.extra_guid:
            rows.append(row(guid_key, *self.extra_guid))
        if self.extra_parent:
            rows.append(row(UA, *self.extra_parent))
        if not self.drop_count:
            rows += [row(COUNT, *e) for e in ENTRIES]
        with (output_dir / "export.csv").open("w", newline="", encoding="utf-8") as stream:
            writer = csv.DictWriter(stream, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)


def _extract(tmp_path, runner):
    from veritrace.parsers.userassist import UserAssistAdapter
    case = case_for(tmp_path, "userassist")
    batch = tmp_path / "UserAssist.reb"
    batch.write_text("test batch")
    return UserAssistAdapter(["RECmd"], "test", "0" * 64, batch, runner=runner).extract(case, case.manifest.items)


def test_recursive_batch_output_uses_count_rows_once(tmp_path):
    result = _extract(tmp_path, RealShapeRunner())
    assert result.coverage[0].status == "parsed" and result.coverage[0].record_count == 2
    assert all(r.locator.identifiers["key_path"].endswith("\\Count") for r in result.records)
    assert len({r.record_id for r in result.records}) == 2
    notepad = next(r for r in result.records if r.target == "{System}\\notepad.exe")
    assert notepad.times[0].normalized_utc.isoformat() == "2026-11-27T07:14:30.530000+00:00"


def test_counter_without_execution_time_keeps_no_time_and_no_basis(tmp_path):
    result = _extract(tmp_path, RealShapeRunner())
    session = next(r for r in result.records if r.target == "UEME_CTLSESSION")
    assert session.times[0].normalized_utc is None
    assert session.times[0].normalization_basis is None
    assert "No execution time" in session.times[0].uncertainty


def test_parent_row_that_is_not_a_count_echo_fails_instead_of_being_dropped(tmp_path):
    result = _extract(tmp_path, RealShapeRunner(extra_parent=("ABC", "SOMETHING", "Last executed: 2026-11-27 07:00:00.0000000", "Run count: 1")))
    assert result.coverage[0].status == "failed" and not result.records


def test_batch_without_count_rows_fails(tmp_path):
    result = _extract(tmp_path, RealShapeRunner(drop_count=True))
    assert result.coverage[0].status == "failed" and not result.records


def test_guid_key_value_other_than_version_fails(tmp_path):
    result = _extract(tmp_path, RealShapeRunner(extra_guid=("Surprise", "x", "", "")))
    assert result.coverage[0].status == "failed" and not result.records


def test_guid_key_version_value_is_not_an_execution_record(tmp_path):
    result = _extract(tmp_path, RealShapeRunner())
    assert result.coverage[0].status == "parsed"
    assert all(r.locator.identifiers["value_name"] != "Version" for r in result.records)
