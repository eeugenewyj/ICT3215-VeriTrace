"""Long-testimony and source-fragment regressions from standard01 development checks."""
import json

import pytest

from tests.factories import draft_payload, make_claim
from tests.fakes import ReplayClient, TestBudget
from tests.test_claims import batch, registered


def examples(count=10, newline=' '):
    sentences = [f'I downloaded report{i}.pdf.' for i in range(count)]
    return newline.join(sentences), sentences


def replies(sentences):
    values = []
    for start in range(0, len(sentences), 3):
        values.append(batch(*[draft_payload(make_claim(s, claim_id=f'c{i+1}', target=f'report{start+i}.pdf')) for i, s in enumerate(sentences[start:start+3])]))
    return values


@pytest.mark.parametrize('separator', [' ', '\r\n'])
def test_ten_sentences_use_bounded_batches_and_preserve_all_global_spans(tmp_path, separator):
    from veritrace.agents.claims import extract_claims
    text, sentences = examples(newline=separator)
    case = registered(tmp_path, text)
    client = ReplayClient.from_contents(replies(sentences))
    claims = extract_claims(case, client, TestBudget())
    assert len(claims) == 10 and len(client.requests) == 4
    assert len({c.claim_id for c in claims}) == 10
    assert [c.sentence for c in claims] == sentences
    assert all(text[c.start:c.end] == c.sentence for c in claims)
    assert [c.target for c in claims] == [f'report{i}.pdf' for i in range(10)]
    assert all('batch' in ' '.join(c.interpretation_notes).lower() for c in claims)
    for request in client.requests:
        payload = json.loads(request['messages'][1]['content'])
        assert len(payload['testimony'].split('I downloaded')) <= 4


def test_preceding_interpretations_are_context_not_additional_extractable_source(tmp_path):
    from veritrace.agents.claims import extract_claims
    sentences = ['I downloaded report.pdf.', 'I launched Notepad.', 'I launched Calculator.', 'I opened it.', 'I deleted it.', 'I opened notes.txt.']
    actions = ['download_file', 'launch_program', 'launch_program', 'open_document', 'recycle_file', 'open_document']
    targets = ['report.pdf', 'Notepad', 'Calculator', 'report.pdf', 'report.pdf', 'notes.txt']
    bodies = [batch(*[draft_payload(make_claim(sentences[i], action=actions[i], target=targets[i], claim_id=f'c{i-start}')) for i in range(start,start+3)]) for start in (0,3)]
    text = ' '.join(sentences)
    client = ReplayClient.from_contents(bodies)
    claims = extract_claims(registered(tmp_path, text), client, TestBudget())
    context = json.loads(client.requests[1]['messages'][1]['content'])['preceding_context']
    assert context[0]['target'] == 'report.pdf'
    assert all('sentence' not in item and 'action' not in item and 'negated' not in item for item in context)
    assert [c.target for c in claims] == targets
    assert all(text[c.start:c.end] == c.sentence for c in claims)


def test_repairs_are_limited_to_two_across_the_entire_long_testimony(tmp_path):
    from veritrace.agents.claims import extract_claims
    from veritrace.errors import ModelError
    text, sentences = examples(6)
    good = replies(sentences)
    client = ReplayClient.from_contents([batch(), good[0], batch(), batch()])
    with pytest.raises(ModelError, match='two repairs'):
        extract_claims(registered(tmp_path,text),client,TestBudget())
    assert len(client.requests) == 4


def test_denial_repair_in_a_later_batch_keeps_both_actions_and_global_spans(tmp_path):
    from veritrace.agents.claims import extract_claims
    _, first = examples(3)
    compound = "I downloaded final.pdf but I didn't open it."
    last = [compound, 'I launched Notepad.', 'I deleted final.pdf.']
    download = make_claim(compound, target='final.pdf')
    denied = make_claim(compound, claim_id='denied', action='open_document', target='final.pdf', negated=True)
    remaining = [make_claim(last[1], claim_id='program', action='launch_program', target='Notepad'),
                 make_claim(last[2], claim_id='deleted', action='recycle_file', target='final.pdf')]
    client = ReplayClient.from_contents([
        replies(first)[0], batch(draft_payload(download), *map(draft_payload, remaining)),
        batch(draft_payload(download), draft_payload(denied), *map(draft_payload, remaining)),
    ])
    text = ' '.join(first + last)
    claims = extract_claims(registered(tmp_path, text), client, TestBudget())
    assert len(client.requests) == 3 and len(claims) == 7
    assert len({c.claim_id for c in claims}) == 7
    assert all(text[c.start:c.end] == c.sentence for c in claims)
    assert [(c.action, c.negated) for c in claims[3:5]] == [('download_file', False), ('open_document', True)]
    assert claims[3].start == claims[4].start == text.index(compound)
    assert 'no negated claim covers' in client.requests[-1]['messages'][-1]['content']


