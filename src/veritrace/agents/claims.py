import json
import re
from importlib.resources import files

from pydantic import ValidationError

from ..cases.models import FrozenModel
from ..errors import ModelError
from .models import ClaimDraft


class DraftBatch(FrozenModel):
    claims: list[ClaimDraft]


def locate(testimony, sentence, occurrence):
    """Exact span of the nth non-overlapping verbatim occurrence of sentence.

    The model only names the sentence; this code derives the character offsets,
    so span preservation never depends on the model counting characters.
    """
    if not sentence:
        raise ValueError("Claim sentence is empty")
    cursor, found = 0, 0
    while found < occurrence:
        start = testimony.find(sentence, cursor)
        if start < 0:
            if found == 0:
                raise ValueError(f"Sentence {sentence[:80]!r} does not appear verbatim in the testimony; copy it exactly, including punctuation and line breaks")
            raise ValueError(f"Sentence {sentence[:80]!r} occurs only {found} time(s); occurrence {occurrence} does not exist")
        found += 1
        cursor = start + len(sentence)
    return start, start + len(sentence)


MONTH = r"(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*"
DATE_HINT = re.compile(rf"\b(?:19|20)\d{{2}}\b|\b\d{{1,2}}[/-]\d{{1,2}}\b|\b\d{{1,2}}(?:st|nd|rd|th)?\s+{MONTH}\b|\b{MONTH}\s+\d{{1,2}}\b", re.I)
NO_DATE_NOTE = "Resolved time bounds dropped: the sentence states no date and the case has no reference time"

PLACEHOLDERS = {"", "-", "none", "n/a", "na", "nil", "null", "no", "not applicable", "no uncertainty"}


def without_placeholders(values):
    """Drop list entries that only say 'nothing here'; they carry no information."""
    return [v for v in values if v.strip().casefold() not in PLACEHOLDERS]


def compact_schema(schema):
    if isinstance(schema, dict):
        return {k: compact_schema(v) for k, v in schema.items() if k not in ("title", "default", "description")}
    if isinstance(schema, list):
        return [compact_schema(v) for v in schema]
    return schema


def load_prompt(name):
    return files("veritrace").joinpath("prompts", name + ".txt").read_text(encoding="utf-8")


def extract_claims(case, client, budget):
    data = {"testimony": case.testimony, "reference_time": case.manifest.testimony_reference_time.isoformat() if case.manifest.testimony_reference_time else None, "source_timezone": case.manifest.source_timezone}
    messages = [{"role": "system", "content": load_prompt("claims")}, {"role": "user", "content": json.dumps(data, ensure_ascii=False, separators=(",", ":"))}]
    schema = compact_schema(DraftBatch.model_json_schema())
    for attempt in range(3):
        budget.ensure(messages, None, schema)
        turn = client.chat(messages, schema=schema)
        try:
            if turn.tool_calls:
                raise ValueError("Claim interpretation has no tools")
            drafts = DraftBatch.model_validate_json(turn.content).claims
            if not drafts and case.testimony.strip():
                raise ValueError("No claims extracted from nonempty testimony")
            ids, interpretations, claims = set(), set(), []
            for draft in drafts:
                if draft.claim_id in ids:
                    raise ValueError("Duplicate claim ID")
                ids.add(draft.claim_id)
                draft = draft.model_copy(update={"uncertainty": without_placeholders(draft.uncertainty), "interpretation_notes": without_placeholders(draft.interpretation_notes)})
                stated = draft.time_expression
                if stated is not None and (not stated.strip() or stated.casefold() not in case.testimony.casefold()):
                    raise ValueError(f"time_expression {stated!r} is not words from the testimony; copy the witness's own words for the time, or use null when no time was stated")
                occurrence = draft.occurrence
                while True:
                    claim = draft.to_claim(*locate(case.testimony, draft.sentence, occurrence))
                    identity = (claim.start, claim.end, claim.action, claim.target, claim.negated)
                    if identity not in interpretations:
                        break
                    # The model repeated an identical claim. If the sentence really does occur
                    # again, it is the next statement, not a duplicate; qwen3:8b ignores repair
                    # messages here, so the host decides instead of asking again.
                    occurrence += 1
                    try:
                        locate(case.testimony, draft.sentence, occurrence)
                    except ValueError:
                        raise ValueError("Duplicate interpretation of the same source occurrence") from None
                interpretations.add(identity)
                if not case.manifest.testimony_reference_time and re.search(r"\b(yesterday|today|tomorrow|last|ago)\b", claim.time_expression or "", re.I) and (claim.resolved_start or claim.resolved_end):
                    raise ValueError("Relative testimony time lacks a reference date; keep bounds unresolved")
                if not case.manifest.testimony_reference_time and (claim.resolved_start or claim.resolved_end) and not DATE_HINT.search(claim.sentence):
                    # Regression: qwen3:8b invented 2023-10-05 for "Around 2 PM". With no date to anchor
                    # on, any bound it supplies is made up, so the host removes it rather than ask again.
                    claim = claim.model_copy(update={"resolved_start": None, "resolved_end": None, "interpretation_notes": [*claim.interpretation_notes, NO_DATE_NOTE]})
                claims.append(claim)
            return claims
        except (ValueError, ValidationError) as exc:
            if attempt == 2:
                raise ModelError(f"Claim extraction failed after two repairs: {exc}") from exc
            messages.extend([turn.as_assistant_message(), {"role": "user", "content": f"Validation error: {exc}. Return a corrected complete JSON claim batch. Keep the source unchanged."}])
