import hashlib

import pytest

from tests.factories import make_record


def test_pagination_is_stable_and_case_scoped(tmp_path):
    from veritrace.evidence.index import EvidenceIndex, SearchFilters
    with EvidenceIndex(tmp_path / "index.sqlite") as index:
        records = [make_record(record_id=hashlib.sha256(str(i).encode()).hexdigest()) for i in range(26)]
        index.add(records)
        index.add(records)
        index.add([make_record("other")])
        first = index.search("case01", SearchFilters(), None)
        second = index.search("case01", SearchFilters(), first.next_cursor)
        assert len(first.records) == 25 and len(second.records) == 1
        assert first.total == 26
        assert {r.record_id for r in first.records}.isdisjoint(r.record_id for r in second.records)
        assert second.next_cursor is None


def test_literals_unicode_paths_url_case_and_cursor_binding(tmp_path):
    from veritrace.evidence.index import EvidenceIndex, SearchFilters
    from veritrace.errors import InputError
    with EvidenceIndex(tmp_path / "index.sqlite") as index:
        index.add([make_record(target="C:\\Users\\Victim\\résumé_100%.pdf"), make_record(record_id="1" * 64, target="https://example.test/Case")])
        assert len(index.search("case01", SearchFilters(target="RÉSUMÉ_100%"), None).records) == 1
        assert not index.search("case01", SearchFilters(target="https://example.test/case"), None).records
        first = index.search("case01", SearchFilters(), None, limit=1)
        with pytest.raises(InputError):
            index.search("case01", SearchFilters(target="changed"), first.next_cursor)
        with pytest.raises(InputError):
            index.get("other", make_record().record_id)
