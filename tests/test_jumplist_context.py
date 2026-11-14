"""Jump List evidence must retain application context and timestamp meanings."""
import json

from tests.factories import make_claim, make_record
from veritrace.agents.tools import compact_record, model_view
from veritrace.evidence.time import native_time


def jumplist_record(**updates):
    times = [native_time(value, "iso8601", role) for role, value in (
        ("destlist_birth_object_id_created", "2026-11-14T09:05:50+00:00"),
        ("destlist_entry_modified", "2026-11-14T13:40:27+00:00"),
        ("target_file_created", "2026-11-14T09:07:01+00:00"),
    )]
    return make_record(family="jumplist", application="Notepad 64-bit", times=times,
                       original_path=r"C:\Users\Victim\Recent\9b9cdc69c1c24e2b.automaticDestinations-ms",
                       **updates)


def test_jump_list_search_view_retains_application_and_container_kind():
    record = jumplist_record()
    view = compact_record(record)
    assert view["application"] == "Notepad 64-bit"
    assert view["jumplist_type"] == "automatic"
    assert [t["role"] for t in view["times"]] == ["destlist_entry_modified"]
    detailed = model_view("get_record", record.model_dump(mode="json"))
    assert set(detailed["omitted_noninteraction_time_roles"]) == {"destlist_birth_object_id_created", "target_file_created"}
    assert len(record.times) == 3  # The full record still retains every timestamp.
    custom = compact_record(record.model_copy(update={"original_path": r"C:\Recent\app.customDestinations-ms"}))
    assert custom["jumplist_type"] == "custom"
    unknown = compact_record(record.model_copy(update={"application": None, "original_path": None}))
    assert "application" not in unknown and "jumplist_type" not in unknown


def test_jump_list_record_view_keeps_meaningful_context_without_duplicate_times():
    raw = {"AppId": "9b9cdc69c1c24e2b", "AppIdDescription": "Notepad 64-bit", "EntryNumber": "1",
           "InteractionCount": "0", "PinStatus": "Not pinned", "Arguments": "--example", "Notes": "Specific parser caveat",
           "CreationTime": "2026-11-14T09:05:50+00:00", "LastModified": "2026-11-14T13:40:27+00:00",
           "TargetCreated": "2026-11-14T09:07:01+00:00", "SourceCreated": "2099-01-01T00:00:00Z",
           "FileBirthDroid": "x" * 500, "source_file_timestamps_scope": "working copy " * 100}
    record = jumplist_record(raw_fields=raw)
    view = model_view("get_record", record.model_dump(mode="json"))
    for key in ("AppId", "EntryNumber", "InteractionCount", "PinStatus", "Arguments", "Notes"):
        assert view["details"][key] == raw[key]
    assert not {"CreationTime", "LastModified", "TargetCreated", "SourceCreated", "FileBirthDroid"} & view["details"].keys()
    assert view["application"] == record.application
    assert record.raw_fields == raw  # Compaction never edits the preserved record.
    assert len(json.dumps(view)) < len(record.model_dump_json())


def test_jump_list_clock_check_ignores_birth_and_target_times():
    from veritrace.agents.timecheck import time_agrees, time_conflict
    record = jumplist_record()
    opening = lambda text: make_claim(action="open_document", time_expression=text)
    assert time_agrees(opening("9:40 pm"), [record], "Asia/Singapore")
    assert not time_agrees(opening("5:05 pm"), [record], "Asia/Singapore")
    assert time_conflict(opening("5:05 pm"), [record], "Asia/Singapore")
    assert time_conflict(opening("5:07 pm"), [record], "Asia/Singapore")
    # A Jump List association timestamp cannot validate a different action's clock.
    assert not time_agrees(make_claim(action="download_file", time_expression="9:40 pm"), [record], "Asia/Singapore")


def test_jump_list_without_an_interaction_time_does_not_supply_one():
    from veritrace.agents.timecheck import time_agrees
    record = jumplist_record()
    record = record.model_copy(update={"times": [t for t in record.times if t.role != "destlist_entry_modified"]})
    assert not time_agrees(make_claim(action="open_document", time_expression="5:05 pm"), [record], "Asia/Singapore")


def test_jump_list_view_converts_only_the_activity_time_using_the_case_timezone():
    record = jumplist_record()
    view = model_view("get_record", record.model_dump(mode="json"), source_timezone="Asia/Singapore")
    assert view["times"] == [{"role": "destlist_entry_modified", "utc": "2026-11-14T13:40:27Z", "local": "2026-11-14T21:40:27+08:00"}]
    assert view["source_timezone"] == "Asia/Singapore"
    assert "09:05:50" not in json.dumps(view) and "09:07:01" not in json.dumps(view)


def test_jump_list_view_does_not_invent_a_local_time_for_an_unknown_zone():
    view = compact_record(jumplist_record(), source_timezone="Unknown/Zone")
    assert "local" not in view["times"][0]
    assert "not inferred" in view["local_time_note"]


def test_jump_list_view_omits_repeated_rules_but_preserves_specific_warnings():
    from veritrace.agents.tools import JUMPLIST_GENERIC_LIMITATIONS
    specific = "Embedded target is ambiguous in this source."
    record = jumplist_record(limitations=[*JUMPLIST_GENERIC_LIMITATIONS, specific])
    view = compact_record(record)
    assert view["limitations"] == [specific]
    assert set(record.limitations) == JUMPLIST_GENERIC_LIMITATIONS | {specific}
