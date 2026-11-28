"""Host-computed starting search for a claim.

A small model copied the example family in the tool description (edge_history) for every claim and
searched the pronoun 'it', so LNK and Recycle Bin records were never queried. Which source family
shows an action, and which word of the claim names the file, are deterministic: compute them here.
"""
import re

from ..settings import FAMILIES as SOURCE_FAMILIES
from .timecheck import claimed_seconds, time_agrees, time_conflict

# action -> evidence families that can show it, most direct first
FAMILIES = {
    "download_file": ["edge_history"],
    "open_document": ["lnk", "jumplist", "edge_history"],
    "launch_program": ["prefetch", "userassist"],
    "recycle_file": ["recyclebin"],
}

# Words that name a kind of thing rather than a particular file
GENERIC = {"a", "an", "the", "it", "its", "this", "that", "these", "those", "them", "they", "one", "ones",
           "file", "files", "image", "images", "picture", "pictures", "photo", "photos", "document",
           "documents", "item", "items", "thing", "things", "my", "our", "your", "of", "on", "in", "to",
           "program", "programs", "application", "applications", "app", "apps", "software", "tool", "executable", "something", "anything"}
PRONOUN_TARGETS = {"it", "its", "this", "that", "these", "those", "them", "they"}


def target_word(target):
    """Longest non-generic word of the claim target, or None (for example for the pronoun 'it')."""
    words = [w for w in re.findall(r"[A-Za-z0-9._-]+", target or "") if w.lower() not in GENERIC]
    return max(words, key=len) if words else None


def record_can_show(claim, record):
    """Can this one record evidence the claimed action? Unknown actions are not judged.
    Regression (acquired run, claim 'I opened it'): the model cited an Edge page visit and the Edge download
    row, neither of which shows the file being opened (the download row even says opened=0), and left out the
    LNK record that does. A browser record shows opening only when the browser itself flags it as opened."""
    families = FAMILIES.get(claim.action)
    if not families:
        return True
    if record.family not in families:
        return False
    if claim.action == "open_document" and record.family == "edge_history":
        return str(record.raw_fields.get("opened")) in ("1", "True", "true")
    return True


def family_can_show(claim, records):
    """False when the action is known and none of the records can show it. A Recycle Bin record cited for
    'I never opened X' produced 'contradicted' in an acquired run; a deletion record says nothing about opening."""
    return not FAMILIES.get(claim.action) or any(record_can_show(claim, r) for r in records)


DOWNLOAD_ROLES = {"download_started", "download_completed"}


def shows_action(claim, record, claims, source_timezone):
    """Does this record show the claimed action on the claim's target (and at its stated clock time, if exact)?
    Stricter than record_can_show: a page visit does not show a download, and a record for another file shows
    nothing about this one. Used only to catch a verdict that contradicts the record the model itself cited."""
    if not record_can_show(claim, record):
        return False
    word = target_word(resolved_target(claim, claims))
    if word and word.lower() not in (record.target or "").lower():
        return False
    if claim.action == "download_file" and not any(t.role in DOWNLOAD_ROLES for t in record.times):
        return False
    if claimed_seconds(claim.time_expression) is not None and not time_agrees(claim, [record], source_timezone):
        return False
    if time_conflict(claim, [record], source_timezone):
        return False
    return True


def consistency_problem(claim, status):
    """What is wrong with this status, given that a cited record shows the action. None when nothing is."""
    if claim.negated and status == "supported":
        return "This claim is a denial, and the cited records show the action did happen. A denial cannot be 'supported' by that. Answer contradicted if the records match the claim's target and time, otherwise inconclusive."
    if status == "unverified":
        verdict = "contradicted (the claim is a denial)" if claim.negated else "supported"
        return f"You cited a record that shows this action on this target, so 'unverified' (no relevant evidence) is wrong. Answer {verdict}, or inconclusive if a limit prevents it."
    return None


def parsed_families(coverage):
    return {c.family for c in coverage or [] if c.status == "parsed" and c.record_count}


def search_hint(claim, claims, coverage=None):
    """Suggested first search; explicit pronouns use the same nearest reference as claim_view.
    Generic/unknown targets do not inherit a filename. With coverage, only families
    that actually produced records are suggested."""
    word = target_word(claim.target)
    if word is None and (claim.target or "").strip().casefold() in PRONOUN_TARGETS:
        word = target_word(resolved_target(claim, claims))
    families = FAMILIES.get(claim.action, [])
    if coverage is not None:
        have = parsed_families(coverage)
        families = [f for f in families if f in have]
    if not families and word is None:
        return None
    hint = {}
    if families:
        hint["family"] = families[0]
        if len(families) > 1:
            hint["then_try_families"] = families[1:]
    if word:
        hint["target"] = word
    hint["limit"] = 5
    return hint


def tool_search_hint(case_id, claim, claims, coverage=None):
    """Show the model an actual call envelope, not filters at the argument root."""
    hint = search_hint(claim, claims, coverage)
    if hint is None:
        return None
    filters = {key: hint[key] for key in ("family", "target") if key in hint}
    proposal = {"name": "search_records", "arguments": {"case_id": case_id, "filters": filters, "limit": hint["limit"]}}
    if hint.get("then_try_families"):
        proposal["then_try_families"] = hint["then_try_families"]
    return proposal


def resolved_target(claim, claims):
    """The claim's own target, or for a pronoun ('it') the nearest earlier claim's named target, else a later one."""
    if target_word(claim.target):
        return claim.target
    if (claim.target or "").strip().casefold() not in PRONOUN_TARGETS:
        return claim.target
    ordered = list(claims)
    index = next((i for i, c in enumerate(ordered) if c.claim_id == claim.claim_id), len(ordered))
    for other in [*reversed(ordered[:index]), *ordered[index + 1:]]:
        if target_word(other.target):
            return other.target
    return claim.target


def claim_view(claim, claims=()):
    """The claim as the model needs it. The source sentence is left out: it is often a compound sentence
    shared by several claims (qwen3:8b judged the 'deleted' claim against the 'opened' clause of it), and
    the character span is only for the report. A pronoun target is replaced by the file it refers to,
    because the model took 'it' literally and found it 'not in the evidence'."""
    data = claim.model_dump(mode="json", exclude={"sentence", "start", "end"})
    data["target"] = resolved_target(claim, claims)
    return {k: v for k, v in data.items() if v not in (None, [], "") or k == "negated"}


def coverage_view(coverage):
    """Bound model context by family count, never by the number of input files.

    Status counts include family-level markers (whose item_id is absent); items
    counts only actual supplied files. Undeclared families share an 'other' row.
    Full per-item diagnostics remain in coverage.json and extraction receipts.
    """
    groups, other_families = {}, set()
    for c in coverage:
        family = c.family if c.family in SOURCE_FAMILIES else "other"
        if family == "other":
            other_families.add(c.family)
        row = groups.setdefault(family, {"family": family, "items": 0, "records": 0, "statuses": {}})
        row["items"] += c.item_id is not None
        row["records"] += c.record_count
        row["statuses"][c.status] = row["statuses"].get(c.status, 0) + 1
    rows = []
    for family in (*SOURCE_FAMILIES, "other"):
        if family in groups:
            row = groups[family]
            row["statuses"] = dict(sorted(row["statuses"].items()))
            if family == "other":
                row["family_count"] = len(other_families)
            rows.append(row)
    return {"families": rows, "detail_tool": "get_source_coverage"}
