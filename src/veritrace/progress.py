"""Live narration for an analyst waiting on a run.

Everything here goes to stderr, so stdout keeps the JSON summary that scripts read. It only describes what the
pipeline already did (claims found, searches made, host checks that fired); it never decides anything. The model's
own hidden reasoning is not shown, because it is not reliably available; its tool calls and answers are.
"""
import sys
import textwrap
from pathlib import Path

ENABLED = True  # the evaluate command runs many cases and switches this off
WIDTH = 100

WARNING = ("Final warning: these verdicts come from a language model and host-side checks. They are not final. "
           "They exist to make cross-referencing digital artefacts quicker. Check every cited record against the "
           "original evidence before relying on any verdict.")


def say(text="", indent=0):
    if not ENABLED:
        return
    pad = " " * indent
    for line in str(text).splitlines() or [""]:
        if not line.strip():
            print("", file=sys.stderr)
            continue
        print(textwrap.fill(line, WIDTH, initial_indent=pad, subsequent_indent=pad + "  ", break_long_words=False, break_on_hyphens=False), file=sys.stderr, flush=True)


def short(value, limit=90):
    value = " ".join(str(value).split())
    return value if len(value) <= limit else value[:limit - 3] + "..."


def case_started(case):
    say()
    say(f"VeriTrace run for case {case.manifest.case_id}")
    say("Testimony in question:")
    say(case.testimony.strip(), indent=2)
    say()
    say("Now moving on to Agent 1 to extract the claims made in the testimony...")


def claims_extracted(claims):
    say(f"Agent 1 extracted {len(claims)} claim(s):")
    for claim in claims:
        say(f'Claim {claim.claim_id}: "{short(claim.sentence, 160)}"', indent=2)
        facts = [f"action: {claim.action}", f"target: {claim.target or 'none named'}", f"time: {claim.time_expression or 'none stated'}", f"denial: {'yes' if claim.negated else 'no'}"]
        say(" | ".join(facts), indent=4)
        for note in claim.interpretation_notes:
            say(f"note: {note}", indent=4)
    say()
    say("These claims will now be passed to Agent 2.")


def evidence_available(coverage):
    parsed = [f"{c.family} ({c.record_count} record(s))" for c in coverage if c.status == "parsed" and c.record_count]
    say()
    say("Evidence parsed and searchable: " + (", ".join(parsed) if parsed else "none"))
    problems = [f"{c.family}: {c.status}" for c in coverage if c.status in ("failed", "parsed-with-no-records")]
    if problems:
        say("Not usable: " + ", ".join(problems))


def claim_started(claim, hint):
    say()
    say(f"Agent 2 is assessing claim {claim.claim_id} ({claim.action} -> {claim.target or 'no target'})...")
    families = [hint["arguments"]["filters"].get("family")] + hint.get("then_try_families", []) if hint else []
    families = [f for f in families if f]
    if families:
        say("Artefact families that can show this action: " + ", ".join(families), indent=2)


def out_of_coverage(claim):
    say(f"Claim {claim.claim_id}: the action '{claim.action}' is outside what this prototype can verify, so no model was asked.", indent=2)


def tool_call(name, args, result):
    """One line per search or fetch Agent 2 makes, plus the records it got back."""
    try:
        if isinstance(result, dict) and result.get("error"):
            say(f"{name}: error - {short(result['error'].get('message', ''), 120)}", indent=2)
            return
        if name == "search_records":
            filters = {k: v for k, v in (args.get("filters") or {}).items() if v not in (None, "")}
            asked = ", ".join(f"{k}={short(v, 40)}" for k, v in filters.items()) or "no filters"
            records = result.get("records", [])
            say(f"search_records ({asked}) -> {result.get('total', len(records))} match(es)", indent=2)
            for record in records[:5]:
                times = record.get("times") or []
                when = f" @ {times[0].get('local') or times[0].get('utc')} ({times[0].get('role')})" if times else ""
                say(f"- {record.get('family')}: {short(record.get('target'), 70)}{when}", indent=4)
        elif name == "get_record":
            say(f"get_record -> {result.get('family')}: {short(result.get('target'), 80)}", indent=2)
        elif name == "get_source_coverage":
            say("get_source_coverage -> checked which sources were parsed", indent=2)
    except Exception:  # narration must never break a run
        say(f"{name} done", indent=2)


def draft_verdict(assessment):
    say(f"Agent 2's own answer: {assessment.status} (cites {len(assessment.cited_record_ids)} record(s))", indent=2)


def host(text):
    say(f"Host check: {text}", indent=2)


def final(result):
    """The readable end of the run: verdict, reasoning, which records support it, and where to look next."""
    by_id = {a.claim_id: a for a in result.assessments}
    records = {r.record_id: r for r in result.records}
    say()
    say("=" * 60)
    say("Final verdicts")
    for claim in result.claims:
        say()
        say(f'Claim {claim.claim_id}: "{short(claim.sentence, 160)}"')
        assessment = by_id.get(claim.claim_id)
        if assessment is None:
            error = result.claim_errors.get(claim.claim_id, {})
            say(f"No verdict: {error.get('code', 'unknown')} - {error.get('message', 'the claim was not assessed')}", indent=2)
            continue
        say(f"Final LLM verdict: {assessment.status.upper()}", indent=2)
        say(f"Reasoning: {assessment.justification}", indent=2)
        cited = [records[r] for r in assessment.cited_record_ids if r in records]
        if cited:
            say("Cited records:", indent=2)
            for record in cited:
                say(f"- {record.family}: {short(record.target, 80)} (from {record.original_path or 'unknown source'})", indent=4)
        changed = [l for l in assessment.limitations if l.startswith(("Status changed", "Revised after", "Retrieval stopped", "Assessed from a reduced view"))]
        if changed:
            say("Where the host changed or limited the model's answer:", indent=2)
            for line in changed:
                say(f"- {line}", indent=4)
        others = [l for l in assessment.limitations if l not in changed]
        if others:
            say("Limitations:", indent=2)
            for line in others:
                say(f"- {line}", indent=4)
    for error in result.errors:
        say(f"Run error: {error.get('code')} - {error.get('message')}")
    report = result.output_paths.get("report.html")
    if report:
        folder = Path(report).parent
        say()
        say("Where to look for more detail:")
        say(f"- Full report: {report}", indent=2)
        say(f"- Every search the model made: {folder / 'tool_calls.jsonl'}", indent=2)
        say(f"- Parsed evidence database: {folder / 'evidence.sqlite'}", indent=2)
        say(f"- Raw parser output: {folder / 'raw'}", indent=2)
    seconds = (result.runtime_metadata or {}).get("duration_s")
    if seconds is not None:
        say(f"Run time: {seconds:.0f} s", indent=0)


def warning():
    say()
    say(WARNING)
