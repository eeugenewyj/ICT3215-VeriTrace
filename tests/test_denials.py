import pytest

from tests.factories import write_case, make_claim, draft_payload
from tests.fakes import ReplayClient, TestBudget
from tests.test_claims import batch, registered


@pytest.mark.parametrize("sentence,denied,hedged", [
    ("I did not download report.pdf.", {"download_file"}, set()),
    ("I didn't open it.", {"open"}, set()),
    ("I never opened STD01-notes.txt in Notepad.", {"open"}, set()),
    ("I have never used Notepad.", {"launch_program"}, set()),
    ("I haven't even deleted it.", {"recycle_file"}, set()),
    ("I don't remember deleting report.pdf.", set(), {"recycle_file"}),
    ("I'm not sure I opened it.", set(), {"open"}),
    ("I can't recall whether I downloaded it.", set(), {"download_file"}),
    ("I downloaded report.pdf but I didn't open it.", {"open"}, set()),
    ("I opened report.pdf.", set(), set()),
    ("I do not think I downloaded report.pdf.", set(), set()),  # a soft denial stays the model's call
])
def test_sentence_analysis_separates_denials_from_hedges(sentence, denied, hedged):
    from veritrace.agents.claims import analyse_sentence
    found_denied, found_hedged, convoluted, _ = analyse_sentence(sentence)
    assert (found_denied, found_hedged, convoluted) == (denied, hedged, False)


def test_double_negation_is_left_to_the_model():
    from veritrace.agents.claims import analyse_sentence
    denied, hedged, convoluted, _ = analyse_sentence("I did not say that I never opened it.")
    assert convoluted and not denied


def test_dropped_denial_in_a_compound_sentence_is_repaired(tmp_path):
    """Regression (real run t3e): 'I downloaded X but I didn't open it.' produced only the download claim."""
    from veritrace.agents.claims import extract_claims
    text = "I downloaded report.pdf but I didn't open it."
    case = registered(tmp_path, text)
    download = make_claim(text, action="download_file", negated=False)
    opened = make_claim(text, claim_id="claim02", action="open_document", negated=True)
    client = ReplayClient.from_contents([batch(draft_payload(download)), batch(draft_payload(download), draft_payload(opened))])
    claims = extract_claims(case, client, TestBudget())
    assert len(client.requests) == 2 and "no negated claim covers" in client.requests[1]["messages"][-1]["content"]
    assert [(c.action, c.negated) for c in claims] == [("download_file", False), ("open_document", True)]


def test_a_denial_that_is_never_extracted_is_an_error_not_a_silent_gap(tmp_path):
    from veritrace.agents.claims import extract_claims
    from veritrace.errors import ModelError
    text = "I downloaded report.pdf but I didn't open it."
    case = registered(tmp_path, text)
    download = make_claim(text, action="download_file", negated=False)
    with pytest.raises(ModelError, match="no negated claim covers"):
        extract_claims(case, ReplayClient.from_contents([batch(draft_payload(download))] * 3), TestBudget())


def test_a_denial_claim_covers_the_sentence_even_with_an_open_program_label(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I never opened Notepad."
    case = registered(tmp_path, text)
    claim = make_claim(text, action="launch_program", target="Notepad", negated=True)
    assert extract_claims(case, ReplayClient.from_contents([batch(draft_payload(claim))]), TestBudget())[0].negated is True


@pytest.mark.parametrize("negated", [True, False])
def test_no_memory_is_recorded_as_uncertainty_not_a_denial(tmp_path, negated):
    """Regression (real run t3e): 'I don't remember deleting X' was recorded as a flat denial."""
    from veritrace.agents.claims import NO_RECALL, extract_claims
    text = "I don't remember deleting report.pdf."
    case = registered(tmp_path, text)
    claim = make_claim(text, action="recycle_file", negated=negated)
    result = extract_claims(case, ReplayClient.from_contents([batch(draft_payload(claim))]), TestBudget())[0]
    assert result.negated is False and NO_RECALL in result.uncertainty
    assert "not remembering" in result.interpretation_notes[-1]


def test_a_positive_sentence_cannot_be_marked_as_a_denial(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I opened report.pdf."
    case = registered(tmp_path, text)
    wrong = make_claim(text, action="open_document", negated=True)
    right = wrong.model_copy(update={"negated": False})
    client = ReplayClient.from_contents([batch(draft_payload(wrong)), batch(draft_payload(right))])
    assert extract_claims(case, client, TestBudget())[0].negated is False
    assert "contains no negation" in client.requests[1]["messages"][-1]["content"]


def test_a_soft_denial_with_uncertainty_is_left_as_the_team_decided(tmp_path):
    from veritrace.agents.claims import extract_claims
    text = "I do not think I downloaded report.pdf."
    case = registered(tmp_path, text)
    claim = make_claim(text, negated=True, uncertainty=["I do not think"])
    result = extract_claims(case, ReplayClient.from_contents([batch(draft_payload(claim))]), TestBudget())[0]
    assert result.negated is True and result.uncertainty == ["I do not think"]


def test_a_witness_who_does_not_remember_gets_neither_supported_nor_contradicted(tmp_path):
    """The record of a deletion neither supports nor contradicts 'I don't remember deleting it'."""
    from veritrace.agents.claims import NO_RECALL
    from veritrace.agents.verify import verify_claims
    from tests.test_verification import add_download_record, backend, call, finished, verdict
    for status in ("supported", "contradicted"):
        case, tools = backend(tmp_path / status)
        add_download_record(tools)
        claim = make_claim(negated=False, uncertainty=[NO_RECALL])
        client = ReplayClient([call("extract_case", {"case_id": "case01"}), call("search_records", {"case_id": "case01", "filters": {}, "cursor": None}), finished(), verdict(status, ["2" * 64])])
        result = verify_claims(case, [claim], client, TestBudget(), tools)
        assessment = result.assessments[0]
        assert assessment.status == "inconclusive" and "do not remember" in assessment.justification
        tools.index.connection.close()
