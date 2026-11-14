import re
from importlib.resources import files

from jinja2 import Environment, select_autoescape

from ..errors import CitationError


def render_report(result, output_dir):
    records = {r.record_id: r for r in result.records}
    for assessment in result.assessments:
        for record_id in assessment.cited_record_ids:
            if not re.fullmatch(r"[0-9a-f]{64}", record_id) or record_id not in records or records[record_id].case_id != result.case_id:
                raise CitationError("Report citation cannot resolve to this case")
    template = files("veritrace").joinpath("report", "templates", "report.html").read_text(encoding="utf-8")
    environment = Environment(autoescape=select_autoescape(default_for_string=True))
    html = environment.from_string(template).render(result=result, assessment_by_id={a.claim_id: a for a in result.assessments})
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / "report.html"
    path.write_text(html, encoding="utf-8")
    return path
