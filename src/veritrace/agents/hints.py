"""Host-computed starting search for a claim.

A small model copied the example family in the tool description (edge_history) for every claim and
searched the pronoun 'it', so LNK and Recycle Bin records were never queried. Which source family
shows an action, and which word of the claim names the file, are deterministic: compute them here.
"""
import re

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
           "documents", "item", "items", "thing", "things", "my", "our", "your", "of", "on", "in", "to"}


def target_word(target):
    """Longest non-generic word of the claim target, or None (for example for the pronoun 'it')."""
    words = [w for w in re.findall(r"[A-Za-z0-9._-]+", target or "") if w.lower() not in GENERIC]
    return max(words, key=len) if words else None


def parsed_families(coverage):
    return {c.family for c in coverage or [] if c.status == "parsed" and c.record_count}


def search_hint(claim, claims, coverage=None):
    """Suggested first search for this claim. A pronoun target borrows the first named file in the case.
    With coverage, only families that actually produced records are suggested."""
    word = target_word(claim.target)
    if word is None:
        word = next((w for w in (target_word(c.target) for c in claims) if w), None)
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


def resolved_target(claim, claims):
    """The claim's own target, or for a pronoun ('it') the nearest earlier claim's named target, else a later one."""
    if target_word(claim.target):
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
    """Parsed sources in full, everything else as a bare name list, to save context."""
    rows, not_covered = [], []
    for c in coverage:
        if c.status in ("unsupported", "unavailable-in-input"):
            not_covered.append(c.family)
            continue
        row = {"family": c.family, "status": c.status, "records": c.record_count}
        for key, value in (("item_id", c.item_id), ("reason", c.reason), ("error", c.error_code), ("companions", c.companion_handling)):
            if value:
                row[key] = value
        rows.append(row)
    return {"sources": rows, "not_covered": sorted(set(not_covered))}
