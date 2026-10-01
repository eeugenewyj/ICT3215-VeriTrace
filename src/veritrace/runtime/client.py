import hashlib
from typing import Any

import httpx
from pydantic import BaseModel, ConfigDict, Field

from ..errors import DependencyError, ModelError
from ..settings import Settings


class ModelTurn(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)
    content: str = ""
    tool_calls: list[dict[str, Any]] = Field(default_factory=list)
    metrics: dict[str, Any] = Field(default_factory=dict)

    def as_assistant_message(self):
        message = {"role": "assistant", "content": self.content}
        if self.tool_calls:
            message["tool_calls"] = self.tool_calls
        return message


class OllamaClient:
    def __init__(self, settings: Settings, *, transport=None):
        self.settings = settings
        self._http = httpx.Client(base_url=settings.model_base_url, timeout=settings.model_timeout_s, transport=transport, trust_env=False, follow_redirects=False)
        self._metadata = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self._http.close()

    def _request(self, path, data=None):
        try:
            response = self._http.get(path) if data is None else self._http.post(path, json=data)
            response.raise_for_status()
            body = response.json()
            if not isinstance(body, dict) or body.get("error"):
                raise ValueError("Invalid/error API response")
            return body
        except (httpx.HTTPError, ValueError) as exc:
            raise ModelError(f"Ollama request {path} failed: {exc}") from exc

    def metadata(self):
        if self._metadata is not None:
            return self._metadata
        version = self._request("/api/version")
        tags = self._request("/api/tags")
        model = next((m for m in tags.get("models", []) if m.get("name") == self.settings.model_name or m.get("model") == self.settings.model_name), None)
        if model is None:
            raise DependencyError(f"Local model {self.settings.model_name} is not downloaded")
        info = self._request("/api/show", {"model": self.settings.model_name})
        if any(info.get(k) or model.get(k) for k in ("remote_host", "remote_model")) or "cloud" in json_text(model).lower():
            raise DependencyError("Cloud-backed models cannot receive case data")
        capabilities = info.get("capabilities", [])
        if "tools" not in capabilities or not model.get("digest") or not info.get("template"):
            raise DependencyError("Model must advertise tools and have a local digest/template")
        self._metadata = {"runtime_version": version.get("version"), "model": self.settings.model_name,
                          "digest": model["digest"], "quantization": model.get("details", {}).get("quantization_level"),
                          "template_sha256": hashlib.sha256(info["template"].encode()).hexdigest(),
                          "capabilities": capabilities, "think": False if "thinking" in capabilities else None}
        return self._metadata

    def chat(self, messages, *, tools=None, schema=None):
        metadata = self.metadata()  # Check local model BEFORE any case text is sent.
        payload = {"model": self.settings.model_name, "messages": messages, "stream": False,
                   "options": {"num_ctx": self.settings.num_ctx, "temperature": self.settings.temperature}}
        if tools is not None:
            payload["tools"] = tools
        if schema is not None:
            payload["format"] = schema
        if metadata["think"] is not None:
            payload["think"] = metadata["think"]
        body = self._request("/api/chat", payload)
        message = body.get("message")
        if body.get("done") is not True or not isinstance(message, dict) or message.get("role") != "assistant":
            raise ModelError("Incomplete or malformed assistant response")
        try:
            return ModelTurn(content=message.get("content", ""), tool_calls=message.get("tool_calls") or [],
                             metrics={k: body[k] for k in ("total_duration", "load_duration", "prompt_eval_count", "prompt_eval_duration", "eval_count", "eval_duration") if k in body})
        except ValueError as exc:
            raise ModelError("Malformed assistant content/tool calls") from exc


def json_text(value):
    import json
    return json.dumps(value, ensure_ascii=False)
