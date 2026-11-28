# VeriTrace

Testimony-to-artefact verification for acquired Windows 10 evidence. A local
model extracts atomic claims, requests forensic parsing and bounded evidence
queries, and produces an offline HTML report with source-linked assessments.
The investigator reviews the complete report and makes the final decision.

The backend prototype is implemented. The [desktop model benchmark](docs/desktop-benchmark.md)
passed with local qwen3:8b, including an 8,192-token refresh on 14 November 2026.
**All six parser families have recorded victim-source field comparisons**, including
a nonempty Edge sample in the standard01 development case. A coverage-context fix
let its five claims reach assessments at the verified 8,192-token limit; 41 invalid
or empty Prefetch inputs remain explicit failures. Focused
[Jump List integration](docs/jumplist-contribution.md) also passed genuine local-model
runs. Unit tests, parser comparisons and synthetic benchmarks do not establish
classification accuracy. The observed denial-interpretation failure has been fixed
and replayed; broader semantic and attribution evaluation remains pending. See
[implementation status](docs/implementation-status.md) for remaining evaluation work.
The [standard01 development fault checks](docs/standard01-development-tests.md)
record source-removal, corruption, claim-scope, date, uncertainty and response-capacity tests;
their draft expectations still require independent review.

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
if (-not (Test-Path -LiteralPath veritrace.local.toml)) {
    Copy-Item veritrace.example.toml veritrace.local.toml
}
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

## Parser tools and versions

Five of the six families use Eric Zimmerman's command-line tools
([LECmd](https://github.com/EricZimmerman/LECmd),
[JLECmd](https://github.com/EricZimmerman/JLECmd),
[PECmd](https://github.com/EricZimmerman/PECmd),
[RBCmd](https://github.com/EricZimmerman/RBCmd) and
[RECmd](https://github.com/EricZimmerman/RECmd) with the
[RegistryPlugins](https://github.com/EricZimmerman/RegistryPlugins) UserAssist
decoder). Edge History uses [Hindsight](https://github.com/RyanDFIR/hindsight),
which is not an Eric Zimmerman tool. Every executable, its dependency files and
its version are pinned by hash in a private parser profile; a changed file or
version is rejected.

| Family | Tool | Desktop validation (recorded in [tools-setup](docs/tools-setup.md)) | Kali development VM build (15 Nov 2026) |
| --- | --- | --- | --- |
| lnk | LECmd | 2026.5.0 | 2026.10.4 |
| jumplist | JLECmd | 2026.5.0 | 2026.10.6 |
| prefetch | PECmd | 2026.5.0 | 2026.10.3 (profile drafted, not enabled) |
| recyclebin | RBCmd | 2026.5.0 | 2026.10.1 |
| userassist | RECmd + RegistryPlugin.UserAssist 0.5 | 2026.5.0 | not built yet |
| edge_history | Hindsight | 2026.06 (pinned source 4cf136f) | 2026.06 |

The Kali builds are compiled from the upstream source for .NET 10 and run with
`dotnet <tool>.dll`; the desktop uses the released .NET 9 builds. The two
environments therefore run different tool versions. A family counts as validated
only for the version recorded in its profile and comparison record, so rerun the
acquired-sample comparison before relying on a different version.

Outputs include `report.html`, claims/assessments/coverage JSON, `run.json`,
`registration.json`, `tool_calls.jsonl`, `evidence.sqlite` and retained raw
parser output. `coverage-summary.json` and the HTML distinguish parsed files
from unparsed inputs and explain failures. `veritrace report` can produce a new
view with source-bound diagnostic notes without rerunning inference; see the
[manual](docs/manual.md). Citations must match this case, a record returned for that claim,
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
