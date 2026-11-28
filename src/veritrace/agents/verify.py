import json

from pydantic import ValidationError

from .. import progress
from ..errors import CitationError, ContextOverflowError, IntegrityError, ModelError, VeriTraceError, WorkflowError
from .claims import NO_RECALL, SUPPORTED_ACTIONS, compact_schema, load_prompt
from .citations import validate_citations
from .context import deduplicate_record_messages
from ..runtime.client import ModelTurn
from .models import Assessment, VerificationResult
from .hints import claim_view, consistency_problem, coverage_view, family_can_show, record_can_show, shows_action, time_contradiction, tool_search_hint
from .timecheck import time_agrees, time_conflict
from .tools import compact_record, model_view, tool_definitions


class VerdictNudge(CitationError):
    """The verdict contradicts the records the model cited. Asked again without re-sending the rejected answer."""


def withheld(assessment, reason):
    """End the claim as inconclusive instead of keeping, or silently flipping, a verdict the cited records contradict."""
    return assessment.model_copy(update={"status": "inconclusive", "justification": f"{assessment.justification} Host check: {reason}, so '{assessment.status}' was withheld.", "limitations": [*assessment.limitations, f"Status changed from {assessment.status} to inconclusive: {reason}"]})


def assessments_cited(tools, case, assessment):
    return [tools.index.get(case.manifest.case_id, rid) for rid in assessment.cited_record_ids]


def compact_correction(case, claim, claims, records, nudge):
    """A small context for asking the model to correct a verdict: no tool transcript, only what it cited."""
    body = {"case_id": case.manifest.case_id, "source_timezone": case.manifest.source_timezone, "claim": claim_view(claim, claims),
            "cited_records": [compact_record(r, case.manifest.source_timezone) for r in records], "your_answer_was_rejected": nudge}
    return [{"role": "system", "content": load_prompt("verify")},
            {"role": "user", "content": json.dumps(body, ensure_ascii=False, separators=(",", ":"))},
            {"role": "user", "content": "Return the assessment JSON for this claim using only the cited records above."}]


def compact_final(case, claim, claims, tools, budget, schema):
    """A small context for the final answer when the whole retrieval transcript does not fit beside the answer schema.

    Regression (held-out PDF run, 4,096 context): an Edge search, a LNK search and a full LNK get_record left no room for
    the answer, and with no earlier verdict to fall back on the claim ended as a context_limit error with no assessment.
    The records the model retrieved are in the ledger, so ask again with only their compact views, most relevant first,
    dropping the last ones until the request fits. Returns (messages, kept, total), or None when not even one fits.
    """
    seen = []
    for entry in tools.ledger.entries:
        if entry.claim_id == claim.claim_id and entry.error is None:
            seen.extend(rid for rid in entry.returned_record_ids if rid not in seen)
    records = [tools.index.get(case.manifest.case_id, rid) for rid in seen]
    records.sort(key=lambda r: not record_can_show(claim, r))  # stable: records that can show the action come first
    zone = case.manifest.source_timezone
    for keep in range(len(records), 0, -1):
        body = {"case_id": case.manifest.case_id, "source_timezone": zone, "claim": claim_view(claim, claims), "retrieved_records": [compact_record(r, zone) for r in records[:keep]]}
        messages = [{"role": "system", "content": load_prompt("verify")},
                    {"role": "user", "content": json.dumps(body, ensure_ascii=False, separators=(",", ":"))},
                    {"role": "user", "content": "Retrieval is finished. Return the assessment JSON for this claim using only the retrieved records above."}]
        try:
            budget.ensure(messages, None, schema)
        except ContextOverflowError:
            continue
        return messages, keep, len(records)
    return None


