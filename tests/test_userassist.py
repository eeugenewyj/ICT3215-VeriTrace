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
