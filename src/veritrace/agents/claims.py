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

SUPPORTED_ACTIONS = ("download_file", "open_document", "launch_program", "recycle_file")
NEGATION_WORDS = {"never", "not", "no"}
AUXILIARIES = {"do", "did", "does", "have", "has", "had", "is", "was", "were", "been", "be"}
CONTRACTIONS = {word: auxiliary + " not" for auxiliary in ("do", "did", "does", "have", "has", "had", "is", "was", "were")
                for word in (auxiliary + "n't", auxiliary + "nt")}
# Verbs that unambiguously name one supported action. "open" is left out: it could mean a document or a program.
VERB_ACTION = {**{v: "launch_program" for v in ("use", "used", "using", "run", "ran", "running", "execute", "executed", "start", "started", "launch", "launched")},
               **{v: "download_file" for v in ("download", "downloaded", "downloading")},
               **{v: "recycle_file" for v in ("delete", "deleted", "remove", "removed", "trash", "trashed", "recycle", "recycled")}}
ACTION_SUFFIXES = {"download_file": {(), ("file",), ("files",)},
                   "recycle_file": {(), ("file",), ("files",)},
                   "launch_program": {(), ("program",), ("application",), ("app",)},
                   "open_document": {("document",), ("file",)}}
DOCUMENT_TARGET = re.compile(r"\.(?:pdf|docx?|xlsx?|pptx?|txt|rtf|csv|jpe?g|png|gif|bmp|zip|rar|7z)\b", re.I)
ACTION_CUES = {
    "download_file": re.compile(r"\bdownload(?:ed|ing|s)?\b", re.I),
    "open_document": re.compile(r"\b(?:open(?:ed|ing|s)?|read(?:ing)?|view(?:ed|ing|s)?|access(?:ed|ing)?|inspect(?:ed|ing)?|look(?:ed|ing)?\s+at)\b", re.I),
    "launch_program": re.compile(r"\b(?:launch(?:ed|ing)?|start(?:ed|ing)?|execut(?:e|ed|ing)|run|ran|running|use|used|using|open(?:ed|ing|s)?)\b", re.I),
    "recycle_file": re.compile(r"\b(?:delet(?:e|ed|ing)|remov(?:e|ed|ing)|trash(?:ed|ing)?|recycl(?:e|ed|ing)|mov(?:e|ed|ing)\b.*\b(?:recycle\s+bin|trash))\b", re.I),
}


def normalize_action(draft):
    """Canonicalize a single clear action label, preserving polarity and an audit note.

    Do not infer polarity from the whole source sentence: distinct actions can share it.
    Compound/qualified labels involving a supported verb need model repair, not a guess
    based on their first word. Genuinely unsupported activities keep their action names.
    """
    if draft.action.strip().casefold() in PLACEHOLDERS | {"unknown", "unsupported"}:
        raise ValueError("action must name the asserted activity, not a placeholder; use a canonical action for supported activities, preserve actual unsupported activities, and keep denial in negated")
    if draft.action in SUPPORTED_ACTIONS:
        return draft
    words = [part for word in re.split(r"[\s_-]+", draft.action.strip().casefold().replace("\u2019", "'"))
             for part in CONTRACTIONS.get(word, word).split()]
    verbs = VERB_ACTION | {"open": "open_document", "opened": "open_document"}
    positions = [i for i, word in enumerate(words) if word in verbs]
    if not positions:
        return draft
    pos = positions[0]
    action = verbs[words[pos]]
    prefix, suffix = words[:pos], tuple(words[pos + 1:])
    # Bare 'opened' can refer to a program as well as a document. 'used' with a
    # document target is likewise ambiguous; keep the existing coverage behavior.
    if not prefix and not suffix and (action == "open_document" or (action == "launch_program" and DOCUMENT_TARGET.search(draft.target or ""))):
        return draft
    negations = sum(word in NEGATION_WORDS for word in prefix)
    clear_prefix = all(word in AUXILIARIES | NEGATION_WORDS for word in prefix)
    if (len(positions) != 1 or negations > 1 or any(word in {"and", "or", "only"} for word in words)
            or (negations and not clear_prefix) or (prefix and not suffix and action == "open_document")):
        raise ValueError(f"action {draft.action!r} is not a single clear supported action label; use the canonical action and negated flag for each atomic activity, preserving qualification/uncertainty and unsupported activities without guessing")
    if not clear_prefix or suffix not in ACTION_SUFFIXES[action]:
        # E.g. run_sql_query and open_network_port describe other activities.
        # A shared verb alone is not permission to force them into coverage.
        return draft
    if action == "launch_program" and DOCUMENT_TARGET.search(draft.target or ""):
        raise ValueError(f"action {draft.action!r} has an ambiguous document/program target; return the activity actually asserted without guessing")
    negated = bool(negations)
    note = f"The host read the action {draft.action!r} as {action}" + (" with the claim negated" if negated and not draft.negated else "")
    return draft.model_copy(update={"action": action, "negated": draft.negated or negated, "interpretation_notes": [*draft.interpretation_notes, note]})


