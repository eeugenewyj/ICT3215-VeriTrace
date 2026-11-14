from html.parser import HTMLParser

from tests.factories import make_claim, make_record


class Links(HTMLParser):
    def __init__(self):
        super().__init__()
        self.ids, self.links = set(), []
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if values.get("id"):
            self.ids.add(values["id"])
        if values.get("href"):
            self.links.append(values["href"])


def result():
    import hashlib
    from veritrace.report.models import RunResult
    from veritrace.agents.models import Assessment
    claim, record = make_claim(), make_record()
    return RunResult(run_id="run01", case_id="case01", testimony=claim.sentence, testimony_sha256=hashlib.sha256(claim.sentence.encode()).hexdigest(), status="complete", claims=[claim], assessments=[Assessment(claim_id=claim.claim_id, status="supported", cited_record_ids=[record.record_id], justification="Positive record", alternative_explanations=[], limitations=["Account attribution only"])], records=[record])


def test_report_escapes_case_text_and_all_citation_links_resolve(tmp_path):
    from veritrace.report.render import render_report
    value = result().model_copy(update={"testimony": '<script>alert("x")</script>'})
    html = render_report(value, tmp_path).read_text(encoding="utf-8")
    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html
    parsed = Links()
    parsed.feed(html)
    assert parsed.links
    assert all(link.startswith("#") and link[1:] in parsed.ids for link in parsed.links)


def test_report_refuses_dangling_or_forged_citation(tmp_path):
    import pytest
    from veritrace.report.render import render_report
    from veritrace.errors import CitationError
    value = result().model_copy(update={"records": []})
    with pytest.raises(CitationError):
        render_report(value, tmp_path)
