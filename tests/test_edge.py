import json
import sqlite3
from types import SimpleNamespace

import pytest

from tests.factories import write_case


def edge_case(tmp_path, duplicate=False):
    from veritrace.cases.registry import register_case
    root = write_case(tmp_path)
    (root / "evidence" / "History").unlink()
    with sqlite3.connect(root / "evidence" / "History") as db:
        db.executescript('CREATE TABLE urls(id INTEGER PRIMARY KEY, url TEXT); CREATE TABLE visits(id INTEGER PRIMARY KEY,url INTEGER,visit_time INTEGER); CREATE TABLE downloads(id INTEGER PRIMARY KEY,target_path TEXT,start_time INTEGER,end_time INTEGER,last_access_time INTEGER,opened INTEGER); CREATE TABLE downloads_url_chains(id INTEGER,chain_index INTEGER,url TEXT);')
        db.execute("INSERT INTO urls VALUES(1,?)", ("https://example.test/report.pdf",))
        db.execute("INSERT INTO visits VALUES(7,1,11644473600000000)")
        if duplicate:
            db.execute("INSERT INTO visits VALUES(8,1,11644473600000000)")
        db.execute("INSERT INTO downloads VALUES(2,?,11644473600000000,11644473601000000,0,0)", ("C:\\Users\\Victim\\Downloads\\report.pdf",))
        db.execute("INSERT INTO downloads_url_chains VALUES(2,0,?)", ("https://example.test/report.pdf",))
    db.close()
    return register_case(root, tmp_path / "run")


class ExportRunner:
    def __init__(self, lines):
        self.lines = lines
    def run(self, command, output_dir):
        output_dir.mkdir(parents=True)
        prefix = command[command.index("-o") + 1]
        with open(prefix + ".jsonl", "w", encoding="utf-8") as stream:
            for line in self.lines:
                stream.write(json.dumps(line) + "\n")
        return SimpleNamespace(exit_code=0)


def test_visit_and_download_native_ids_and_raw_timestamps(tmp_path):
    from veritrace.parsers.edge import EdgeAdapter
    case = edge_case(tmp_path)
    rows = [{"data_type": "chrome:history:page_visited", "visit_id": 7, "url": "https://example.test/report.pdf", "datetime": "1970-01-01T00:00:00+00:00"}, {"data_type": "chrome:history:file_downloaded", "download_id": 2, "target_path": "C:\\Users\\Victim\\Downloads\\report.pdf", "datetime": "1970-01-01T00:00:00+00:00", "timestamp_desc": "File Downloaded"}]
    result = EdgeAdapter(["hindsight"], "2026.06", "0" * 64, runner=ExportRunner(rows)).extract(case, case.manifest.items)
    assert len(result.records) == 2
    visit = next(r for r in result.records if r.locator.identifiers["table"] == "visits")
    assert visit.locator.identifiers["id"] == 7
    assert visit.times[0].raw_value == 11644473600000000
    assert visit.times[0].normalized_utc.isoformat() == "1970-01-01T00:00:00+00:00"
    assert visit.raw_output_locator["line"] == 1
    download = next(r for r in result.records if r.locator.identifiers["table"] == "downloads")
    assert download.locator.identifiers["chain_indices"] == [0]
    assert all(r.locator.resolution == "resolved" for r in result.records)
    assert result.coverage[0].record_count == 2


def test_ambiguous_rows_are_not_guessed(tmp_path):
    from veritrace.parsers.edge import EdgeAdapter
    case = edge_case(tmp_path, duplicate=True)
    rows = [{"data_type": "chrome:history:page_visited", "url": "https://example.test/report.pdf", "datetime": "1970-01-01T00:00:00+00:00"}, {"data_type": "chrome:history:file_downloaded", "download_id": 2, "target_path": "C:\\Users\\Victim\\Downloads\\report.pdf", "datetime": "1970-01-01T00:00:00+00:00"}]
    result = EdgeAdapter(["hindsight"], "2026.06", "0" * 64, runner=ExportRunner(rows)).extract(case, case.manifest.items)
    assert result.coverage[0].status == "failed"
    assert "unresolved native row identities" in result.coverage[0].reason
    assert not result.records
    assert list((case.working_root / "raw/edge").glob("*/output/hindsight.jsonl"))


@pytest.mark.parametrize("rows", [[{"data_type": "invented"}], []])
def test_unknown_schema_or_silent_missing_records_is_failure(tmp_path, rows):
    from veritrace.parsers.edge import EdgeAdapter
    case = edge_case(tmp_path)
    result = EdgeAdapter(["hindsight"], "2026.06", "0" * 64, runner=ExportRunner(rows)).extract(case, case.manifest.items)
    assert result.coverage[0].status == "failed"
    assert not result.records
