import json

from pydantic import ValidationError

from ..errors import CitationError, IntegrityError, ModelError, VeriTraceError, WorkflowError
from .claims import compact_schema, load_prompt
from .citations import validate_citations
from .models import Assessment, VerificationResult
from .tools import tool_definitions


def execute_request(turn, tools, *, claim_id):
    responses = []
    for call in turn.tool_calls:
        function = call.get("function", {})
        name, args = function.get("name", ""), function.get("arguments", {})
        try:
            result = tools.dispatch(name, args, claim_id=claim_id)
        except IntegrityError:
            raise
        except VeriTraceError as exc:
            result = {"error": {"code": exc.code, "message": str(exc)}}
        responses.append({"role": "tool", "tool_name": name, "content": json.dumps(result, ensure_ascii=False, separators=(",", ":"))})
    return responses


def require_extraction(case, client, budget, tools):
    definitions = tool_definitions(case.manifest.case_id, ["extract_case"])
    messages = [{"role": "system", "content": "Call extract_case for the registered case before any assessment. Only a real host tool call satisfies this step."}, {"role": "user", "content": case.manifest.case_id}]
    for attempt in range(2):
        budget.ensure(messages, definitions, None)
        turn = client.chat(messages, tools=definitions)
        if len(turn.tool_calls) == 1 and turn.tool_calls[0].get("function", {}).get("name") == "extract_case":
            responses = execute_request(turn, tools, claim_id=None)
            if tools.extracted:
                return
            messages.extend([turn.as_assistant_message(), *responses])
        else:
            messages.extend([{"role": "user", "content": "Required extraction call missing or invalid. Request exactly one extract_case with this case ID."}])
    raise WorkflowError("Model failed to request and execute required extraction after one correction")


def verify_claims(case, claims, client, budget, tools):
    require_extraction(case, client, budget, tools)
    assessments, errors = [], {}
    definitions = tool_definitions(case.manifest.case_id)
    schema = compact_schema(Assessment.model_json_schema())
    for claim in claims:
        messages = [{"role": "system", "content": load_prompt("verify")}, {"role": "user", "content": json.dumps({"case_id": case.manifest.case_id, "claim": claim.model_dump(mode="json"), "coverage": [c.model_dump(mode="json") for c in tools.coverage]}, ensure_ascii=False, separators=(",", ":"))}]
        count, repairs = 0, 0
        try:
            while True:
                budget.ensure(messages, definitions, schema)
                turn = client.chat(messages, tools=definitions, schema=schema)
                if turn.tool_calls:
                    if count + len(turn.tool_calls) > 12:
                        raise WorkflowError("Twelve tool calls exhausted for this claim")
                    count += len(turn.tool_calls)
                    messages.extend([turn.as_assistant_message(), *execute_request(turn, tools, claim_id=claim.claim_id)])
                    continue
                try:
                    assessment = Assessment.model_validate_json(turn.content)
                    if assessment.claim_id != claim.claim_id:
                        raise CitationError("Assessment does not match this claim")
                    if claim.action not in ("download_file", "open_document", "launch_program", "recycle_file") and assessment.status in ("supported", "contradicted"):
                        raise CitationError("Action outside prototype coverage cannot receive a positive assessment")
                    validate_citations(case, assessment, tools.index, tools.ledger)
                    assessments.append(assessment)
                    break
                except (ValueError, ValidationError, CitationError) as exc:
                    if repairs == 2:
                        raise ModelError(f"Assessment invalid after two repairs: {exc}") from exc
                    repairs += 1
                    messages.extend([turn.as_assistant_message(), {"role": "user", "content": f"Validation failed: {exc}. Return a corrected assessment or retrieve appropriate records. Absence alone never contradicts."}])
        except IntegrityError:
            raise
        except VeriTraceError as exc:
            errors[claim.claim_id] = {"code": exc.code, "message": str(exc)}
    return VerificationResult(assessments=assessments, claim_errors=errors)
