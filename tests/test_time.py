def test_native_epoch_and_unset_time():
    from veritrace.evidence.time import native_time
    value = native_time(11644473600000000, "webkit_microseconds", "visit_time")
    assert value.normalized_utc.isoformat() == "1970-01-01T00:00:00+00:00"
    unset = native_time(0, "webkit_microseconds", "visit_time")
    assert unset.normalized_utc is None


def test_naive_iso_stays_unknown_and_filetime_retains_precision():
    from veritrace.evidence.time import native_time
    assert native_time("2026-10-02T01:00:00", "iso8601", "action").normalized_utc is None
    precise = native_time(116444736000000001, "filetime", "action")
    assert precise.raw_value == 116444736000000001
    assert precise.raw_precision == "100 nanoseconds"
    assert "sub-microsecond" in precise.uncertainty