def validate_activity_scope(draft):
    """Reject known over-splits without treating lexical cues as a semantic proof.

    Cues are used only to reject an absent activity when another supported
    activity is expressed. Unrecognized phrasing needs semantic evaluation;
    absence of every cue does not prove the witness asserted no activity.
    """
    expressed = {action for action, pattern in ACTION_CUES.items() if pattern.search(draft.sentence)}
    if draft.action in SUPPORTED_ACTIONS and expressed and draft.action not in expressed:
        raise ValueError(f"claim {draft.claim_id}: action {draft.action!r} is not expressed in this source sentence; do not infer extra downloading, opening, launching or deletion. Return only the actual asserted activities, preserving their negation and the source sentence")
    if draft.action != "launch_program" or not draft.target:
        return
    sentence = draft.sentence
    # A separate program predicate (including pronoun references) can assert an
    # activity independently. Do not discard it merely because an app is also a means.
    if re.search(r"\b(?:launch(?:ed|ing)?|start(?:ed|ing)?|execut(?:e|ed|ing)|run|ran|running|use|used|(?:am|is|are|was|were|been)\s+using)\b", sentence, re.I):
        return
    mentions = list(re.finditer(r"(?<!\w)" + re.escape(draft.target) + r"(?!\w)", sentence, re.I))
    if not mentions:
        return
    for mention in mentions:
        prefix = sentence[:mention.start()]
        means = re.search(r"\b(?:using|with|in)\s+(?:the\s+)?$", prefix, re.I)
        if means is None:
            return
        clause = re.split(r"[;!?]|\b(?:and|but|while|then)\b", prefix[:means.start()], flags=re.I)[-1]
        if not re.search(r"\b(?:download(?:ed|ing)?|open(?:ed|ing)?|delet(?:e|ed|ing)|recycl(?:e|ed|ing)|remov(?:e|ed|ing))\b", clause, re.I):
            return
    raise ValueError(f"claim {draft.claim_id}: {draft.target!r} is only the means of another activity in this sentence, not a separately asserted program activity. Omit this extra launch_program claim; retain the actual download/open/delete claim with its own negation. Do not change the source sentence")

# --- Denials and hedges, read from the witness's own sentence --------------------------------------------------------
# The model alone decides `negated`; normalize_action only reads negation hidden in an action label. Two failures seen on
# the real model (qwen3:8b, "I downloaded X but I didn't open it." and "I don't remember deleting X."): the second
# activity was silently dropped, and a hedge was recorded as a flat denial. Both are checked here against the sentence.
NO_RECALL = "witness does not remember or is not sure"
NEG_TOKEN = re.compile(r"^(?:never|not|cannot|can't|cant|won't|wont|(?:did|does|do|have|has|had|was|were|is|would|could|should)n'?t)$")
OTHER_NEGATION = {"no", "none", "nothing", "nobody", "neither", "nor", "without", "deny", "denied", "denies", "refuse", "refused",
                  "avoid", "avoided", "refrained", "skipped", "declined"}
FILLERS = {"even", "really", "ever", "once", "actually", "also", "yet", "been", "have", "has", "had", "just", "definitely", "personally", "to"}
HEDGE_WORDS = {"remember", "recall", "recollect", "know", "sure", "certain"}  # "do not think I..." stays a soft denial, as the team decided
SPEECH_WORDS = {"say", "said", "claim", "claimed", "deny", "denied", "admit", "admitted", "state", "stated"}
VERB_FORMS = {**{v: "open" for v in ("open", "opened", "opening", "opens")},
              **{v: "download_file" for v in ("download", "downloaded", "downloading")},
              **{v: "recycle_file" for v in ("delete", "deleted", "deleting", "remove", "removed", "removing", "trash", "trashed", "trashing", "recycle", "recycled", "recycling")},
              **{v: "launch_program" for v in ("use", "used", "using", "run", "ran", "running", "launch", "launched", "launching", "start", "started", "starting", "execute", "executed", "executing")}}


