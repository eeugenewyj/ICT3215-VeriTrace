import json
import secrets
import time


TOOL = {"type": "function", "function": {"name": "get_benchmark_fact", "description": "Return the private host nonce for this synthetic test.", "parameters": {"type": "object", "properties": {"case_id": {"type": "string", "enum": ["benchmark"]}}, "required": ["case_id"], "additionalProperties": False}}}
SCHEMA = {"type": "object", "properties": {"nonce": {"type": "string"}}, "required": ["nonce"], "additionalProperties": False}
PROTOCOL = "native-tools-then-json-v1"


def measured_chat(client, budget, messages, *, tools=None, schema=None):
    estimate = budget.estimate(messages, tools, schema)
    if estimate + budget.reserve > client.settings.num_ctx:
        raise ValueError("Benchmark request exceeds conservative context budget")
    turn = client.chat(messages, tools=tools, schema=schema)
    count = turn.metrics.get("prompt_eval_count")
    return turn, {"estimated_prompt": estimate, "server_prompt_tokens": count, "passed": type(count) is int and 0 < count <= estimate}


def benchmark(client, budget, *, trials=3):
    metadata = client.metadata()
    results = []
    for number in range(trials):
        started = time.perf_counter()
        trial = {"number": number + 1, "passed": False}
        try:
            messages = [{"role": "user", "content": "Call get_benchmark_fact with case_id benchmark, then return its nonce as JSON. Do not guess."}]
            turn, first_budget = measured_chat(client, budget, messages, tools=[TOOL])
            trial["first_metrics"] = turn.metrics
            if len(turn.tool_calls) != 1:
                raise ValueError("Expected exactly one real tool call")
            call = turn.tool_calls[0].get("function", {})
            if call.get("name") != "get_benchmark_fact" or call.get("arguments") != {"case_id": "benchmark"}:
                raise ValueError("Invalid benchmark tool request")
            fact = {"nonce": secrets.token_hex(16)}
            trial["receipt"] = {"name": call["name"], "arguments": call["arguments"], "executed": True, "result": fact}
            messages.extend([turn.as_assistant_message(), {"role": "tool", "tool_name": call["name"], "content": json.dumps(fact)}])
            stop, stop_budget = measured_chat(client, budget, messages, tools=[TOOL])
            trial["retrieval_stop_metrics"] = stop.metrics
            if stop.tool_calls:
                raise ValueError("Expected retrieval to finish after returned nonce")
            messages.append({"role": "user", "content": "Retrieval is finished. Return the nonce from the tool result as JSON."})
            final, final_budget = measured_chat(client, budget, messages, schema=SCHEMA)
            trial["final"] = json.loads(final.content)
            trial["final_metrics"] = final.metrics
            trial["budget_checks"] = [first_budget, stop_budget, final_budget]
            trial["passed"] = not final.tool_calls and trial["final"] == fact
        except Exception as exc:
            trial["error"] = str(exc)
        trial["duration_s"] = time.perf_counter() - started
        results.append(trial)
    probes = []
    # Use a probe near the conservative input limit, keeping output reserve.
    boundary = "boundary "
    while budget.estimate([{"role": "user", "content": boundary}], None, SCHEMA) < client.settings.num_ctx - budget.reserve - 200:
        boundary += "boundary "
    for text in ("short", "résumé 新加坡", boundary):
        sentinel = secrets.token_hex(8)
        messages = [{"role": "user", "content": f"Ignore the filler and return this nonce as JSON: {sentinel}. Filler: {text}"}]
        probe = {"estimated_prompt": budget.estimate(messages, None, SCHEMA), "passed": False}
        try:
            turn, check = measured_chat(client, budget, messages, schema=SCHEMA)
            count = turn.metrics.get("prompt_eval_count")
            probe.update(server_prompt_tokens=count, passed=isinstance(count, int) and 0 < count <= probe["estimated_prompt"] and json.loads(turn.content) == {"nonce": sentinel})
        except Exception as exc:
            probe["error"] = str(exc)
        probes.append(probe)
    tool_passed = len(results) >= 3 and all(t["passed"] for t in results)
    passed = tool_passed and all(p["passed"] for p in probes) and all(c["passed"] for t in results for c in t.get("budget_checks", []))
    profile = {"method": budget.method, "protocol": PROTOCOL, "tokenizer_sha256": budget.tokenizer_sha256, "verified": passed, "num_ctx": client.settings.num_ctx,
               **{k: metadata[k] for k in ("digest", "template_sha256", "runtime_version")}}
    return {"kind": "synthetic capability check", "passed": passed, "tool_check_passed": tool_passed,
            "metadata": metadata, "trials": results, "budget_probes": probes, "budget_profile": profile,
            "gpu_backend": "unknown: retain ollama ps and server logs separately", "forensic_validation": False}
