import json

import pytest

from tests.factories import write_case, make_claim, draft_payload
from tests.fakes import ReplayClient, TestBudget


def registered(tmp_path, text):
    from veritrace.cases.registry import register_case
    return register_case(write_case(tmp_path, text), tmp_path / "run")


def batch(*payloads):
    return json.dumps({"claims": list(payloads)})


def test_repeated_identical_claim_takes_the_next_occurrence_without_a_retry(tmp_path):
    """Regression: qwen3:8b emitted the same claim twice with occurrence 1 and ignored the repair message."""
    from veritrace.agents.claims import extract_claims
    text = "I opened résumé.pdf.\r\nI opened résumé.pdf."
    case = registered(tmp_path, text)
    first = make_claim("I opened résumé.pdf.", action="open_document")
    second = first.model_copy(update={"claim_id": "claim02"})
    client = ReplayClient.from_contents([batch(draft_payload(first), draft_payload(second))])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 1
    assert [c.start for c in claims] == [0, 22]
    assert claims[1].sentence == text[22:42]


def test_explicit_occurrence_still_honoured(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I opened it. I opened it."
    case = registered(tmp_path, text)
    first = make_claim("I opened it.", action="open_document")
    second = first.model_copy(update={"claim_id": "claim02"})
    client = ReplayClient.from_contents([batch(draft_payload(first), draft_payload(second, occurrence=2))])
    assert [c.start for c in extract_claims(case, client, TestBudget())] == [0, 13]


def test_true_duplicate_of_a_sentence_that_occurs_once_is_still_rejected(tmp_path):
    from veritrace.agents.claims import extract_claims
    from veritrace.errors import ModelError
    case = registered(tmp_path, "I opened it.")
    first = make_claim("I opened it.", action="open_document")
    second = first.model_copy(update={"claim_id": "claim02"})
    body = batch(draft_payload(first), draft_payload(second))
    client = ReplayClient.from_contents([body] * 3)
    with pytest.raises(ModelError, match="Duplicate interpretation"):
        extract_claims(case, client, TestBudget())


def test_negation_uncertainty_and_unsupported_action_retained(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I think I never emailed it."
    case = registered(tmp_path, text)
    claim = make_claim(text, action="send_email", target=None, negated=True, uncertainty=["I think", "unclear target"])
    client = ReplayClient.from_contents([batch(draft_payload(claim))])
    result = extract_claims(case, client, TestBudget())
    assert result[0].negated is True
    assert result[0].uncertainty == ["I think", "unclear target"]
    assert result[0].action == "send_email"


def test_code_derives_spans_the_model_miscounted(tmp_path):
    """Regression: qwen3:8b returned the right sentences but offsets off by 1, 1 and 3."""
    from veritrace.agents.claims import extract_claims
    text = "I downloaded invoice.pdf from Edge. I opened it. Then I deleted it."
    case = registered(tmp_path, text)
    sentences = ["I downloaded invoice.pdf from Edge.", "I opened it.", "Then I deleted it."]
    actions = ["download_file", "open_document", "recycle_file"]
    payloads = [draft_payload(make_claim(s, claim_id=f"claim0{i}", action=a, target="invoice.pdf")) for i, (s, a) in enumerate(zip(sentences, actions), 1)]
    client = ReplayClient.from_contents([batch(*payloads)])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 1
    assert [(c.start, c.end) for c in claims] == [(0, 35), (36, 48), (49, 67)]
    assert all(text[c.start:c.end] == c.sentence for c in claims)


def test_distinct_actions_may_share_one_sentence(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I downloaded and opened report.pdf."
    case = registered(tmp_path, text)
    one = make_claim(text, claim_id="claim01", action="download_file")
    two = make_claim(text, claim_id="claim02", action="open_document")
    claims = extract_claims(case, ReplayClient.from_contents([batch(draft_payload(one), draft_payload(two))]), TestBudget())
    assert [(c.start, c.end, c.action) for c in claims] == [(0, 35, "download_file"), (0, 35, "open_document")]


def test_occurrence_beyond_available_sentences_is_repaired_with_a_useful_message(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I opened it. I opened it."
    case = registered(tmp_path, text)
    claim = make_claim("I opened it.", action="open_document")
    client = ReplayClient.from_contents([batch(draft_payload(claim, occurrence=3)), batch(draft_payload(claim, occurrence=2))])
    claims = extract_claims(case, client, TestBudget())
    assert "occurs only 2 time(s)" in client.requests[1]["messages"][-1]["content"]
    assert (claims[0].start, claims[0].end) == (13, 25)


def test_agent_one_schema_does_not_ask_the_model_for_offsets(tmp_path):
    from veritrace.agents.claims import extract_claims
    case = registered(tmp_path, "I opened it.")
    claim = make_claim("I opened it.", action="open_document")
    client = ReplayClient.from_contents([batch(draft_payload(claim))])
    extract_claims(case, client, TestBudget())
    properties = client.requests[0]["schema"]["$defs"]["ClaimDraft"]["properties"]
    assert "start" not in properties and "end" not in properties
    assert "occurrence" in properties


@pytest.mark.parametrize("problem", ["invented", "relative", "empty"])
def test_invalid_claims_exhaust_repairs_as_operational_error(tmp_path, problem):
    from veritrace.agents.claims import extract_claims
    from veritrace.errors import ModelError
    case = registered(tmp_path, "I downloaded it yesterday.")
    claim = make_claim(case.testimony, time_expression="yesterday")
    value = draft_payload(claim)
    if problem == "invented":
        value["sentence"] = "invented statement"
    elif problem == "relative":
        value["resolved_start"] = "2026-10-01T00:00:00+08:00"
    body = batch() if problem == "empty" else batch(value)
    client = ReplayClient.from_contents([body] * 3)
    with pytest.raises(ModelError):
        extract_claims(case, client, TestBudget())
    assert len(client.requests) == 3


def test_invented_time_expression_is_repaired_with_a_useful_message(tmp_path):
    """Regression: qwen3:8b copied the input field name 'reference_time' into time_expression."""
    from veritrace.agents.claims import extract_claims
    case = registered(tmp_path, "I downloaded it.")
    claim = make_claim("I downloaded it.")
    bad = draft_payload(claim) | {"time_expression": "reference_time"}
    client = ReplayClient.from_contents([batch(bad), batch(draft_payload(claim))])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 2
    assert "time_expression" in client.requests[1]["messages"][-1]["content"]
    assert claims[0].time_expression is None


def test_time_expression_copied_from_testimony_is_accepted_ignoring_case(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "Around 2 PM I downloaded it."
    case = registered(tmp_path, text)
    claim = make_claim(text, time_expression="around 2 pm")
    client = ReplayClient.from_contents([batch(draft_payload(claim))])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 1
    assert claims[0].time_expression == "around 2 pm"


def test_placeholder_uncertainty_and_notes_are_dropped_real_ones_kept(tmp_path):
    """Regression: qwen3:8b wrote uncertainty ['none'] when the witness expressed no doubt."""
    from veritrace.agents.claims import extract_claims
    case = registered(tmp_path, "I opened it.")
    claim = make_claim("I opened it.", action="open_document", uncertainty=["none"], interpretation_notes=["N/A", "'it' taken to mean report.pdf from the previous sentence"])
    client = ReplayClient.from_contents([batch(draft_payload(claim))])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 1
    assert claims[0].uncertainty == []
    assert claims[0].interpretation_notes == ["'it' taken to mean report.pdf from the previous sentence"]


def test_bounds_invented_without_any_date_are_dropped_with_a_note(tmp_path):
    """Regression: qwen3:8b resolved 'Around 2 PM' to 2023-10-05 with no date and no reference time."""
    from datetime import datetime, timezone
    from veritrace.agents.claims import extract_claims, NO_DATE_NOTE
    text = "Around 2 PM I downloaded it."
    case = registered(tmp_path, text)
    at = datetime(2023, 10, 5, 14, 0, tzinfo=timezone.utc)
    claim = make_claim(text, time_expression="Around 2 PM", resolved_start=at, resolved_end=at)
    client = ReplayClient.from_contents([batch(draft_payload(claim))])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 1
    assert claims[0].resolved_start is None and claims[0].resolved_end is None
    assert NO_DATE_NOTE in claims[0].interpretation_notes


def test_bounds_kept_when_the_sentence_states_a_date(tmp_path):
    from datetime import datetime, timezone
    from veritrace.agents.claims import extract_claims
    text = "On 5 October 2026 at 2 PM I downloaded it."
    case = registered(tmp_path, text)
    at = datetime(2026, 10, 5, 14, 0, tzinfo=timezone.utc)
    claim = make_claim(text, time_expression="5 October 2026 at 2 PM", resolved_start=at, resolved_end=at)
    claims = extract_claims(case, ReplayClient.from_contents([batch(draft_payload(claim))]), TestBudget())
    assert claims[0].resolved_start == at
