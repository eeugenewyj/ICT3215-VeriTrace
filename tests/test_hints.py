from veritrace.agents.hints import search_hint, target_word
from veritrace.agents.models import Claim


def claim(cid, action, target):
    return Claim(claim_id=cid, sentence="s", start=0, end=1, action=action, target=target, actor=None, negated=False,
                 time_expression=None, resolved_start=None, resolved_end=None, uncertainty=[], interpretation_notes=[])


CLAIMS = [claim("claim_1", "download_file", "the sample image"), claim("claim_2", "open_document", "it"), claim("claim_3", "recycle_file", "it")]


def test_target_word_drops_generic_words_and_pronouns():
    assert target_word("the sample image") == "sample"
    assert target_word("it") is None
    assert target_word(None) is None
    assert target_word("report.pdf") == "report.pdf"


def test_action_selects_family():
    assert search_hint(CLAIMS[0], CLAIMS)["family"] == "edge_history"
    assert search_hint(CLAIMS[1], CLAIMS)["family"] == "lnk"
    assert search_hint(CLAIMS[2], CLAIMS)["family"] == "recyclebin"


def test_pronoun_target_borrows_named_file():
    assert search_hint(CLAIMS[1], CLAIMS) == {"family": "lnk", "then_try_families": ["jumplist", "edge_history"], "target": "sample", "limit": 5}
    assert search_hint(CLAIMS[2], CLAIMS)["target"] == "sample"


def test_unknown_action_without_any_name_gives_no_hint():
    only = [claim("c", "visit_page", "it")]
    assert search_hint(only[0], only) is None


def entry(family, status="parsed", records=1, **extra):
    from veritrace.parsers.base import CoverageEntry
    return CoverageEntry(family=family, status=status, record_count=records, **extra)


def test_hint_only_suggests_families_that_were_parsed():
    coverage = [entry("lnk"), entry("edge_history"), entry("jumplist", "unsupported", 0)]
    hint = search_hint(CLAIMS[1], CLAIMS, coverage)
    assert hint["family"] == "lnk" and hint["then_try_families"] == ["edge_history"]
    no_lnk = [entry("edge_history"), entry("lnk", "failed", 0)]
    assert search_hint(CLAIMS[1], CLAIMS, no_lnk)["family"] == "edge_history"
    assert "family" not in search_hint(CLAIMS[2], CLAIMS, no_lnk)  # nothing parsed can show a deletion


def test_claim_view_drops_the_shared_sentence_and_empty_fields():
    from veritrace.agents.hints import claim_view
    view = claim_view(CLAIMS[2])
    assert "sentence" not in view and "start" not in view and "end" not in view
    assert view["action"] == "recycle_file" and view["negated"] is False
    assert "uncertainty" not in view and "resolved_start" not in view


def test_coverage_view_lists_unparsed_families_by_name_only():
    from veritrace.agents.hints import coverage_view
    view = coverage_view([entry("lnk", item_id="lnk01"), entry("jumplist", "unsupported", 0, reason="Family outside enabled coverage"), entry("prefetch", "unsupported", 0), entry("recyclebin", "failed", 0, error_code="parser_exit")])
    assert view["not_covered"] == ["jumplist", "prefetch"]
    assert [r["family"] for r in view["sources"]] == ["lnk", "recyclebin"]
    assert view["sources"][1]["error"] == "parser_exit"


def test_pronoun_target_is_replaced_by_the_nearest_named_file_for_the_model():
    """Regression: qwen3:8b read 'it' literally and found no file called 'it' in the evidence."""
    from veritrace.agents.hints import claim_view
    assert claim_view(CLAIMS[2], CLAIMS)["target"] == "the sample image"
    assert claim_view(CLAIMS[0], CLAIMS)["target"] == "the sample image"
    alone = [claim("c1", "open_document", "it")]
    assert claim_view(alone[0], alone)["target"] == "it"  # nothing to borrow
    nearest = [claim("a", "download_file", "a.pdf"), claim("b", "open_document", "b.pdf"), claim("c", "recycle_file", "it")]
    assert claim_view(nearest[2], nearest)["target"] == "b.pdf"


def test_tool_search_hint_matches_the_actual_nested_argument_schema():
    from veritrace.agents.hints import tool_search_hint
    from veritrace.agents.tools import SearchArgs
    proposal = tool_search_hint("case01", CLAIMS[1], CLAIMS)
    args = SearchArgs.model_validate(proposal["arguments"])
    assert proposal["name"] == "search_records"
    assert args.case_id == "case01" and args.filters.family == "lnk" and args.filters.target == "sample"
    assert proposal["then_try_families"] == ["jumplist", "edge_history"]
    assert "then_try_families" not in proposal["arguments"]
    only_jumplists = tool_search_hint("case01", CLAIMS[1], CLAIMS, [entry("jumplist")])
    assert SearchArgs.model_validate(only_jumplists["arguments"]).filters.family == "jumplist"


def test_tool_search_hint_keeps_an_unactionable_claim_unresolved():
    from veritrace.agents.hints import tool_search_hint
    only = [claim("c", "visit_page", "it")]
    assert tool_search_hint("case01", only[0], only) is None
