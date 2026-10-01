import json
import re
from importlib.resources import files

from pydantic import ValidationError

from ..cases.models import FrozenModel
from ..errors import ModelError
from .models import Claim


class ClaimBatch(FrozenModel):
    claims: list[Claim]


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
    schema = compact_schema(ClaimBatch.model_json_schema())
    for attempt in range(3):
        budget.ensure(messages, None, schema)
        turn = client.chat(messages, schema=schema)
        try:
            if turn.tool_calls:
                raise ValueError("Claim interpretation has no tools")
            claims = ClaimBatch.model_validate_json(turn.content).claims
            if not claims and case.testimony.strip():
                raise ValueError("No claims extracted from nonempty testimony")
            ids, interpretations = set(), set()
            for claim in claims:
                if claim.claim_id in ids:
                    raise ValueError("Duplicate claim ID")
                ids.add(claim.claim_id)
                if not (0 <= claim.start < claim.end <= len(case.testimony)) or case.testimony[claim.start:claim.end] != claim.sentence:
                    raise ValueError("Claim text does not match its exact source span")
                identity = (claim.start, claim.end, claim.action, claim.target, claim.negated)
                if identity in interpretations:
                    raise ValueError("Duplicate interpretation of the same source occurrence")
                interpretations.add(identity)
                if not case.manifest.testimony_reference_time and re.search(r"\b(yesterday|today|tomorrow|last|ago)\b", claim.time_expression or "", re.I) and (claim.resolved_start or claim.resolved_end):
                    raise ValueError("Relative testimony time lacks a reference date; keep bounds unresolved")
            return claims
        except (ValueError, ValidationError) as exc:
            if attempt == 2:
                raise ModelError(f"Claim extraction failed after two repairs: {exc}") from exc
            messages.extend([turn.as_assistant_message(), {"role": "user", "content": f"Validation error: {exc}. Return a corrected complete JSON claim batch. Keep the source unchanged."}])
