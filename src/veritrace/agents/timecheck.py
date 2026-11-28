"""Host-side check of a witness's exact clock time against the cited records.

Regression: for "I downloaded the sample image at 5:10 pm" qwen3:8b saw a 16:25 download,
noted the discrepancy and still answered "supported". Comparing clock times is arithmetic, so
plain code does it instead of the model, and a mismatch withholds "supported".
"""
import re
from datetime import date, datetime, time, timedelta
from zoneinfo import ZoneInfo

TIME_TOLERANCE_S = 120
# "about 10 am" is not an exact minute, but a record five hours away is still a conflict. Approximate wording gets a
# wide window; range or direction wording ("between", "before", "sometime") is still left to the model.
APPROX_TOLERANCE_S = 3600

VAGUE = re.compile(r"\b(?:around|about|approx\w*|roughly|sometime|between|before|after|early|late|maybe|or so)\b|~|\w-?ish\b", re.I)
APPROX = re.compile(r"\b(?:around|about|approx\w*|roughly|or so)\b|~|\w-?ish\b", re.I)
RANGE_WORDS = re.compile(r"\b(?:sometime|between|before|after|early|late|maybe)\b", re.I)
CLOCK12 = re.compile(r"\b(1[0-2]|0?[1-9])(?::([0-5]\d))?\s*([ap])\.?m(?![a-z])", re.I)
CLOCK24 = re.compile(r"\b([01]?\d|2[0-3]):([0-5]\d)\b")
MONTHS = {name: number for number,name in enumerate(("jan","feb","mar","apr","may","jun","jul","aug","sep","oct","nov","dec"),1)}
MONTH_NAME = r"(?:January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|Jun|Jul|Aug|Sept|Sep|Oct|Nov|Dec)"
DAY_FIRST = re.compile(rf"\b(\d{{1,2}})(?:st|nd|rd|th)?\s+({MONTH_NAME})\s+(\d{{4}})\b",re.I)
MONTH_FIRST = re.compile(rf"\b({MONTH_NAME})\s+(\d{{1,2}})(?:st|nd|rd|th)?[,]?\s+(\d{{4}})\b",re.I)
ISO_DATE = re.compile(r"\b(\d{4})-(\d{2})-(\d{2})(?=T|\b)")


def stated_date(expression):
    """One unambiguous full date from the witness's own words, never model bounds.

    Numeric day/month ambiguity, relative days and multiple-date scope remain
    unresolved here. This check does not implement general date interpretation.
    """
    dates = set()
    def uncertain(match):
        # Do not turn 'around 15 October' or 'between 15 and 16 October'
        # into an exact date. A qualifier after the date can instead concern
        # its clock time ('on 15 October at about 3 pm').
        return bool(VAGUE.search((expression or "")[:match.start()]))
    try:
        for match in DAY_FIRST.finditer(expression or ""):
            if uncertain(match): return None
            dates.add(date(int(match[3]),MONTHS[match[2][:3].lower()],int(match[1])))
        for match in MONTH_FIRST.finditer(expression or ""):
            if uncertain(match): return None
            dates.add(date(int(match[3]),MONTHS[match[1][:3].lower()],int(match[2])))
        for match in ISO_DATE.finditer(expression or ""):
            if uncertain(match): return None
            dates.add(date(int(match[1]),int(match[2]),int(match[3])))
    except ValueError:
        return None
    return next(iter(dates)) if len(dates)==1 else None


def _clock(expression):
    """Seconds-of-day a clock time in the expression can mean, or None when it holds no clock time."""
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


def claimed_seconds(expression):
    """Seconds-of-day an exact clock time can mean, or None when it is vague or not a clock time."""
    if not expression or VAGUE.search(expression):
        return None
    return _clock(expression)


def approximate_seconds(expression):
    """Like claimed_seconds, for "about 10 am": approximate wording with one clock time. Ranges and directions are not covered."""
    if not expression or not APPROX.search(expression) or RANGE_WORDS.search(expression):
        return None
    return _clock(expression)


def _compare(claim, records, source_timezone, tolerance, *, approximate=False):
    """None when the comparison does not apply; else (matched, record times in the witness's timezone)."""
    wanted = claimed_seconds(claim.time_expression)
    if wanted is None and approximate:
        wanted, tolerance = approximate_seconds(claim.time_expression), APPROX_TOLERANCE_S
    day = stated_date(claim.time_expression)
    if (wanted is None and day is None) or not source_timezone:
        return None
    zone = ZoneInfo(source_timezone)
    local = []
    for record in records:
        times = record.times
        if record.family == "jumplist":
            # Target-file FILETIMEs and birth-object UUID times do not measure
            # the claimed document interaction. Custom lists may have no such time.
            times = [t for t in times if claim.action == "open_document" and t.role == "destlist_entry_modified"]
        local.extend(t.normalized_utc.astimezone(zone) for t in times if t.normalized_utc)
    if not local:
        return None
    for stamp in local:
        if day is not None and wanted is None:
            if stamp.date() == day:
                return True, local
            continue
        seconds = stamp.hour * 3600 + stamp.minute * 60 + stamp.second
        for target in wanted:
            if day is not None:
                at = datetime.combine(day,time(),tzinfo=zone)+timedelta(seconds=target)
                gap = stamp.timestamp()-at.timestamp()
            else:
                gap = (seconds - target + 43200) % 86400 - 43200
            if -tolerance <= gap <= 60 + tolerance:  # the stated minute, plus tolerance either side
                return True, local
    return False, local


def time_conflict(claim, records, source_timezone, tolerance=TIME_TOLERANCE_S):
    """None when the check passes or does not apply; otherwise a sentence explaining the mismatch."""
    result = _compare(claim, records, source_timezone, tolerance, approximate=True)
    if result is None or result[0]:
        return None
    shown = ", ".join(sorted({s.strftime("%Y-%m-%d %H:%M:%S" if stated_date(claim.time_expression) else "%H:%M:%S") for s in result[1]}))
    if stated_date(claim.time_expression) is not None and claimed_seconds(claim.time_expression) is None and approximate_seconds(claim.time_expression) is None:
        return f"the witness stated {claim.time_expression!r}, but the cited record dates/times in {source_timezone} are {shown}; none is on the stated calendar date"
    return f"the witness stated {claim.time_expression!r}, but the cited record times in {source_timezone} are {shown}; none is within {(APPROX_TOLERANCE_S if claimed_seconds(claim.time_expression) is None else tolerance) // 60} minutes"


def time_agrees(claim, records, source_timezone, tolerance=TIME_TOLERANCE_S):
    """True only when the claim has an exact clock time and a cited record time matches it."""
    if claimed_seconds(claim.time_expression) is None:
        return False
    result = _compare(claim, records, source_timezone, tolerance)
    return bool(result and result[0])
