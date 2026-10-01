import json
import secrets
import time


TOOL = {"type": "function", "function": {"name": "get_benchmark_fact", "description": "Return the private host nonce for this synthetic test.", "parameters": {"type": "object", "properties": {"case_id": {"type": "string", "enum": ["benchmark"]}}, "required": ["case_id"], "additionalProperties": False}}}
SCHEMA = {"type": "object", "properties": {"nonce": {"type": "string"}}, "required": ["nonce"], "additionalProperties": False}


def benchmark(client, budget, *, trials=3):
    metadata = client.metadata()
    results = []
    for number in range(trials):
        started = time.perf_counter()
        trial = {"number": number + 1, "passed": False}
        try:
            messages = [{"role": "user", "content": "Call get_benchmark_fact with case_id benchmark, then return its nonce as JSON. Do not guess."}]
            turn = client.chat(messages, tools=[TOOL])
            trial["first_metrics"] = turn.metrics
            if len(turn.tool_calls) != 1:
                raise ValueError("Expected exactly one real tool call")
            call = turn.tool_calls[0].get("function", {})
            if call.get("name") != "get_benchmark_fact" or call.get("arguments") != {"case_id": "benchmark"}:
                raise ValueError("Invalid benchmark tool request")
            fact = {"nonce": secrets.token_hex(16)}
            trial["receipt"] = {"name": call["name"], "arguments": call["arguments"], "executed": True, "result": fact}
            messages.extend([turn.as_assistant_message(), {"role": "tool", "tool_name": call["name"], "content": json.dumps(fact)}])
            final = client.chat(messages, schema=SCHEMA)
            trial["final"] = json.loads(final.content)
            trial["final_metrics"] = final.metrics
            trial["passed"] = trial["final"] == fact
        except Exception as exc:
            trial["error"] = str(exc)
        trial["duration_s"] = time.perf_counter() - started
        results.append(trial)
    probes = []
    for text in ("short", "résumé 新加坡", "boundary " * 180):
        sentinel = secrets.token_hex(8)
        messages = [{"role": "user", "content": f"Ignore the filler and return this nonce as JSON: {sentinel}. Filler: {text}"}]
        probe = {"estimated_prompt": budget.estimate(messages, None, SCHEMA), "passed": False}
        try:
            turn = client.chat(messages, schema=SCHEMA)
            count = turn.metrics.get("prompt_eval_count")
            probe.update(server_prompt_tokens=count, passed=isinstance(count, int) and 0 < count <= probe["estimated_prompt"] and json.loads(turn.content) == {"nonce": sentinel})
        except Exception as exc:
            probe["error"] = str(exc)
        probes.append(probe)
    tool_passed = len(results) >= 3 and all(t["passed"] for t in results)
    passed = tool_passed and all(p["passed"] for p in probes)
    profile = {"method": "utf8-upper-bound-v1", "verified": passed, "num_ctx": client.settings.num_ctx,
               **{k: metadata[k] for k in ("digest", "template_sha256", "runtime_version")}}
    return {"kind": "synthetic capability check", "passed": passed, "tool_check_passed": tool_passed,
            "metadata": metadata, "trials": results, "budget_probes": probes, "budget_profile": profile,
            "gpu_backend": "unknown: retain ollama ps and server logs separately", "forensic_validation": False}
