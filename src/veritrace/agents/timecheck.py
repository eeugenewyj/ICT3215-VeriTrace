"""Host-side check of a witness's exact clock time against the cited records.

Regression: for "I downloaded the sample image at 5:10 pm" qwen3:8b saw a 16:25 download,
noted the discrepancy and still answered "supported". Comparing clock times is arithmetic, so
plain code does it instead of the model, and a mismatch withholds "supported".
"""
import re
from zoneinfo import ZoneInfo

TIME_TOLERANCE_S = 120

VAGUE = re.compile(r"\b(?:around|about|approx\w*|roughly|sometime|between|before|after|early|late|maybe|or so)\b|~|\w-?ish\b", re.I)
CLOCK12 = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m(?![a-z])", re.I)
CLOCK24 = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")


def claimed_seconds(expression):
    """Seconds-of-day an exact clock time can mean, or None when it is vague or not a clock time."""
    if not expression or VAGUE.search(expression):
        return None
    match = CLOCK12.search(expression)
    if match:
        hour = int(match[1]) % 12 + (12 if match[3].lower() == "p" else 0)
        return {hour * 3600 + int(match[2] or 0) * 60}
    match = CLOCK24.search(expression)
    if match:
        hour, minute = int(match[1]), int(match[2])
        hours = {hour, hour + 12} if 1 <= hour <= 11 else {hour}  # "4:25" with no am/pm could be either
        return {h * 3600 + minute * 60 for h in hours}
    return None


def time_conflict(claim, records, source_timezone, tolerance=TIME_TOLERANCE_S):
    """None when the check passes or does not apply; otherwise a sentence explaining the mismatch."""
    wanted = claimed_seconds(claim.time_expression)
    if wanted is None or not source_timezone:  # without the witness's timezone a clock time cannot be compared
        return None
    zone = ZoneInfo(source_timezone)
    local = [t.normalized_utc.astimezone(zone) for r in records for t in r.times if t.normalized_utc]
    if not local:
        return None
    for stamp in local:
        seconds = stamp.hour * 3600 + stamp.minute * 60 + stamp.second
        for target in wanted:
            gap = (seconds - target + 43200) % 86400 - 43200
            if -tolerance <= gap <= 60 + tolerance:  # the stated minute, plus tolerance either side
                return None
    shown = ", ".join(sorted({s.strftime("%H:%M:%S") for s in local}))
    return f"the witness stated {claim.time_expression!r}, but the cited record times in {source_timezone} are {shown}; none is within {tolerance // 60} minutes"
