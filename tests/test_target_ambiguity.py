"""Generic targets must not inherit the identity of an earlier named file."""
import pytest

from tests.factories import make_claim


@pytest.mark.parametrize('target',[None,'a document','document','a file','file','an image','something'])
def test_indefinite_targets_remain_indefinite_in_projection_and_search(target):
    from veritrace.agents.hints import claim_view,search_hint
    earlier=make_claim('I downloaded report.pdf.')
    ambiguous=make_claim('I opened a document.',claim_id='c2',action='open_document',target=target)
    claims=[earlier,ambiguous]
    view=claim_view(ambiguous,claims)
    assert view.get('target')==target
    hint=search_hint(ambiguous,claims)
    assert hint is not None and hint['family']=='lnk'
    assert 'target' not in hint


def test_pronoun_search_and_projection_use_the_same_nearest_reference():
    from veritrace.agents.hints import claim_view,search_hint
    earlier=make_claim('I downloaded first.pdf.',target='first.pdf')
    nearest=make_claim('I opened second.pdf.',claim_id='c2',action='open_document',target='second.pdf')
    pronoun=make_claim('I deleted it.',claim_id='c3',action='recycle_file',target='it')
    claims=[earlier,nearest,pronoun]
    assert claim_view(pronoun,claims)['target']=='second.pdf'
    assert search_hint(pronoun,claims)['target']=='second.pdf'