def test_uncertainty_in_a_later_batch_stays_with_its_claim(tmp_path):
    from veritrace.agents.claims import NO_RECALL, extract_claims
    _, first = examples(3)
    last = ["I don't remember deleting final.pdf.", 'I opened notes.txt.', 'I launched Notepad.']
    later = [make_claim(last[0], claim_id='memory', action='recycle_file', target='final.pdf', negated=True),
             make_claim(last[1], claim_id='opened', action='open_document', target='notes.txt'),
             make_claim(last[2], claim_id='program', action='launch_program', target='Notepad')]
    client = ReplayClient.from_contents([replies(first)[0], batch(*map(draft_payload, later))])
    text = ' '.join(first + last)
    claims = extract_claims(registered(tmp_path, text), client, TestBudget())
    assert len(claims) == 6 and len(client.requests) == 2
    assert claims[3].negated is False and NO_RECALL in claims[3].uncertainty
    assert all(NO_RECALL not in c.uncertainty for c in claims[:3] + claims[4:])
    assert all(text[c.start:c.end] == c.sentence for c in claims)


def test_repeated_sentences_in_separate_batches_keep_their_own_occurrences(tmp_path):
    from veritrace.agents.claims import extract_claims
    sentence = 'I downloaded résumé.pdf.'
    text = ' '.join([sentence]*6)
    body = batch(*[draft_payload(make_claim(sentence,claim_id=f'c{i}',target='résumé.pdf')) for i in range(3)])
    client = ReplayClient.from_contents([body,body])
    claims = extract_claims(registered(tmp_path,text),client,TestBudget())
    assert [c.start for c in claims] == [i*(len(sentence)+1) for i in range(6)]
    assert len({c.claim_id for c in claims}) == 6


@pytest.mark.parametrize('fragment',['using Edge','using Edge.','pdf using Edge.','I downloaded report.','I downloaded report.pdf using Edge.'])
def test_cropped_source_fragments_are_repaired_to_the_whole_sentence(tmp_path, fragment):
    from veritrace.agents.claims import extract_claims
    text = 'On 28 November 2026, I downloaded report.pdf using Edge.'
    good = make_claim(text, target='report.pdf')
    instrumental = fragment.startswith(('using','pdf using'))
    extra = make_claim(fragment, claim_id='extra', action='launch_program' if instrumental else 'download_file', target='Edge' if instrumental else 'report.pdf')
    client = ReplayClient.from_contents([batch(draft_payload(extra)), batch(draft_payload(good))])
    claims = extract_claims(registered(tmp_path,text),client,TestBudget())
    assert len(client.requests) == 2
    assert len(claims) == 1 and claims[0].sentence == text
    assert 'sentence' in client.requests[1]['messages'][-1]['content']


def test_leading_separator_space_is_allowed_on_a_complete_sentence(tmp_path):
    from veritrace.agents.claims import extract_claims
    text='I launched Notepad. I downloaded report.pdf.'
    sentence=' I downloaded report.pdf.'
    value=make_claim(sentence,target='report.pdf')
    claims=extract_claims(registered(tmp_path,text),ReplayClient.from_contents([batch(draft_payload(value))]),TestBudget())
    assert len(claims)==1 and text[claims[0].start:claims[0].end]==sentence


def test_source_context_is_not_reextracted_by_a_later_batch(tmp_path):
    from veritrace.agents.claims import extract_claims
    text, sentences = examples(6)
    good = replies(sentences)
    old_claim = batch(draft_payload(make_claim(sentences[0], target='report0.pdf')))
    client = ReplayClient.from_contents([good[0],old_claim,good[1]])
    claims = extract_claims(registered(tmp_path,text),client,TestBudget())
    assert len(claims) == 6 and len(client.requests) == 3
    assert len({(c.start,c.end) for c in claims}) == 6


def test_oversized_testimony_is_refused_before_unbounded_model_calls(tmp_path):
    from veritrace.agents.claims import extract_claims
    from veritrace.errors import ModelError
    text,_ = examples(49)
    client=ReplayClient.from_contents([])
    with pytest.raises(ModelError,match='16-batch'):
        extract_claims(registered(tmp_path,text),client,TestBudget())
    assert client.requests==[]
