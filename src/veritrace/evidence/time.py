from datetime import datetime, timedelta, timezone

from .models import EvidenceTime


def native_time(value, encoding, role):
    normalized, basis, uncertainty = None, None, None
    precision = {"webkit_microseconds": "microsecond", "filetime": "100 nanoseconds", "iso8601": "as represented"}.get(encoding, "unknown")
    try:
        if encoding in ("webkit_microseconds", "filetime") and isinstance(value, int) and not isinstance(value, bool) and value > 0:
            micros = value if encoding == "webkit_microseconds" else value // 10
            normalized = datetime(1601, 1, 1, tzinfo=timezone.utc) + timedelta(microseconds=micros)
            basis = "1601 UTC epoch; declared source field encoding"
            if encoding == "filetime" and value % 10:
                uncertainty = "Python UTC view drops sub-microsecond remainder; raw value retained"
        elif encoding == "iso8601" and isinstance(value, str):
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.utcoffset() is not None:
                normalized, basis = parsed.astimezone(timezone.utc), "Explicit offset in parser value"
            else:
                uncertainty = "No defensible timezone supplied"
        else:
            uncertainty = "Unset or unsupported timestamp encoding/value"
    except (ValueError, OverflowError):
        uncertainty = "Invalid or out-of-range time; raw value retained"
    return EvidenceTime(role=role, raw_value=value, raw_encoding=encoding, raw_precision=precision, normalized_utc=normalized, normalization_basis=basis, uncertainty=uncertainty)
