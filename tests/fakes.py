import json


class ReplayClient:
    """Scripted model boundary for tests; never available through configuration."""
    def __init__(self, turns):
        self.turns = list(turns)
        self.requests = []
    @classmethod
    def from_contents(cls, values):
        from veritrace.runtime.client import ModelTurn
        return cls([ModelTurn(content=v) for v in values])
    def chat(self, messages, *, tools=None, schema=None):
        self.requests.append(json.loads(json.dumps({"messages": messages, "tools": tools, "schema": schema})))
        return self.turns.pop(0)


class TestBudget:
    def ensure(self, messages, tools, schema):
        pass
