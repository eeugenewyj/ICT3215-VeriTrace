# Development and desktop setup

Development uses Python 3.12 in a project-local environment. Do not use the
development laptop's default Python 2.7. With Python 3.12 and uv installed:

```powershell
uv venv --python 3.12
uv sync --frozen
uv run python -m veritrace --help
uv run pytest -q
```

On the desktop **host**, install [Ollama for Windows](https://ollama.com/download/windows).
The official [Windows guide](https://docs.ollama.com/windows) describes the
installer and localhost API. Open a fresh PowerShell terminal after installation:

```powershell
ollama --version
ollama pull qwen3:8b
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/version
```

Stop the victim VM before benchmarking. Install this Python package on the
desktop, copy veritrace.example.toml to veritrace.local.toml, then run:

Download the tokenizer from the pinned [official Qwen model revision](https://huggingface.co/Qwen/Qwen3-8B/tree/b968826d9c46dd6066d109eabc6255188de91218)
and configure tokenizer_path = ".external/qwen3-tokenizer.json":

```powershell
New-Item -ItemType Directory -Force .external | Out-Null
Invoke-WebRequest -Uri 'https://huggingface.co/Qwen/Qwen3-8B/resolve/b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json' -OutFile '.external/qwen3-tokenizer.json'
```

```powershell
uv run python -m veritrace doctor --config veritrace.local.toml
uv run python -m veritrace benchmark --config veritrace.local.toml --output .runs/benchmark.json
ollama ps
```

Keep benchmark.json, benchmark.budget.json and the relevant server log.
GPU acceleration must be observed, not inferred from the RX 6750 XT. The
[hardware guide](https://docs.ollama.com/gpu) describes AMD/Vulkan support.
Set budget_profile in the configuration only after a passing benchmark.
The conservative token budget is empirical and tied to runtime version,
model digest, template, tokenizer hash and context length. Serialized payload
tokens plus framing allowance are not an exact rendering of Ollama's template.
Without a tokenizer the byte upper bound is available but usually too restrictive
for verification at 4,096 tokens. Both methods require measured server-count and
retained-sentinel checks before live cases.
Failures require a recorded model/context adjustment and rebenchmark.

The profile also records native-tools-then-json-v1: retrieval with native tools,
a tool-result/stop turn, then constrained JSON with tools omitted. Server prompt
counts are checked for all three stages as well as short, Unicode and near-boundary
retention probes. Old profiles without this protocol identity are rejected.

Initially use localhost. Laptop access needs a later private-LAN configuration
limited to the laptop, after localhost succeeds. Do not expose the server publicly.
Inference and victim experiments occur at different times. The application
does not install model weights, acquire a live victim, or parse RAM.

External forensic parsers are separate prerequisites. Until their commands,
versions, schema profiles and acquired-sample comparisons are recorded, source
families are unavailable or unsupported and cannot be advertised as validated.
