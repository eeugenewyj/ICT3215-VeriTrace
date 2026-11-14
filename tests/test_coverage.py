from tests.factories import write_case, make_record


class Index:
    def __init__(self):
        self.records = []
    def add(self, records):
        self.records.extend(records)


def test_complete_inventory_and_cache_key(tmp_path):
    from veritrace.cases.registry import register_case
    from veritrace.parsers.base import CoverageEntry, ExtractionResult
    from veritrace.parsers.coverage import extract_case
    source = write_case(tmp_path)
    (source / "evidence" / "Other").write_bytes(b"unknown")
    case = register_case(source, tmp_path / "run")
    class Adapter:
        identity = {"version": "1", "config": "a", "normalization": "1"}
        calls = 0
        def extract(self, case, items):
            self.calls += 1
            return ExtractionResult(records=[], coverage=[CoverageEntry(item_id=i.item_id, family=i.family, status="parsed-with-no-records") for i in items])
    adapter, index = Adapter(), Index()
    first = extract_case(case, {"edge_history": adapter}, index)
    assert next(c for c in first if c.item_id == "history01").status == "parsed-with-no-records"
    assert any(c.status == "unsupported" and c.family == "unknown" for c in first)
    assert any(c.status == "unsupported" and c.family == "prefetch" for c in first)
    assert extract_case(case, {"edge_history": adapter}, index) == first
    assert adapter.calls == 1
    adapter.identity = {"version": "2", "config": "a", "normalization": "1"}
    extract_case(case, {"edge_history": adapter}, index)
    assert adapter.calls == 2


def test_source_failure_does_not_hide_other_sources(tmp_path):
    import json
    from veritrace.cases.registry import register_case
    from veritrace.parsers.base import CoverageEntry, ExtractionResult
    from veritrace.parsers.coverage import extract_case
    from veritrace.errors import ParserError
    source = write_case(tmp_path)
    (source / "evidence" / "one.lnk").write_bytes(b"link")
    path = source / "case.json"
    data = json.loads(path.read_text())
    data["items"].append({"item_id": "link01", "acquired_path": "one.lnk", "family": "lnk"})
    path.write_text(json.dumps(data))
    case = register_case(source, tmp_path / "run")
    class Bad:
        identity = {"version": "1"}
        def extract(self, *args):
            raise ParserError("corrupt database")
    class Good:
        identity = {"version": "1"}
        def extract(self, case, items):
            return ExtractionResult(records=[], coverage=[CoverageEntry(item_id=items[0].item_id, family="lnk", status="parsed-with-no-records")])
    result = extract_case(case, {"edge_history": Bad(), "lnk": Good()}, Index())
    assert next(c for c in result if c.item_id == "history01").status == "failed"
    assert next(c for c in result if c.item_id == "link01").status == "parsed-with-no-records"
