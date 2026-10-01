import json

import pytest

from tests.factories import write_case, make_claim
from tests.fakes import ReplayClient, TestBudget


def registered(tmp_path, text):
    from veritrace.cases.registry import register_case
    return register_case(write_case(tmp_path, text), tmp_path / "run")


def test_repeated_sentence_requires_distinct_source_spans(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I opened résumé.pdf.\r\nI opened résumé.pdf."
    case = registered(tmp_path, text)
    first = make_claim("I opened résumé.pdf.", action="open_document")
    wrong = first.model_copy(update={"claim_id": "claim02"})
    correct = make_claim("I opened résumé.pdf.", start=len("I opened résumé.pdf.\r\n"), claim_id="claim02", action="open_document")
    client = ReplayClient.from_contents([json.dumps({"claims": [first.model_dump(mode="json"), wrong.model_dump(mode="json")]}), json.dumps({"claims": [first.model_dump(mode="json"), correct.model_dump(mode="json")]})])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 2
    assert [c.start for c in claims] == [0, 22]
    assert claims[1].sentence == text[22:42]


def test_negation_uncertainty_and_unsupported_action_retained(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I think I never emailed it."
    case = registered(tmp_path, text)
    claim = make_claim(text, action="send_email", target=None, negated=True, uncertainty=["I think", "unclear target"])
    client = ReplayClient.from_contents([json.dumps({"claims": [claim.model_dump(mode="json")]})])
    result = extract_claims(case, client, TestBudget())
    assert result[0].negated is True
    assert result[0].uncertainty == ["I think", "unclear target"]
    assert result[0].action == "send_email"


@pytest.mark.parametrize("problem", ["span", "relative", "empty"])
def test_invalid_claims_exhaust_repairs_as_operational_error(tmp_path, problem):
    from veritrace.agents.claims import extract_claims
    from veritrace.errors import ModelError
    case = registered(tmp_path, "I downloaded it yesterday.")
    claim = make_claim(case.testimony, time_expression="yesterday")
    value = claim.model_dump(mode="json")
    if problem == "span":
        value["sentence"] = "invented statement"
    elif problem == "relative":
        value["resolved_start"] = "2026-10-01T00:00:00+08:00"
    body = json.dumps({"claims": [] if problem == "empty" else [value]})
    client = ReplayClient.from_contents([body] * 3)
    with pytest.raises(ModelError):
        extract_claims(case, client, TestBudget())
    assert len(client.requests) == 3
