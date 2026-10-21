import json
import hashlib

from ..errors import ContextLimitError
from .benchmark import PROTOCOL


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
        self.tokenizer = None
        self.tokenizer_sha256 = None
        if settings.tokenizer_path:
            try:
                from tokenizers import Tokenizer
                self.tokenizer_sha256 = hashlib.sha256(settings.tokenizer_path.read_bytes()).hexdigest()
                self.tokenizer = Tokenizer.from_file(str(settings.tokenizer_path))
            except (OSError, ValueError, Exception) as exc:
                raise ContextLimitError(f"Cannot load tokenizer: {exc}") from exc
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
        serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        count = len(self.tokenizer.encode(serialized, add_special_tokens=False).ids) if self.tokenizer else len(serialized.encode("utf-8"))
        return count + self.overhead

    @property
    def method(self):
        return "tokenizer-json-upper-bound-v1" if self.tokenizer else "utf8-upper-bound-v1"

    def ensure(self, messages, tools, schema):
        expected = {k: self.metadata.get(k) for k in ("digest", "template_sha256", "runtime_version")}
        if not self.profile or self.profile.get("verified") is not True or self.profile.get("protocol") != PROTOCOL or self.profile.get("method") != self.method or self.profile.get("num_ctx") != self.settings.num_ctx or any(self.profile.get(k) != v for k, v in expected.items()) or self.profile.get("tokenizer_sha256") != self.tokenizer_sha256:
            raise ContextLimitError("Run the model benchmark to create a matching verified budget profile")
        if self.estimate(messages, tools, schema) + self.reserve > self.settings.num_ctx:
            raise ContextLimitError("Request exceeds the conservative context budget; narrow input or benchmark a larger context")
