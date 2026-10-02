# VeriTrace

Testimony-to-artefact verification for acquired Windows 10 evidence. A local
model extracts atomic claims, requests forensic parsing and bounded evidence
queries, and produces an offline HTML report with source-linked assessments.
The investigator reviews the complete report and makes the final decision.

The backend prototype is implemented. **Live desktop-model and victim-sample
validation are pending.** Unit tests and an upstream parser fixture check do
not establish forensic accuracy. See [implementation status](docs/implementation-status.md).

## Start here

Use Python **3.12** and [uv](https://docs.astral.sh/uv/). From this checkout:

```powershell
uv venv --python 3.12
uv sync --frozen
uv run veritrace --help
uv run pytest -q
```

Follow [desktop model setup](docs/setup.md), then [parser configuration](docs/parser-compatibility.md)
and the [acquisition rehearsal](docs/acquisition.md). The desktop hosts the
Windows 10 Pro victim VM; development and analysis use investigator working
copies. Only victim acquisitions enter VeriTrace.

```powershell
Copy-Item veritrace.example.toml veritrace.local.toml
uv run veritrace doctor --config veritrace.local.toml
uv run veritrace benchmark --config veritrace.local.toml --output .runs/benchmark.json
# After a passing benchmark and parser sample validation:
uv run veritrace run --config veritrace.local.toml --case .cases/dev01 --output .runs/dev01
```

`doctor` checks the local model inventory and advertises configured families;
it does not certify parsers or GPU acceleration. `benchmark` tests the actual
native-tool/structured-output protocol and measured context retention using
synthetic nonces. A passing, matching budget profile is required for case runs.

## Inputs and results

Each case contains `case.json`, UTF-8 `testimony.txt` and `evidence/`. The
[manifest example](examples/case.json) illustrates the format; it contains no
acquired evidence. Ground-truth labels are separate from agent input.

The six adapter families are Edge History/downloads, LNK, Jump Lists, Prefetch,
decoded UserAssist and Recycle Bin metadata. External parser executables,
versions, dependency hashes and acquired-sample comparisons must be configured
before enabling them. Unavailable, failed, empty and unsupported sources are
reported explicitly. The model cannot choose executable paths or arbitrary SQL.

Outputs include `report.html`, claims/assessments/coverage JSON, `run.json`,
`registration.json`, `tool_calls.jsonl`, `evidence.sqlite` and retained raw
parser output. Citations must match this case, a record returned for that claim,
an original source identity and an unchanged parser-output location.

Assessments are **supported**, **contradicted**, **unverified** or
**inconclusive**. Missing evidence alone never contradicts a claim. Record
identity checks do not establish relevance, sufficiency or the human actor.

Read the [investigator manual](docs/manual.md), [evaluation procedure](docs/evaluation.md)
and [delivery checklist](docs/delivery.md). The approved [design](docs/superpowers/specs/2026-10-02-veritrace-design.md)
and [implementation plan](docs/superpowers/plans/2026-10-02-veritrace-prototype.md)
record the agreed scope.

Direct disk-image ingestion, RAM analysis, compromise-specific evidence families,
a browser interface and stronger prompt-injection defenses are later extensions.
Model weights, forensic binaries, acquisitions and private configuration remain
outside source control. The package can be built with `uv run python -m build`.
