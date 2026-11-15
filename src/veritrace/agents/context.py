"""Lossless removal of repeated record projections from the model context."""
import json


POLICY = "identical-record-references-v2"


def canonical(value):
    # JSON comparison preserves distinctions such as true versus 1.
    return json.dumps(value, sort_keys=True, ensure_ascii=False, separators=(",", ":"))


def tool_result(message):
    if message.get("role") != "tool":
        return None
    try:
        value = json.loads(message.get("content", ""))
    except (TypeError, ValueError):
        return None
    return value if isinstance(value, dict) else None


def deduplicate_record_messages(messages):
    """Replace only data fully repeated in a retained get_record response.

    No tool messages, pagination fields, unique fields or record IDs are removed.
    The full retained projection stays in context and the original tool ledger is
    untouched. References make the presentation change explicit to the model.
    """
    latest = {}
    for number, message in enumerate(messages):
        result = tool_result(message)
        if message.get("tool_name") == "get_record" and result and "record_id" in result and "details" in result:
            latest[result["record_id"]] = (number, result)
    replaced = 0
    for number, message in enumerate(messages):
        result = tool_result(message)
        if not result:
            continue
        changed = False
        if message.get("tool_name") == "search_records" and isinstance(result.get("records"), list):
            for position, record in enumerate(result["records"]):
                if not isinstance(record, dict):
                    continue
                later = latest.get(record.get("record_id"))
                if later is None:
                    continue
                full = later[1]
                if all(key in full and canonical(full[key]) == canonical(value) for key, value in record.items()):
                    direction = "later" if later[0] > number else "earlier"
                    result["records"][position] = {"record_id": record["record_id"], "details_in": f"{direction} get_record response"}
                    replaced += 1
                    changed = True
        elif message.get("tool_name") == "get_record" and "details" in result:
            later = latest.get(result.get("record_id"))
            if later and later[0] > number and canonical(result) == canonical(later[1]):
                result = {"record_id": result["record_id"], "details_in": "later identical get_record response"}
                replaced += 1
                changed = True
        if changed:
            message["content"] = json.dumps(result, ensure_ascii=False, separators=(",", ":"))
    return replaced
