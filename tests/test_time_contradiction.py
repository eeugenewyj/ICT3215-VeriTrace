import hashlib

from tests.factories import make_claim, make_record
from tests.test_timecheck import record_at, run_status


class FakeIndex:
    """Just enough of EvidenceIndex for the host's own search of the case."""

    def __init__(self, records, more=False):
        self.records, self.more = records, more

    def search(self, case_id, filters, cursor=None, limit=25):
        from veritrace.evidence.index import RecordPage
        found = [r for r in self.records if r.family == filters.family and filters.target.casefold() in (r.target or "").casefold()]
        return RecordPage(records=found, total=len(found), next_cursor="more" if self.more else None)

    def get(self, case_id, record_id):
        return next(r for r in self.records if r.record_id == record_id)


def record(name, *utc_times, target="report.pdf", family="edge_history"):
    return make_record(record_id=hashlib.sha256(name.encode()).hexdigest(), target=target, family=family, times=record_at(*utc_times).times)


def contradiction(claim, records, cited=None, **kwargs):
    from veritrace.agents.hints import time_contradiction
    index = FakeIndex(records, **kwargs)
    return time_contradiction(claim, [claim], cited if cited is not None else records[:1], index, "case01", "Asia/Singapore")


EVENING = "2026-11-26T10:11:24"  # 18:11 in Singapore
MORNING = "2026-11-26T01:05:00"  # 09:05 in Singapore


def test_the_only_record_hours_away_from_the_stated_time_is_a_contradiction():
    """Regression (acquired run, "about 9:00 am" against a download at 18:11): the host could only answer inconclusive."""
    text = contradiction(make_claim(time_expression="about 9:00 am"), [record("a", EVENING)])
    assert text and "outside the stated time" in text and "18:11:24" in text


def test_an_exact_time_hours_away_is_a_contradiction_too():
    assert contradiction(make_claim(time_expression="9:00 am"), [record("a", EVENING)])


def test_another_record_at_the_stated_time_keeps_the_answer_inconclusive():
    claim = make_claim(time_expression="about 9:00 am")
    assert contradiction(claim, [record("a", EVENING), record("b", MORNING)], cited=[record("a", EVENING)]) is None


def test_a_record_for_a_different_file_does_not_count_as_agreement():
    claim = make_claim(time_expression="about 9:00 am")
    other = record("b", MORNING, target="other.pdf")
    assert contradiction(claim, [record("a", EVENING), other], cited=[record("a", EVENING)])


def test_denials_and_not_remembering_are_never_contradicted_by_time():
    assert contradiction(make_claim(time_expression="about 9:00 am", negated=True), [record("a", EVENING)]) is None
    assert contradiction(make_claim(time_expression="about 9:00 am", uncertainty=["witness does not remember or is not sure"]), [record("a", EVENING)]) is None


def test_no_clock_time_or_a_range_is_never_contradicted():
    for expression in (None, "yesterday", "sometime in the morning", "between 8 and 9 am"):
        assert contradiction(make_claim(time_expression=expression), [record("a", EVENING)]) is None


def test_date_only_scope_does_not_enable_the_clock_contradiction_check():
    assert contradiction(make_claim(time_expression="25 November 2026"), [record("a", EVENING)]) is None


def test_another_calendar_day_may_be_a_different_occurrence():
    for expression in ("25 November 2026 at 6:11 pm", "25 November 2026 at 9:00 am"):
        assert contradiction(make_claim(time_expression=expression), [record("a", EVENING)]) is None


def test_clock_mismatch_on_the_stated_local_day_keeps_the_new_check():
    claim = make_claim(time_expression="26 November 2026 at 9:00 am")
    assert contradiction(claim, [record("a", EVENING)])
    # This UTC timestamp falls on 26 November in the source timezone.
    assert contradiction(claim, [record("b", "2026-11-25T16:11:24")])


def test_too_many_records_to_read_keeps_the_answer_inconclusive():
    assert contradiction(make_claim(time_expression="about 9:00 am"), [record("a", EVENING)], more=True) is None


def test_the_cited_record_must_be_one_that_shows_the_action():
    claim = make_claim(time_expression="about 9:00 am")
    assert contradiction(claim, [record("a", EVENING)], cited=[record("z", EVENING, target="other.pdf")]) is None


def test_a_launch_claim_is_checked_against_prefetch_records():
    claim = make_claim(sentence="I ran notepad.exe.", action="launch_program", target="notepad.exe", time_expression="9:00 am")
    assert contradiction(claim, [record("a", EVENING, target="NOTEPAD.EXE-1234.pf", family="prefetch")])


def test_full_pipeline_changes_supported_to_contradicted_and_keeps_the_citation(tmp_path):
    result = run_status(tmp_path, "about 9:00 am", "2026-10-16T08:25:19")
    (assessment,) = result.assessments
    assert assessment.status == "contradicted"
    assert assessment.justification.startswith("Host time check:") and "outside the stated time" in assessment.justification
    assert any("supported to contradicted" in limit for limit in assessment.limitations)
    assert assessment.cited_record_ids == [make_record().record_id]
