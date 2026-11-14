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


def run_status(tmp_path, expression, stamp, status="supported", **claim_overrides):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    object.__setattr__(case, "manifest", case.manifest.model_copy(update={"source_timezone": "Asia/Singapore"}))
    timed = record_at(stamp).times
    real_get = tools.index.get
    tools.index.get = lambda case_id, record_id: real_get(case_id, record_id).model_copy(update={"times": timed})  # extraction re-runs inside verify_claims
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict(status)])
    result = verify_claims(case, [make_claim(time_expression=expression, **claim_overrides)], client, TestBudget(), tools)
    tools.index.connection.close()
    return result


def run_supported(tmp_path, expression, stamp):
    return run_status(tmp_path, expression, stamp)


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


def test_time_agrees_needs_an_exact_clock_time_and_a_matching_record():
    from veritrace.agents.timecheck import time_agrees
    record = record_at("2026-10-16T08:25:19")
    at = lambda expr: make_claim(time_expression=expr)
    assert time_agrees(at("4:25 pm"), [record], "Asia/Singapore")
    assert not time_agrees(at("5:10 pm"), [record], "Asia/Singapore")
    assert not time_agrees(at("around 4:25 pm"), [record], "Asia/Singapore")  # vague: not decided by the host
    assert not time_agrees(at(None), [record], "Asia/Singapore")
    assert not time_agrees(at("4:25 pm"), [record], None)


def test_contradicted_is_withheld_when_a_cited_record_matches_the_stated_time(tmp_path):
    """Regression: qwen3:8b called 'I deleted it at 4:27 pm' contradicted although the deletion was at 16:27."""
    (assessment,) = run_status(tmp_path, "4:25 pm", "2026-10-16T08:25:19", "contradicted").assessments
    assert assessment.status == "inconclusive"
    assert "Host check" in assessment.justification
    assert any("contradicted to inconclusive" in limit for limit in assessment.limitations)


def test_contradicted_is_kept_for_a_time_mismatch_and_for_negated_claims(tmp_path):
    assert run_status(tmp_path / "a", "5:10 pm", "2026-10-16T08:25:19", "contradicted").assessments[0].status == "contradicted"
    assert run_status(tmp_path / "b", "4:25 pm", "2026-10-16T08:25:19", "contradicted", negated=True).assessments[0].status == "contradicted"


class OverflowAfterSearch:
    """A budget whose window is full once the model has searched: the next tool-enabled request does not fit."""
    def __init__(self, tools):
        self.tools = tools

    def ensure(self, messages, tools, schema):
        from veritrace.errors import ContextOverflowError
        if tools is not None and any(r.name == "search_records" for r in self.tools.ledger.entries):
            raise ContextOverflowError("Request exceeds the conservative context budget")


def test_a_full_context_after_a_search_finalizes_from_the_evidence_found_instead_of_failing(tmp_path):
    """Regression: qwen3:8b kept searching other families, the next request no longer fit, and the claim failed."""
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)
    client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), verdict("supported")])
    result = verify_claims(case, [make_claim()], client, OverflowAfterSearch(tools), tools)
    tools.index.connection.close()
    (assessment,) = result.assessments
    assert not result.claim_errors and assessment.status == "supported"
    assert any("Retrieval stopped early" in limit for limit in assessment.limitations)
    assert client.requests[-1]["tools"] is None and client.requests[-1]["schema"]  # the final turn carries no tool definitions


def test_a_full_context_before_any_search_is_still_a_claim_error(tmp_path):
    from veritrace.agents.verify import verify_claims
    case, tools = backend(tmp_path)

    class AlwaysFull:
        def ensure(self, messages, tools, schema):
            from veritrace.errors import ContextOverflowError
            if tools is not None and tools and tools[0]["function"]["name"] != "extract_case":
                raise ContextOverflowError("Request exceeds the conservative context budget")
    client = ReplayClient([call("extract_case", {"case_id": "case01"})])
    result = verify_claims(case, [make_claim()], client, AlwaysFull(), tools)
    tools.index.connection.close()
    assert result.claim_errors["claim01"]["code"] == "context_limit" and not result.assessments
