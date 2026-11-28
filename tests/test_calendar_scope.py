"""Calendar arithmetic regressions: same clock time on another date is not a match."""
from datetime import datetime

import pytest

from tests.factories import make_claim
from tests.test_timecheck import record_at, run_status


@pytest.mark.parametrize('expression', ['15 October 2026 at 4:25 pm','2026-10-15 at 16:25','2026-10-15T16:25:00+08:00','October 15, 2026 at 4:25 pm'])
def test_wrong_calendar_day_does_not_match_the_same_clock(expression):
    from veritrace.agents.timecheck import time_agrees,time_conflict
    claim=make_claim(time_expression=expression)
    record=record_at('2026-10-16T08:25:19')
    assert not time_agrees(claim,[record],'Asia/Singapore')
    assert time_conflict(claim,[record],'Asia/Singapore')


def test_date_only_mismatch_is_a_conflict_but_not_a_clock_match():
    from veritrace.agents.timecheck import time_agrees,time_conflict
    claim=make_claim(time_expression='15 October 2026')
    record=record_at('2026-10-16T08:25:19')
    assert time_conflict(claim,[record],'Asia/Singapore')
    assert not time_agrees(claim,[record],'Asia/Singapore')


def test_calendar_is_compared_in_the_source_timezone():
    from veritrace.agents.timecheck import time_agrees,time_conflict
    claim=make_claim(time_expression='16 October 2026 at 12:25 am')
    record=record_at('2026-10-15T16:25:19')
    assert time_agrees(claim,[record],'Asia/Singapore')
    assert time_conflict(claim,[record],'Asia/Singapore') is None


def test_clock_tolerance_is_preserved_across_midnight():
    from veritrace.agents.timecheck import time_agrees
    claim=make_claim(time_expression='15 October 2026 at 11:59 pm')
    assert time_agrees(claim,[record_at('2026-10-15T16:00:30')],'Asia/Singapore')


def test_unsupported_model_bounds_cannot_override_an_explicit_source_date():
    from veritrace.agents.timecheck import time_agrees
    claim=make_claim(time_expression='15 October 2026 at 4:25 pm',resolved_start=datetime.fromisoformat('2026-10-16T16:25:00+08:00'))
    assert not time_agrees(claim,[record_at('2026-10-16T08:25:19')],'Asia/Singapore')


def test_a_differently_dated_record_does_not_show_the_stated_action():
    from veritrace.agents.hints import shows_action
    claim=make_claim(time_expression='15 October 2026')
    assert not shows_action(claim,record_at('2026-10-16T08:25:19'),[claim],'Asia/Singapore')


def test_positive_assessment_with_the_wrong_day_is_withheld(tmp_path):
    result=run_status(tmp_path,'15 October 2026 at 4:25 pm','2026-10-16T08:25:19')
    assert result.assessments[0].status=='inconclusive'
    assert 'Host time check' in result.assessments[0].justification


@pytest.mark.parametrize('expression',['around 15 October 2026','after 15 October 2026','between 15 and 16 October 2026'])
def test_uncertain_or_range_dates_are_not_forced_into_a_single_exact_day(expression):
    from veritrace.agents.timecheck import time_conflict
    assert time_conflict(make_claim(time_expression=expression),[record_at('2026-10-16T08:25:19')],'Asia/Singapore') is None
