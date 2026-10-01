import json
from types import SimpleNamespace

import httpx
import pytest


def server(mode="ok"):
    requests = []
    def handle(request):
        data = json.loads(request.content) if request.content else {}
        requests.append((request.url.path, data))
        if mode == "timeout":
            raise httpx.ReadTimeout("timed out", request=request)
        if request.url.path == "/api/version":
            body = {"version": "test-1"}
        elif request.url.path == "/api/tags":
            body = {"models": [] if mode == "missing" else [{"name": "qwen3:8b", "digest": "abc", "details": {"quantization_level": "Q4_K_M"}}]}
        elif request.url.path == "/api/show":
            body = {"capabilities": ["completion", "tools", "thinking"], "template": "synthetic template", "details": {}}
            if mode == "cloud":
                body["remote_host"] = "https://cloud.example"
        else:
            body = {"message": {"role": "assistant", "content": "", "thinking": "private", "tool_calls": [{"function": {"name": "get_source_coverage", "arguments": {"case_id": "case01"}}}]}, "done": True, "prompt_eval_count": 12, "eval_count": 3}
        return httpx.Response(200, json=body)
    return SimpleNamespace(transport=httpx.MockTransport(handle), requests=requests)


def test_chat_payload_and_tool_calls():
    from veritrace.settings import Settings
    from veritrace.runtime.client import OllamaClient
    mock = server()
    with OllamaClient(Settings(), transport=mock.transport) as client:
        turn = client.chat([{"role": "user", "content": "case"}], tools=[], schema={"type": "object"})
    payload = next(body for path, body in mock.requests if path == "/api/chat")
    assert payload["stream"] is False
    assert payload["format"] == {"type": "object"}
    assert payload["think"] is False
    assert turn.tool_calls[0]["function"]["name"] == "get_source_coverage"
    assert "thinking" not in turn.as_assistant_message()


@pytest.mark.parametrize("mode", ["missing", "cloud", "timeout"])
def test_unusable_model_rejected_before_case_prompt(mode):
    from veritrace.settings import Settings
    from veritrace.runtime.client import OllamaClient
    from veritrace.errors import VeriTraceError
    mock = server(mode)
    with OllamaClient(Settings(), transport=mock.transport) as client:
        with pytest.raises(VeriTraceError):
            client.chat([{"role": "user", "content": "secret testimony"}])
    assert not any(path == "/api/chat" for path, _ in mock.requests)


def test_budget_requires_matching_verified_profile(tmp_path):
    from veritrace.runtime.budget import ContextBudget
    from veritrace.errors import ContextLimitError
    from veritrace.settings import Settings
    metadata = {"digest": "abc", "template_sha256": "def", "runtime_version": "v1"}
    with pytest.raises(ContextLimitError):
        ContextBudget(Settings(), metadata).ensure([], None, None)
    path = tmp_path / "budget.json"
    path.write_text(json.dumps({"verified": True, "method": "utf8-upper-bound-v1", "num_ctx": 4096, **metadata}), encoding="utf-8")
    budget = ContextBudget(Settings(budget_profile=path), metadata)
    budget.ensure([{"role": "user", "content": "résumé"}], None, None)
    with pytest.raises(ContextLimitError):
        budget.ensure([{"role": "user", "content": "a" * 4000}], None, None)
    with pytest.raises(ContextLimitError):
        ContextBudget(Settings(budget_profile=path), {**metadata, "digest": "changed"}).ensure([], None, None)


def test_benchmark_only_passes_after_real_tool_return():
    from veritrace.runtime.benchmark import benchmark
    from veritrace.runtime.client import ModelTurn
    from veritrace.runtime.budget import ContextBudget
    from veritrace.settings import Settings
    class Client:
        settings = Settings()
        def metadata(self):
            return {"digest": "abc", "template_sha256": "def", "runtime_version": "v1"}
        def chat(self, messages, *, tools=None, schema=None):
            if tools:
                return ModelTurn(tool_calls=[{"function": {"name": "get_benchmark_fact", "arguments": {"case_id": "benchmark"}}}])
            result = json.loads(messages[-1]["content"])
            return ModelTurn(content=json.dumps(result), metrics={"prompt_eval_count": 20})
    client = Client()
    result = benchmark(client, ContextBudget(client.settings, client.metadata()), trials=3)
    assert result["tool_check_passed"] is True
    assert len(result["trials"]) == 3
    assert all(t["receipt"]["executed"] and t["final"]["nonce"] == t["receipt"]["result"]["nonce"] for t in result["trials"])
    assert len({t["final"]["nonce"] for t in result["trials"]}) == 3
