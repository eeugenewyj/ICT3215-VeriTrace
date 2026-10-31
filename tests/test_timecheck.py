import json

import pytest

from tests.factories import make_claim, make_record
from tests.fakes import ReplayClient, TestBudget
from tests.test_tools import backend
from tests.test_verification import call, finished, verdict


@pytest.mark.parametrize("text,expected", [
    ("4:25 pm", {16 * 3600 + 25 * 60}),
    ("5 PM", {17 * 3600}),
    ("12 am", {0}),
    ("12:30 p.m.", {12 * 3600 + 30 * 60}),
    ("16:25", {16 * 3600 + 25 * 60}),
    ("4:25", {4 * 3600 + 25 * 60, 16 * 3600 + 25 * 60}),
    ("around 4 pm", None), ("about 4:30 pm", None), ("sometime in the afternoon", None),
    ("yesterday", None), (None, None), ("", None), ("5 pmx", None),
])
def test_claimed_seconds(text, expected):
    from veritrace.agents.timecheck import claimed_seconds
    assert claimed_seconds(text) == expected


def record_at(*utc_times):
    from datetime import datetime, timezone
    from veritrace.evidence.models import EvidenceTime
    return make_record(times=[EvidenceTime(role="download_started", raw_value=1, raw_encoding="test", raw_precision="us", normalized_utc=datetime.fromisoformat(t).replace(tzinfo=timezone.utc)) for t in utc_times])


def test_time_conflict_uses_the_source_timezone_and_a_two_minute_tolerance():
    from veritrace.agents.timecheck import time_conflict
    record = record_at("2026-10-16T08:25:19")  # 16:25:19 in Singapore
    at = lambda expr: make_claim(time_expression=expr)
    assert time_conflict(at("4:25 pm"), [record], "Asia/Singapore") is None
    assert time_conflict(at("4:27 pm"), [record], "Asia/Singapore") is None
    assert time_conflict(at("4:23 pm"), [record], "Asia/Singapore") is None
    assert "16:25:19" in time_conflict(at("5:10 pm"), [record], "Asia/Singapore")
    assert time_conflict(at("8:25 am"), [record], "Asia/Singapore")  # the UTC reading is not the witness's clock
    assert time_conflict(at("8:25 am"), [record], "UTC") is None
    assert time_conflict(at("around 5 pm"), [record], "Asia/Singapore") is None  # vague: not checked
    assert time_conflict(at(None), [record], "Asia/Singapore") is None
    assert time_conflict(at("5:10 pm"), [make_record(times=[])], "Asia/Singapore") is None  # nothing to compare


def run_supported(tmp_path, expression, stamp):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    object.__setattr__(case, "manifest", case.manifest.model_copy(update={"source_timezone": "Asia/Singapore"}))
    timed = record_at(stamp).times
    real_get = tools.index.get
    tools.index.get = lambda case_id, record_id: real_get(case_id, record_id).model_copy(update={"times": timed})  # extraction re-runs inside verify_claims
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict("supported")])
    result = verify_claims(case, [make_claim(time_expression=expression)], client, TestBudget(), tools)
    tools.index.connection.close()
    return result


def test_supported_with_a_mismatching_clock_time_is_withheld(tmp_path):
    """Regression: qwen3:8b called a 5:10 pm claim 'supported' against a 16:25 download."""
    result = run_supported(tmp_path, "5:10 pm", "2026-10-16T08:25:19")
    (assessment,) = result.assessments
    assert assessment.status == "inconclusive"
    assert "Host time check" in assessment.justification and "16:25:19" in assessment.justification
    assert any("host time check" in limit for limit in assessment.limitations)
    assert assessment.cited_record_ids == [make_record().record_id]


def test_supported_with_a_matching_clock_time_is_kept(tmp_path):
    (assessment,) = run_supported(tmp_path, "4:25 pm", "2026-10-16T08:25:19").assessments
    assert assessment.status == "supported" and "Host time check" not in assessment.justification


def test_no_source_timezone_means_no_check():
    from veritrace.agents.timecheck import time_conflict
    assert time_conflict(make_claim(time_expression="5:10 pm"), [record_at("2026-10-16T08:25:19")], None) is None
