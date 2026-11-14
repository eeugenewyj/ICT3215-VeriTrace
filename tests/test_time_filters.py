from datetime import datetime, timezone

from tests.factories import make_record


def test_unknown_time_is_not_an_epoch_and_bounds_select_any_declared_role(tmp_path):
    from veritrace.evidence.index import EvidenceIndex, SearchFilters
    from veritrace.evidence.time import native_time
    with EvidenceIndex(tmp_path / "index.sqlite") as index:
        index.add([make_record(), make_record(record_id="1" * 64, times=[native_time(11644473600000000, "webkit_microseconds", "visit")])])
        page = index.search("case01", SearchFilters(start=datetime(1970, 1, 1, tzinfo=timezone.utc), end=datetime(1970, 1, 2, tzinfo=timezone.utc)), None)
        assert len(page.records) == 1
        assert page.records[0].record_id == "1" * 64