def call_key(call):
    function = call.get("function", {})
    return function.get("name", ""), json.dumps(function.get("arguments", {}), sort_keys=True, default=str)


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
        progress.tool_call(name, args, result)
        responses.append({"role": "tool", "tool_name": name, "content": json.dumps(model_view(name, result, source_timezone=tools.case.manifest.source_timezone), ensure_ascii=False, separators=(",", ":"))})
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
    progress.evidence_available(tools.coverage)
    assessments, errors = [], {}
    # extract_case already ran; leaving its definition out saves context the small model needs.
    definitions = tool_definitions(case.manifest.case_id, ["search_records", "get_record", "get_source_coverage"])
    schema = compact_schema(Assessment.model_json_schema())
    for claim in claims:
        if claim.action not in SUPPORTED_ACTIONS:
            progress.out_of_coverage(claim)
            # Regression (Prefetch review): the model searched, found Notepad had run 12 times, answered
            # 'contradicted', and the host rejected that twice, so the claim ended as an error with no
            # assessment. The prototype cannot verify this action; say so instead of asking a model.
            assessments.append(Assessment(claim_id=claim.claim_id, status="unverified", cited_record_ids=[], justification=f"The claimed action '{claim.action}' is outside what this prototype can verify, so no evidence was searched for it.", alternative_explanations=[], limitations=["Action outside prototype coverage; a missing assessment is not evidence that the action did or did not occur"]))
            continue
        hint = tool_search_hint(case.manifest.case_id, claim, claims, tools.coverage)
        progress.claim_started(claim, hint)
        messages = [{"role": "system", "content": load_prompt("verify")}, {"role": "user", "content": json.dumps({"case_id": case.manifest.case_id, "source_timezone": case.manifest.source_timezone, "claim": claim_view(claim, claims), "search_hint": hint, "coverage": coverage_view(tools.coverage)}, ensure_ascii=False, separators=(",", ":"))}]
        count, repairs, missing_search, stopped_early, made = 0, 0, 0, None, set()
        compacted = None
        held, final_next, nudge, first_status = None, False, None, None
        try:
            while True:
                # Native tool syntax must remain unconstrained by the final JSON grammar.
                searched = any(r.claim_id == claim.claim_id and r.name == "search_records" and r.error is None for r in tools.ledger.entries)
                try:
                    if final_next:
                        # A correction needs no more retrieval; going straight to the answer saves a request.
                        final_next, turn = False, ModelTurn(content="")
                    else:
                        budget.ensure(messages, definitions, None)
                        turn = client.chat(messages, tools=definitions)
                except ContextOverflowError:
                    # Regression: qwen3:8b kept searching other families after it had its evidence, the next request
                    # no longer fit 4,096 tokens, and the whole claim failed. With a search already done, stop
                    # retrieving and assess from what was found (the final turn omits the tool definitions).
                    if not searched:
                        raise
                    stopped_early = "the model context budget was reached"
                    progress.host("retrieval stopped because the model context budget was reached; assessing from what was found")
                    turn = ModelTurn(content="")
                if turn.tool_calls and searched and all(call_key(c) in made for c in turn.tool_calls):
                    # Regression (acquired run): the model repeated one identical search twelve times and never
                    # answered. An identical call returns identical records, so stop retrieving and assess.
                    stopped_early = "the model repeated a search it had already made"
                    progress.host("the model repeated a search it had already made; no further retrieval, assessing from what was found")
                    turn = ModelTurn(content="")
                if turn.tool_calls:
                    made.update(call_key(c) for c in turn.tool_calls)
                    if count + len(turn.tool_calls) > 12:
                        raise WorkflowError("Twelve tool calls exhausted for this claim")
                    count += len(turn.tool_calls)
                    messages.extend([turn.as_assistant_message(), *execute_request(turn, tools, claim_id=claim.claim_id)])
                    tools.context_compactions += deduplicate_record_messages(messages)
                    continue
                if not any(r.claim_id == claim.claim_id and r.name == "search_records" and r.error is None for r in tools.ledger.entries):
                    if missing_search == 2:
                        raise WorkflowError("No successful evidence search for this claim after two corrections")
                    missing_search += 1
                    messages.append({"role": "user", "content": "Search the registered case evidence before finalizing this claim, even if the search returns no records."})
                    continue
                # Keep the retrieval context; request schema-only output in a separate turn.
                final_messages = [*messages, {"role": "user", "content": "Retrieval is finished. Return the assessment JSON for this claim using only the evidence returned above."}]
                try:
                    budget.ensure(final_messages, None, schema)
                except ContextOverflowError:
                    if held is None:
                        # Nothing to correct yet, so the transcript itself does not fit: answer from the retrieved records alone.
                        fitted = compact_final(case, claim, claims, tools, budget, schema)
                        if fitted is None:
                            raise
                        final_messages, kept, total = fitted
                        progress.host("the full retrieval transcript did not fit the model context; asking again with a compact view of the retrieved records")
                        compacted = f"the full retrieval transcript did not fit the model context, so the answer was assessed from a compact view of {kept} of {total} retrieved records"
                    else:
                        # Regression (run 26, 4,096 context): the correction request did not fit beside the whole search
                        # transcript. Ask again with only the claim and the records the model itself cited.
                        final_messages = compact_correction(case, claim, claims, assessments_cited(tools, case, held), nudge)
                        try:
                            budget.ensure(final_messages, None, schema)
                        except ContextOverflowError:
                            assessments.append(withheld(held, "the model context budget was reached before it could be asked to correct the verdict"))
                            break
                turn = client.chat(final_messages, schema=schema)
                if turn.tool_calls:
                    raise ModelError("Final assessment returned tool calls instead of JSON")
                try:
                    assessment = Assessment.model_validate_json(turn.content)
                    if assessment.claim_id != claim.claim_id:
                        raise CitationError("Assessment does not match this claim")
                    if claim.action not in ("download_file", "open_document", "launch_program", "recycle_file") and assessment.status in ("supported", "contradicted"):
                        raise CitationError("Action outside prototype coverage cannot receive a positive assessment")
                    validate_citations(case, assessment, tools.index, tools.ledger)
                    progress.draft_verdict(assessment)
                    if assessment.status in ("supported", "contradicted"):
                        cited = [tools.index.get(case.manifest.case_id, rid) for rid in assessment.cited_record_ids]
                        if not family_can_show(claim, cited):
                            kinds = ", ".join(sorted({r.family for r in cited}))
                            retrieved = [tools.index.get(case.manifest.case_id, rid) for rid in sorted(tools.ledger.returned_ids(claim.claim_id))]
                            usable = sorted({r.family for r in retrieved if record_can_show(claim, r)})
                            if usable and repairs < 2:
                                # The right records were retrieved but not cited; ask once more before withholding.
                                held = assessment
                                raise VerdictNudge(f"The cited {kinds} records cannot show this action. Records you already retrieved from {', '.join(usable)} can; cite those if they support or contradict the claim, otherwise answer unverified")
                            progress.host(f"the cited {kinds} records cannot show this action, so '{assessment.status}' was withheld")
                            assessment = assessment.model_copy(update={"status": "unverified", "justification": f"{assessment.justification} Host check: the cited records ({kinds}) cannot show this action, so '{assessment.status}' was withheld.", "limitations": [*assessment.limitations, f"Status changed from {assessment.status} to unverified: no cited record is from a source that can show this action"]})
                    problem = consistency_problem(claim, assessment.status)
                    if problem:
                        # Regression (run on false testimony): qwen3:8b answered 'supported' for "I never downloaded X"
                        # while citing the download record, and 'unverified' while citing a record that showed the action.
                        cited = [tools.index.get(case.manifest.case_id, rid) for rid in assessment.cited_record_ids]
                        if any(shows_action(claim, r, claims, case.manifest.source_timezone) for r in cited):
                            if repairs < 2:
                                held = assessment
                                raise VerdictNudge(problem)
                            progress.host("the cited records show the action, which does not fit that verdict, so it was withheld")
                            assessment = withheld(assessment, "the cited records show the action, which does not fit that verdict")
                    if assessment.status == "supported":
                        cited = [tools.index.get(case.manifest.case_id, rid) for rid in assessment.cited_record_ids]
                        problem = time_conflict(claim, cited, case.manifest.source_timezone)
                        if problem:
                            contradiction = time_contradiction(claim, claims, cited, tools.index, case.manifest.case_id, case.manifest.source_timezone)
                            if contradiction:
                                progress.host(f"time check - {progress.short(contradiction, 220)}; 'supported' changed to 'contradicted'")
                                assessment = assessment.model_copy(update={"status": "contradicted", "justification": f"Host time check: {contradiction}, so 'supported' was changed to 'contradicted'. The model's own reasoning, written before this check and unreliable on clock times, follows: {assessment.justification}", "limitations": [*assessment.limitations, "Status changed from supported to contradicted by the host time check: the records show this action only at other times; sources not supplied (for example a database -wal file) were not searched"]})
                            else:
                                progress.host(f"time check - {progress.short(problem, 220)}; 'supported' withheld")
                                assessment = assessment.model_copy(update={"status": "inconclusive", "justification": f"{assessment.justification} Host time check: {problem}, so 'supported' was withheld.", "limitations": [*assessment.limitations, "Status changed from supported to inconclusive by the host time check"]})
                    if assessment.status == "contradicted" and not claim.negated:
                        cited = [tools.index.get(case.manifest.case_id, rid) for rid in assessment.cited_record_ids]
                        if time_agrees(claim, cited, case.manifest.source_timezone):
                            progress.host("a cited record's time matches the stated time, so 'contradicted' was withheld")
                            assessment = assessment.model_copy(update={"status": "inconclusive", "justification": f"{assessment.justification} Host check: a cited record's time matches the witness's stated time, so 'contradicted' was withheld.", "limitations": [*assessment.limitations, "Status changed from contradicted to inconclusive by the host time check"]})
                    if NO_RECALL in claim.uncertainty and assessment.status in ("supported", "contradicted"):
                        progress.host("the witness only said they do not remember or are not sure, so the records cannot support or contradict it; withheld")
                        assessment = withheld(assessment, "the witness only said they do not remember or are not sure, so a record of the activity neither supports nor contradicts the statement")
                    if first_status and assessment.status != first_status and not any(l.startswith("Status changed") for l in assessment.limitations):
                        assessment = assessment.model_copy(update={"limitations": [*assessment.limitations, f"Revised after a host check: the model's first answer was '{first_status}', which did not fit the records it cited"]})
                    if stopped_early:
                        assessment = assessment.model_copy(update={"limitations": [*assessment.limitations, f"Retrieval stopped early because {stopped_early}; assessed from the records retrieved so far"]})
                    if compacted:
                        assessment = assessment.model_copy(update={"limitations": [*assessment.limitations, f"Assessed from a reduced view: {compacted}"]})
                    assessments.append(assessment)
                    break
                except VerdictNudge as exc:
                    # Drop the rejected answer (~450 tokens at 4,096 context) and say only what is wrong with it.
                    repairs += 1
                    nudge, first_status = str(exc), first_status or held.status
                    progress.host(f"the answer '{held.status}' did not fit the records it cited; asking the model again ({progress.short(exc, 140)})")
                    messages.append({"role": "user", "content": f"Your answer was rejected: {exc}"})
                    final_next = True
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