def analyse_sentence(sentence):
    """What a sentence denies, what it only hedges about, and whether it is too convoluted to judge by rule.

    Only the verb right after a negation counts ("did not download", "never opened"). A double negation such as
    "I did not say I never opened it" is left to the model, as the prompt asks.
    """
    tokens = re.findall(r"[a-z]+(?:'[a-z]+)?", sentence.casefold().replace("\u2019", "'"))
    denied, hedged, convoluted = set(), set(), False
    for i, token in enumerate(tokens):
        if not NEG_TOKEN.match(token):
            continue
        j = i + 1
        while j < len(tokens) and tokens[j] in FILLERS:
            j += 1
        if j >= len(tokens):
            continue
        word = tokens[j]
        if word in SPEECH_WORDS:
            convoluted = True
        elif word in HEDGE_WORDS:
            verb = next((tokens[k] for k in range(j + 1, min(j + 7, len(tokens))) if tokens[k] in VERB_FORMS), None)
            if verb:
                hedged.add(VERB_FORMS[verb])
        elif word in VERB_FORMS:
            denied.add(VERB_FORMS[word])
    if convoluted:
        denied, hedged = set(), set()
    has_negation = convoluted or any(NEG_TOKEN.match(t) or t in OTHER_NEGATION for t in tokens)
    return denied, hedged, convoluted, has_negation


def action_matches(claim_action, found):
    """'open' alone could be a document or a program; every other verb names one action."""
    return claim_action in {"open_document", "launch_program"} if found == "open" else claim_action == found


def fix_polarity(draft):
    """Hedges are neither assertions nor denials; a denial flag needs a negation in the sentence."""
    denied, hedged, convoluted, has_negation = analyse_sentence(draft.sentence)
    if convoluted:
        return draft
    if any(action_matches(draft.action, found) for found in hedged):
        note = "The host read the witness as not remembering or being unsure, which is neither a denial nor an assertion; the verdict cannot be supported or contradicted"
        return draft.model_copy(update={"negated": False, "uncertainty": [*draft.uncertainty, *([] if NO_RECALL in draft.uncertainty else [NO_RECALL])],
                                        "interpretation_notes": [*draft.interpretation_notes, note]})
    if draft.negated and not has_negation and draft.action in SUPPORTED_ACTIONS:
        raise ValueError(f"claim {draft.claim_id}: marked as a denial, but the sentence contains no negation; set negated=false for a positive statement, keeping the source sentence unchanged")
    return draft


def require_denials_covered(drafts):
    """A sentence that denies an activity must produce a negated claim for it, or the denial is never assessed."""
    for sentence in dict.fromkeys(d.sentence for d in drafts):
        denied, _, convoluted, _ = analyse_sentence(sentence)
        if convoluted:
            continue
        for found in sorted(denied):
            if not any(d.sentence == sentence and d.negated and action_matches(d.action, found) for d in drafts):
                phrase = {"open": "opening", "download_file": "downloading", "recycle_file": "deleting", "launch_program": "using or launching"}[found]
                raise ValueError(f"the sentence {sentence[:80]!r} denies {phrase} something, but no negated claim covers that activity; add a separate claim for it with negated=true, keeping the source sentence unchanged")


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
            ids, interpretations, claims, normalized = set(), set(), [], []
            for draft in drafts:
                if draft.claim_id in ids:
                    raise ValueError("Duplicate claim ID")
                ids.add(draft.claim_id)
                draft = draft.model_copy(update={"uncertainty": without_placeholders(draft.uncertainty), "interpretation_notes": without_placeholders(draft.interpretation_notes)})
                draft = normalize_action(draft)
                validate_activity_scope(draft)
                draft = fix_polarity(draft)
                normalized.append(draft)
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
            require_denials_covered(normalized)
            return claims
        except (ValueError, ValidationError) as exc:
            if attempt == 2:
                raise ModelError(f"Claim extraction failed after two repairs: {exc}") from exc
            messages.extend([turn.as_assistant_message(), {"role": "user", "content": f"Validation error: {exc}. Return a corrected complete JSON claim batch. Keep the source unchanged."}])
