# Development and desktop setup

Development and analysis now run on the desktop. Use Python 3.12 in a
project-local environment; the desktop's system Python 3.13 is outside the
package's supported range. Python 3.12.15 and uv 0.12.22 were installed and the
locked environment recreated on 2 October 2026. Open a fresh terminal to pick
up the installed uv directory in the user PATH. With Python 3.12 and uv installed:

```powershell
uv venv --python 3.12
uv sync --frozen
uv run python -m veritrace --help
uv run pytest -q
```

The desktop **host** has Ollama 0.40.16 and qwen3:8b installed as observed on
14 November 2026; the October runtime was 0.35.0.
Verify the existing model and localhost API without downloading the model again:

```powershell
ollama --version
ollama list
Invoke-RestMethod http://127.0.0.1:11434/api/version
```

The [desktop benchmark](desktop-benchmark.md) passed again for the new runtime,
including an 8,192-token profile used by the focused Jump List cases. On this
desktop those runs use
.runs/jumplist01-preparation/veritrace.jumplist01-8k-validated.toml. The general
veritrace.local.toml retains older runtime/parser references and needs revalidation
before broader runs; it is not the latest validated case configuration. Preserve
both private configurations. Acquired cases and profiles are not included in a clone.
For a new installation, use [Ollama for Windows](https://ollama.com/download/windows)
and the official [Windows guide](https://docs.ollama.com/windows); pull the model
only when ollama list confirms it is absent.

Stop the victim VM before benchmarking. On a fresh checkout, install this
package and copy veritrace.example.toml to veritrace.local.toml. Keep any
existing local configuration. For the tokenizer prerequisite:

Use the tokenizer from the pinned [official Qwen model revision](https://huggingface.co/Qwen/Qwen3-8B/tree/b968826d9c46dd6066d109eabc6255188de91218)
and configure tokenizer_path = ".external/qwen3-tokenizer.json":

```powershell
New-Item -ItemType Directory -Force .external | Out-Null
if (-not (Test-Path -LiteralPath '.external/qwen3-tokenizer.json')) {
    Invoke-WebRequest -Uri 'https://huggingface.co/Qwen/Qwen3-8B/resolve/b968826d9c46dd6066d109eabc6255188de91218/tokenizer.json' -OutFile '.external/qwen3-tokenizer.json'
}
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
For the first benchmark, omit budget_profile rather than pointing to a file
that has not been created yet. Choose fresh output paths for subsequent runs.
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
limited to an explicitly authorized client after localhost succeeds. No LAN
access is needed for the current desktop-only workflow. Do not expose the server publicly.
Inference and victim experiments occur at different times. The application
does not install model weights, acquire a live victim, or parse RAM.

External forensic parsers are separate prerequisites. Until their commands,
versions, schema profiles and acquired-sample comparisons are recorded, source
families are unavailable or unsupported and cannot be advertised as validated.
See the [current acquisition/parser inventory and setup steps](tools-setup.md)
for the desktop's installed tools and outstanding deployment work.
