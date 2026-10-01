import json

from ..errors import ContextLimitError


class ContextBudget:
    """Conservative UTF-8 accounting; empirical profile is runtime/model bound.

    This intentionally overestimates ordinary byte-fallback tokenization. It is
    not an exact tokenizer. Server counts and retained sentinel probes must pass
    before live cases. No silent trimming occurs.
    """
    reserve = 768
    overhead = 512

    def __init__(self, settings, metadata):
        self.settings, self.metadata = settings, metadata
        self.profile = None
        if settings.budget_profile:
            try:
                self.profile = json.loads(settings.budget_profile.read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                raise ContextLimitError(f"Cannot read budget profile: {exc}") from exc

    def estimate(self, messages, tools, schema):
        payload = {"messages": messages}
        if tools is not None:
            payload["tools"] = tools
        if schema is not None:
            payload["format"] = schema
        return len(json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")) + self.overhead

    def ensure(self, messages, tools, schema):
        expected = {k: self.metadata.get(k) for k in ("digest", "template_sha256", "runtime_version")}
        if not self.profile or self.profile.get("verified") is not True or self.profile.get("method") != "utf8-upper-bound-v1" or self.profile.get("num_ctx") != self.settings.num_ctx or any(self.profile.get(k) != v for k, v in expected.items()):
            raise ContextLimitError("Run the model benchmark to create a matching verified budget profile")
        if self.estimate(messages, tools, schema) + self.reserve > self.settings.num_ctx:
            raise ContextLimitError("Request exceeds the conservative context budget; narrow input or benchmark a larger context")
