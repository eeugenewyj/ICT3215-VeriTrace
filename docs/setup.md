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

```powershell
uv run python -m veritrace doctor --config veritrace.local.toml
uv run python -m veritrace benchmark --config veritrace.local.toml --output .runs/benchmark.json
ollama ps
```

Keep benchmark.json, benchmark.budget.json and the relevant server log.
GPU acceleration must be observed, not inferred from the RX 6750 XT. The
[hardware guide](https://docs.ollama.com/gpu) describes AMD/Vulkan support.
Set budget_profile in the configuration only after a passing benchmark.
The conservative UTF-8 budget is empirical and tied to runtime version,
model digest, template and context length; it is not an exact tokenizer.
Failures require a recorded model/context adjustment and rebenchmark.

Initially use localhost. Laptop access needs a later private-LAN configuration
limited to the laptop, after localhost succeeds. Do not expose the server publicly.
Inference and victim experiments occur at different times. The application
does not install model weights, acquire a live victim, or parse RAM.

External forensic parsers are separate prerequisites. Until their commands,
versions, schema profiles and acquired-sample comparisons are recorded, source
families are unavailable or unsupported and cannot be advertised as validated.
