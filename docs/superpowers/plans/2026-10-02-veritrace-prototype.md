# VeriTrace Prototype Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking. The recommended execution method for this project is inline execution with superpowers:executing-plans because the case contracts, parser outputs, tools, and report depend on the same interfaces.

**Goal:** Build and evaluate a local command-line prototype that interprets testimony, genuinely calls forensic tools against an acquired artefact folder, and produces a sourced HTML report.

**Architecture:** A Python backend registers immutable evidence, runs versioned external parser adapters on working copies, and indexes normalized records in SQLite. Two sequential roles share a local model; the verification role calls a fixed case-scoped tool API and returns assessments checked against actual retrieval receipts. The CLI and offline report call the same backend functions.

**Tech Stack:** Python 3.12 virtual environment, uv dependency lock, Pydantic 2, httpx, Jinja2, SQLite, pytest; Ollama/qwen3:8b as the first runtime candidate; Hindsight and the proposed Zimmerman tools as separately installed parser prerequisites. Exact dependency/parser versions are frozen after compatibility checks.

**Spec:** ../specs/2026-10-02-veritrace-design.md

## Global Constraints

The following requirements are copied from the design and apply to every task:

- Acquisitions concern the victim only. Attacker-device forensics is excluded.
- The first prototype accepts an acquired artefact folder. Direct disk-image ingestion is a later milestone.
- Collect and preserve RAM during lab acquisition; RAM analysis is a later milestone.
- Use Edge for browsing and viewing downloaded local PDFs. Notepad is the proposed separate program-launch test.
- Assessment runs automatically; the investigator reviews the complete report.
- Build a command-line interface and standalone HTML report first. Keep the backend independent of the interface so a local browser interface can be added.
- Inference is fully local. The desktop has a Ryzen 7 5700X, 16 GB system RAM, and RX 6750 XT with 12 GB VRAM.
- Stronger prompt-injection defences and optional claim review are future work. The prototype retains basic case-scoped tool and output validation.
- Unknown timestamps remain unknown.
- Keep the testimony unchanged.
- Absence alone is insufficient.

Additional execution constants from the design: one model serves both roles sequentially; initial context 4,096 tokens; search pages at most 25 records; at most 12 tool calls per claim; two output-repair attempts; one correction when the required extraction call is missing. Context/model changes need a recorded benchmark. A failed external dependency produces a recorded failure, never substituted forensic evidence.

## Review Focus

1. UTF-8 names, CRLF testimony and repeated sentences: preserve exact text and character spans, and match the intended source occurrence. Tests in Tasks 2 and 6.
2. Windows junctions, traversal and overlapping evidence/output folders: refuse registration before any copying or parser execution. Tests in Task 2.
3. Missing SQLite sidecars, malformed sources and changing originals: distinguish missing companions, parser failures and integrity errors. Tests in Tasks 3, 4 and 11.
4. Refused tool calls, excessive context and citations never retrieved: return workflow/claim errors with partial reports rather than fabricated assessments. Tests in Tasks 1, 7 and 8.
5. Hostile testimony/artefact HTML and ambiguous evidence identity: escape report content, retain ambiguity, and never turn a guessed database row into a source citation. Tests in Tasks 4 and 8.

## Workspace and milestones

The target application repository is **C:\Users\eugen\Github\ICT3215-VeriTrace**, currently clean on main at d1e2b36, containing only README.md. This plan and the design currently live in the separate planning workspace. Copy both documents into the application repository when implementation begins so they travel with the code.

Execution choices: inline on a new codex/veritrace-prototype branch in the existing checkout; inline in an isolated worktree; or subagent execution in an isolated worktree. Do not create a worktree before the user chooses it. If isolation is chosen, use a native tool only when it targets the application repository; otherwise use a scoped Git worktree for that repository and verify the worktree directory is ignored. A worktree of the planning repository would be the wrong project.

Use command-scoped safe.directory for this explicitly supplied repository when necessary; do not globally disable Git's ownership checks. Writes outside the planning workspace require the platform's normal scoped approval. No push, merge or publication is part of this plan.

The development machine's default python resolves to Python 2.7. A bundled Python **3.12.14** is available at C:\Users\eugen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe. uv **0.12.4** is installed, but its default cache could not be initialized in the sandbox. Use a project-local cache and an explicit Python 3 interpreter. Do not replace the system Python.

- **Milestone 1, Task 1:** runnable package, dependency checks and a genuine local-model capability benchmark.
- **Milestone 2, Tasks 2-8:** an honest Edge-only end-to-end report on acquired evidence. Other families are explicitly outside that interim build's enabled coverage.
- **Milestone 3, Tasks 9-10:** the six agreed source families enabled and independently validated.
- **Milestone 4, Tasks 11-12:** real-case acquisition rehearsal, held-out evaluation, manual and runnable distribution.

The Edge-only intermediate build is a development milestone. The final prototype still targets all six families in the design. VMware/FTK acquisition and desktop inference need owner-run checks because this development session does not control the desktop.

## File map and contracts

All application paths below are relative to the target application repository or its approved worktree.

| Files | Responsibility |
| --- | --- |
| pyproject.toml, uv.lock, .gitignore, veritrace.example.toml | Packaging, reproducible dependencies, private-data exclusions and host configuration |
| src/veritrace/__init__.py, __main__.py, cli.py, errors.py, settings.py | Package entry, command routing, explicit errors and validated configuration |
| src/veritrace/runtime/client.py, budget.py, benchmark.py | Local model transport, context accounting and measured capability checks |
| src/veritrace/cases/models.py, registry.py, integrity.py | Case contracts, registration, evidence copies and source hashes |
| src/veritrace/evidence/models.py, time.py, index.py | Evidence contracts, timestamp interpretation and parameterized queries |
| src/veritrace/parsers/base.py, runner.py, coverage.py | Adapter contract, controlled subprocess execution and processing inventory |
| src/veritrace/parsers/edge.py, lnk.py, jumplist.py, prefetch.py, recyclebin.py, userassist.py | Version-specific source adapters |
| src/veritrace/agents/claims.py, verify.py, tools.py, citations.py | Claim interpretation, actual tool loop, dispatch/receipts and citation checks |
| src/veritrace/prompts/claims.txt, verify.txt | Versioned role instructions |
| src/veritrace/report/render.py, templates/report.html, service.py | Escaped report and reusable orchestration |
| src/veritrace/evaluation/metrics.py, corpus.py | Frozen splits, evaluation exports and measured results |
| tests/factories.py, fakes.py and tests by component | Synthetic unit fixtures and scripted model responses, unavailable as a production runtime |
| docs/setup.md, acquisition.md, manual.md, evaluation.md, delivery.md | Owner setup, acquisition procedure, investigator manual, evaluation and rubric checklist |

Create __init__.py in each source subpackage. Configuration and downloaded parser binaries belong in a private .external directory; cases and runs in .cases and .runs. Ignore those folders, .venv, .uv-cache, .pytest_cache, __pycache__, .env, build and dist. Only synthetic or expressly reusable lab fixtures go into source control.

Use frozen Pydantic models with extra fields forbidden at trust boundaries. Error subclasses of VeriTraceError are InputError, IntegrityError, DependencyError, ParserError, ModelError, ContextLimitError, WorkflowError and CitationError; each exposes a stable code and a printable message. Operational errors are not forensic labels.

| Contract | Required fields |
| --- | --- |
| Settings | model_base_url, model_name, num_ctx=4096, temperature=0.1, model_timeout_s=120, parser_timeout_s=120, parser_commands, parser_versions, parser_config_hashes, enabled_families, budget_profile |
| CaseManifest | schema_version=1, case_id, acquisition metadata, Windows/Edge/security metadata, optional testimony_reference_time/timezone, items and collection omissions |
| EvidenceItem | item_id, acquired_path relative to evidence/, original_path or explicit unknown, family, optional account/SID, optional supplied_sha256, calculated_sha256 populated at registration, companion_item_ids |
| RegisteredCase | manifest, testimony text, testimony_sha256, source root, working root, registered items with calculated hashes |
| EvidenceTime | role, raw_value, raw_encoding, raw_precision, normalized_utc or null, normalization_basis and uncertainty |
| SourceLocator | kind, identifiers dictionary, resolution status; identifies an original database row, Registry value, file/entry or validated parser item |
| EvidenceRecord | record_id, case_id, family, item_id, source_sha256, original_path, locator, times, account/SID if known, application, target, parser identity/config hash, raw fields and raw-output locator/hash |
| Claim | claim_id, sentence, start, end, action, target, actor, negated, time_expression, resolved_start/end or null, uncertainty, interpretation_notes |
| Assessment | claim_id, status, cited_record_ids, justification, alternative_explanations, limitations |
| CoverageEntry | item_id if applicable, family, status, record_count, companion handling and reason/error |
| ToolReceipt | sequence, claim_id if applicable, name, validated arguments, result/error, returned_record_ids, duration and cache status |
| RunResult | run_id, case_id, testimony, testimony_sha256, complete/partial/error status, claims, assessments, claim_errors, coverage, tool receipts, runtime/parser metadata and output paths |

Family identifiers: edge_history, lnk, jumplist, prefetch, userassist, recyclebin. Assessment identifiers: supported, contradicted, unverified, inconclusive. Coverage statuses: parsed, parsed-with-no-records, failed, unavailable-in-input, unsupported. Initial action identifiers: download_file, open_document, launch_program, recycle_file; preserve other interpretations as explicit unsupported actions.

These public interfaces are defined by their owning tasks and must not be renamed independently:

```text
OllamaClient.chat(messages, *, tools=None, schema=None) -> ModelTurn
OllamaClient.metadata() -> dict
ContextBudget.ensure(messages, tools, schema) -> None
benchmark(client, budget, *, trials=3) -> dict
register_case(input_dir: Path, output_dir: Path) -> RegisteredCase
verify_originals(case: RegisteredCase) -> None
stable_record_id(case_id: str, family: str, source_sha256: str, locator: SourceLocator) -> str
ParserRunner.run(command: list[str], output_dir: Path) -> ParserRun
ParserAdapter.extract(case: RegisteredCase, items: list[EvidenceItem]) -> ExtractionResult
extract_case(case: RegisteredCase, adapters: dict[str, ParserAdapter], index: EvidenceIndex) -> list[CoverageEntry]
EvidenceIndex.add(records: list[EvidenceRecord]) -> None
EvidenceIndex.search(case_id: str, filters: SearchFilters, cursor: str | None, limit: int=25) -> RecordPage
EvidenceIndex.get(case_id: str, record_id: str) -> EvidenceRecord
extract_claims(case: RegisteredCase, client: OllamaClient, budget: ContextBudget) -> list[Claim]
ToolBackend.dispatch(name: str, arguments: dict, *, claim_id: str | None) -> dict
ToolLedger.append(receipt: ToolReceipt) -> None
ToolLedger.returned_ids(claim_id: str) -> set[str]
validate_citations(case: RegisteredCase, assessment: Assessment, index: EvidenceIndex, ledger: ToolLedger) -> None
verify_claims(case, claims, client, budget, tools: ToolBackend) -> VerificationResult
render_report(result: RunResult, output_dir: Path) -> Path
run_case(input_dir: Path, output_dir: Path, settings: Settings) -> RunResult
evaluate_corpus(corpus_path: Path, output_dir: Path, settings: Settings) -> dict
macro_f1(expected: list[str], predicted: list[str]) -> float
```

ModelTurn holds content, tool_calls and server timing/token metrics, and implements as_assistant_message() to preserve provider content/tool-call fields without private thinking. SearchFilters holds family, literal target/path/URL text, account and explicit time bounds. RecordPage holds records, total and next_cursor. ParserRun holds command/version, exit code, duration, stdout/stderr paths and output hashes. ExtractionResult holds records and per-item coverage. VerificationResult holds assessments and per-claim operational errors. Define these alongside their relevant models.

## Task 1: Runnable package and local-model benchmark

**Files:** Create packaging/configuration files, errors.py, settings.py, runtime/client.py, budget.py, benchmark.py, cli.py, __main__.py, tests/test_runtime.py, tests/fakes.py and docs/setup.md.

**Interfaces:** Produces Settings, error classes, ModelTurn, OllamaClient, ContextBudget, benchmark, and doctor/benchmark CLI commands.

- [ ] **Step 1: Establish the selected branch/workspace, copy the design/plan, and create Python 3.12 packaging.** Dependencies are pydantic>=2,<3, httpx>=0.27,<1, jinja2>=3,<4 and a tokenizer dependency if required by the verified budget profile; development dependencies are pytest and build. Lock the resolved versions. Use the bundled interpreter in development, or a verified Python 3.12 installation on the desktop. Commands from the application checkout:

Start pyproject.toml with this package configuration and create src/veritrace/__init__.py before environment synchronization:

```toml
[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[project]
name = "veritrace"
version = "0.1.0"
requires-python = ">=3.12,<3.13"
dependencies = ["pydantic>=2,<3", "httpx>=0.27,<1", "jinja2>=3,<4"]

[project.scripts]
veritrace = "veritrace.cli:main"

[dependency-groups]
dev = ["pytest", "build"]

[tool.hatch.build.targets.wheel]
packages = ["src/veritrace"]

[tool.pytest.ini_options]
testpaths = ["tests"]
addopts = "-m 'not integration'"
markers = ["integration: requires acquired evidence, configured parsers and a live local model"]
```

```powershell
uv --cache-dir .uv-cache venv --python 'C:\Users\eugen\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe' .venv
uv --cache-dir .uv-cache lock
uv --cache-dir .uv-cache sync --frozen
```

- [ ] **Step 2: Write HTTP-mocked tests for schema requests, actual tool-call parsing, model-not-found, timeout, remote/cloud model metadata and over-budget input.** Do not expose a fake-runtime CLI option. The following payload check is the first test:

```python
def test_chat_does_not_stream_and_preserves_tool_calls(mock_transport):
    from veritrace.runtime.client import OllamaClient
    client = OllamaClient(mock_transport.settings, transport=mock_transport.transport)
    result = client.chat([{"role": "user", "content": "Check this case."}], tools=[])
    assert mock_transport.requests[0]["stream"] is False
    assert result.tool_calls[0]["function"]["name"] == "get_source_coverage"
```

Implement mock_transport as a pytest fixture using httpx.MockTransport: record chat request JSON in requests, provide version/tags/show metadata for a synthetic local tool-capable model, and return a complete chat message with get_source_coverage(case_id="case01"). A timeout handler raises httpx.ReadTimeout. A cloud-model metadata response must be rejected before sending case text.

- [ ] **Step 3: Run the runtime tests and observe the initial missing-package/function failures.** Run `uv --cache-dir .uv-cache run pytest tests/test_runtime.py -q`.

- [ ] **Step 4: Implement the transport and budget guard.** Use local /api/chat, /api/version, /api/tags and /api/show; verify the selected model is local, present and tool-capable. Retain digest, quantization, runtime version and template identity. Apply the timeout and translate HTTP/JSON failures into ModelError/DependencyError. The chat payload construction is:

```python
payload = {"model": settings.model_name, "messages": messages, "stream": False,
           "options": {"num_ctx": settings.num_ctx, "temperature": settings.temperature}}
if tools is not None:
    payload["tools"] = tools
if schema is not None:
    payload["format"] = schema
```

Discover thinking controls from model metadata; initially test think=false where supported and record the selection. Do not persist private thinking as report justification. ContextBudget includes system prompts, message framing, tools/schema and reserved output. Pin the tokenizer/template accounting profile and compare its estimates with server prompt_eval_count on short, Unicode and near-limit benchmark inputs. An unverified profile or oversized request raises ContextLimitError before a case prompt is sent; never silently cut text. Do not enable live agent execution until the pinned profile's accounting and truncation behavior have been checked.

- [ ] **Step 5: Implement a three-trial structured-output and real tool-call benchmark.** The host tool get_benchmark_fact(case_id) returns a freshly generated nonce unavailable in the prompt. Supply its schema, receive the model's call, validate arguments, execute it, append the tool result, and require the final JSON to reproduce the returned nonce. Record actual calls, repairs, timings, tokens, runtime metadata and failures. This is labelled a synthetic capability check, not forensic validation. The essential receipt check is:

```python
assert receipt["name"] == "get_benchmark_fact"
assert receipt["executed"] is True
assert final_json["nonce"] == receipt["result"]["nonce"]
```

The owner installs a recorded Ollama Windows version and runs `ollama pull qwen3:8b` on the desktop host. Stop the victim VM during the benchmark. Use `ollama ps` and server logs to record GPU/backend selection; do not infer GPU use from the installed card. [Ollama hardware documentation](https://docs.ollama.com/gpu) lists Vulkan as additional support; the RX 6750 XT still needs an actual measured run. LAN access is configured only after localhost succeeds, limited to the development machine and without public forwarding.

- [ ] **Step 6: Run tests, CLI checks and the owner-run benchmark.** Commands: `uv --cache-dir .uv-cache run python -m veritrace doctor --config veritrace.example.toml` and `uv --cache-dir .uv-cache run python -m veritrace benchmark --config veritrace.example.toml --output .runs/benchmark.json`. Doctor reports missing dependencies explicitly. Benchmark records successes/failures for every trial and a pass flag only when the selected runtime completes the required checks. If hardware/latency is unsuitable, record an adjusted local model/backend/context benchmark before continuing live analysis; deterministic backend work can continue independently.

- [ ] **Step 7: Commit the tested package/runtime slice.** Commit message: `feat: add local runtime checks and tool-call benchmark`.

## Task 2: Evidence registration, contracts and integrity

**Files:** Create cases/models.py, registry.py, integrity.py, evidence/models.py, agents claim/assessment models, tests/factories.py and tests/test_cases.py.

**Interfaces:** Produces RegisteredCase, EvidenceItem, EvidenceRecord, Claim, Assessment, registration/integrity functions and deterministic IDs.

- [ ] **Step 1: Define the contracts in the field table and test factories.** write_case(tmp_path, testimony, case_id="case01") writes testimony bytes, case.json and an evidence directory containing a synthetic History file; its manifest maps that file to the original Windows path. make_claim(sentence, start=0, **overrides) supplies all Claim fields; make_record(case_id="case01", **overrides) supplies all EvidenceRecord fields and a resolvable synthetic source/raw-output locator. Tests use these factories, not data from the user's real account.
- [ ] **Step 2: Add tests for Unicode/CRLF preservation, bad UTF-8, duplicate IDs, supplied-hash mismatch, missing declared files, traversal, Windows reparse points, overlapping output directories and an original changed after registration.** The preservation test is:

```python
def test_registration_preserves_decoded_bytes(tmp_path):
    from tests.factories import write_case
    from veritrace.cases.registry import register_case
    text = "I opened résumé.pdf.\r\nI did not delete it."
    source = write_case(tmp_path, text)
    case = register_case(source, tmp_path / "run")
    assert case.testimony == text
    assert case.testimony.encode("utf-8") == (source / "testimony.txt").read_bytes()
```

- [ ] **Step 3: Run `uv --cache-dir .uv-cache run pytest tests/test_cases.py -q` and confirm the new behavior initially fails.**
- [ ] **Step 4: Implement registration with explicit trust boundaries.** Decode testimony from read_bytes().decode("utf-8") so universal-newline conversion does not change spans. Reject invalid UTF-8 explicitly. Require safe case/item IDs; resolve acquired paths inside evidence/; original_path is provenance text and never selects a live path. Reject reparse points and evidence/output overlap. Hash originals, copy declared sources/companions to the working directory, compare copied hashes, and store metadata with unknown values retained. Use the following stable identity basis:

```python
identity = {"case_id": case_id, "family": family,
            "source_sha256": source_sha256, "locator": locator.model_dump(mode="json")}
record_id = hashlib.sha256(json.dumps(identity, sort_keys=True, ensure_ascii=False,
                                      separators=(",", ":")).encode("utf-8")).hexdigest()
```

Inventory and hash every supplied file, including undeclared files; assign unknown original paths/families explicitly rather than guessing them. RegisteredCase.manifest contains calculated hashes and inventoried items in its working metadata without changing the source case.json. verify_originals recalculates every registered source hash and raises IntegrityError on change. Refuse reuse of an existing output run directory so a later run cannot overwrite its audit trail. Store output/registration writes outside input paths. SQLite sidecars and Registry logs remain next to their working-copy parent source.
- [ ] **Step 5: Run case tests and commit.** Commit message: `feat: register cases with immutable evidence provenance`.

## Task 3: Controlled parser runner and source coverage

**Files:** Create parsers/base.py, runner.py, coverage.py, tests/test_parser_runner.py and tests/test_coverage.py.

**Interfaces:** Produces ParserRun, ExtractionResult, ParserAdapter, ParserRunner.run and extract_case; consumes registered working copies and an EvidenceIndex supplied by Task 5.

- [ ] **Step 1: Test process timeout, nonzero exit, malformed output, successful zero-record output, missing binary, input filenames with spaces/ampersands, per-item failure and unknown source inventory.** A tiny test helper executable is invoked through the test interpreter with arguments, records argv in its output, and can exit 3 or exceed a short test timeout. It never interprets a shell command.
- [ ] **Step 2: Run `uv --cache-dir .uv-cache run pytest tests/test_parser_runner.py tests/test_coverage.py -q` and confirm initial failures.**
- [ ] **Step 3: Implement the process boundary and coverage aggregation.** Commands come from host configuration and adapter-owned arguments, never testimony/model text. The process call is:

```python
completed = subprocess.run(command, cwd=output_dir, shell=False, timeout=timeout_s,
                           capture_output=True, text=True, encoding="utf-8", errors="replace")
```

Retain command, version/config hash, stdout/stderr, exit code and output hashes. Timeout, malformed schema and missing executable have distinct error codes. Continue other sources after a source-specific failure; an integrity failure ends analysis. Map valid empty output to parsed-with-no-records, not failed. Record missing companions without inferring that data was lost. Unknown files are inventoried as unsupported. An intermediate disabled family is advertised as unsupported, not silently treated as extracted.
- [ ] **Step 4: Implement extraction over every registered source in enabled coverage before any claim-specific queries.** Batch one family's working sources through its adapter where supported, retain per-item coverage, insert normalized records through EvidenceIndex.add, and recheck originals. Cache only when source hashes, parser/config versions and normalization version match; persist a receipt for a repeated extraction request even on a cache hit.
- [ ] **Step 5: Run tests and commit.** Commit message: `feat: add bounded parser execution and source coverage`.

## Task 4: Edge history/download adapter and first acquired sample

**Files:** Create parsers/edge.py, evidence/time.py, tests/test_edge.py, tests/test_time.py, synthetic fixtures and the initial docs/acquisition.md.

**Interfaces:** Produces EdgeAdapter.extract and typed timestamp helpers; consumes ParserRunner and the evidence contracts.

- [ ] **Step 1: Prepare one development sample, following Task 11's acquisition boundary.** The owner performs a known Edge PDF download, records the action on the investigator machine, preserves the victim disk and exports the Edge profile's History database and available companions. Keep this sample outside source control. Acquisition success is not inferred from the baseline configuration report.
- [ ] **Step 2: Pin a Hindsight build that supports restricted history/download extraction.** Capture `hindsight --help` and `hindsight --list-artifacts`; configure its executable/pinned Python script command. The adapter builds argument arrays with input profile directory, output prefix, JSONL format, and `--only history,downloads`. If the installed build lacks these capabilities, install a compatible pinned build or report DependencyError rather than parsing undeclared artefacts. [Hindsight's documented options](https://github.com/RyanDFIR/hindsight) are the reference, not an assumed Edge version compatibility guarantee.
- [ ] **Step 3: Write tests for visits/downloads, multiple records sharing URL/time, unsupported schemas, malformed JSONL, missing companions and timestamp precision.** Build a synthetic SQLite database with urls/visits and downloads/downloads_url_chains records and matching synthetic parser output. Test the ambiguous locator case:

```python
def test_ambiguous_source_rows_are_not_guessed(edge_case_with_duplicates, edge_adapter):
    result = edge_adapter.extract(edge_case_with_duplicates, edge_case_with_duplicates.manifest.items)
    assert result.records[0].locator.resolution == "ambiguous"
```

edge_case_with_duplicates is a pytest fixture containing two source rows matching the available parser fields; edge_adapter uses the synthetic runner in unit tests. Also test that an ISO value without a defensible timezone remains unnormalized rather than inheriting the investigator machine's timezone.
- [ ] **Step 4: Run `uv --cache-dir .uv-cache run pytest tests/test_edge.py tests/test_time.py -q` and confirm initial failures.**
- [ ] **Step 5: Normalize only visits/downloads with original identifiers and time roles.** Enrich missing native IDs through fixed, parameterized, read-only queries against the working History database: visits.id and its urls.id; downloads.id and relevant chain_index. Require unique matches. Preserve raw native timestamp values and the parser JSONL pointer/hash. Keep ambiguous/unresolved provenance explicit; such records cannot pass the source-citation guard. Use family/field-declared encodings, preserve raw sub-microsecond precision, and derive UTC only when defensible. SQLite recovery/checkpoint activity is allowed only on working copies and recorded with companion handling.
- [ ] **Step 6: Run the pinned parser against the acquired development sample.** Compare a download and visit with their database rows, verify original hashes before/after, and retain parser metadata plus compatibility findings. Do not label Edge execution or a download as proof that the PDF was read.
- [ ] **Step 7: Run adapter tests and commit.** Commit message: `feat: index sourced Edge history and downloads`.

## Task 5: Case-scoped SQLite queries

**Files:** Create evidence/index.py, tests/test_index.py and tests/test_time_filters.py.

**Interfaces:** Produces EvidenceIndex.add/search/get, SearchFilters and RecordPage; consumes EvidenceRecord and EvidenceTime.

- [ ] **Step 1: Test stable pagination across equal timestamps, literal wildcard characters, Unicode Windows paths, unknown timestamps, duplicate inserts, unknown IDs, cross-case IDs and a cursor reused with different filters.** The page boundary test is:

```python
def test_search_pages_have_no_duplicates(index_with_26_records):
    from veritrace.evidence.index import SearchFilters
    index = index_with_26_records
    first = index.search("case01", SearchFilters(), None)
    second = index.search("case01", SearchFilters(), first.next_cursor)
    assert len(first.records) == 25
    assert len(second.records) == 1
    assert {r.record_id for r in first.records}.isdisjoint(r.record_id for r in second.records)
```

index_with_26_records uses make_record from Task 2 and inserts records into a temporary SQLite index.
- [ ] **Step 2: Run `uv --cache-dir .uv-cache run pytest tests/test_index.py tests/test_time_filters.py -q` and confirm initial failures.**
- [ ] **Step 3: Implement an indexed record table and separate typed time rows.** Store full validated record JSON plus case/family/account/target search columns. Every query binds case_id and filter parameters. Literal substring search treats percent/underscore as text, not SQL wildcards; normalize Windows path search separately from case-sensitive URL path identity. Unknown time values are not assigned epoch dates. Use a stable timestamp/record-ID ordering and a cursor containing the case ID, filter fingerprint and last ordering key. Cap pages at 25, permit smaller pages, retain total and explicit next_cursor.

```python
row = connection.execute(
    "SELECT record_json FROM records WHERE case_id = ? AND record_id = ?",
    (case_id, record_id),
).fetchone()
if row is None:
    raise InputError("record_not_found", "The record does not exist in this case.")
```

- [ ] **Step 4: Run query tests and commit.** Commit message: `feat: query evidence with case boundaries and stable pagination`.

## Task 6: Testimony interpretation agent

**Files:** Create agents/claims.py, prompts/claims.txt and tests/test_claims.py.

**Interfaces:** Produces extract_claims; consumes registered testimony, Claim, OllamaClient and ContextBudget.

- [ ] **Step 1: Use ReplayClient from tests/fakes.py to test repeated sentences, multiple atomic actions, negation, unclear targets, relative dates without an anchor, unsupported actions, Unicode/CRLF offsets and two unsuccessful repairs.** ReplayClient.chat returns queued ModelTurn objects and records arguments; it has no production configuration route. A repeated-sentence test supplies an intentionally wrong span and checks the repair request rather than using text.find to silently relocate it.
- [ ] **Step 2: Run `uv --cache-dir .uv-cache run pytest tests/test_claims.py -q` and confirm initial failures.**
- [ ] **Step 3: Implement a schema-guided call and bounded validation.** The system prompt requires atomic claims, exact source sentences/spans, preserved qualifiers, unsupported action preservation, and unresolved ambiguity. Provide testimony and its reference-time metadata as case data. Acquisition time must never resolve a relative testimony date. After model validation, verify every span:

```python
if not (0 <= claim.start < claim.end <= len(case.testimony)):
    raise InputError("invalid_claim_span", "Claim offsets are outside the testimony.")
if case.testimony[claim.start:claim.end] != claim.sentence:
    raise InputError("claim_text_mismatch", "The claim sentence differs from its source span.")
```

Return validation details for at most two repair attempts; persist an operational extraction error after exhaustion. Check cumulative context for every call. Save prompt hashes and settings, not private thinking. Broader exploratory search windows are separate from asserted time bounds.
- [ ] **Step 4: Run tests and one local-model development testimony check after Task 1 passes.** Inspect wording/negation/time preservation against expected claims. Commit message: `feat: extract validated atomic testimony claims`.

## Task 7: Verification agent, real tools and citation guards

**Files:** Create agents/tools.py, verify.py, citations.py, prompts/verify.txt, tests/test_tools.py and tests/test_verification.py.

**Interfaces:** Produces ToolBackend, ToolLedger, VerificationResult, verify_claims and validate_citations. Consumes registration, extraction, query, claim and runtime contracts.

- [ ] **Step 1: Test a model-generated extract_case followed by retrieval, cached extraction, unknown tool, extra arguments, another case ID, premature queries, 12-call exhaustion, empty-evidence contradiction, unknown/unretrieved citations, wrong-case records, unresolved locators and context exhaustion.** The extraction refusal test is:

```python
def test_extract_refusal_is_an_error(registered_case, tools, budget):
    import pytest
    from tests.factories import make_claim
    from tests.fakes import ReplayClient
    from veritrace.errors import WorkflowError
    from veritrace.agents.verify import verify_claims
    client = ReplayClient.from_contents(["I can assess this without tools.", "No tools needed."])
    claims = [make_claim(registered_case.testimony)]
    with pytest.raises(WorkflowError):
        verify_claims(registered_case, claims, client, budget, tools)
    assert not tools.ledger.entries
```

Define fixtures registered_case from write_case/register_case, tools as the Task 7 backend over the temporary index and test adapter, and budget as a generous verified test profile. Add a matching positive test whose first queued turn requests extraction and whose ledger records actual dispatcher execution.
- [ ] **Step 2: Run `uv --cache-dir .uv-cache run pytest tests/test_tools.py tests/test_verification.py -q` and confirm initial failures.**
- [ ] **Step 3: Define the four JSON-schema tools and host dispatch.** Schemas are extract_case(case_id), search_records(case_id, filters, cursor, limit), get_record(case_id, record_id) and get_source_coverage(case_id). Require the registered case ID, forbid undeclared fields, constrain filters/limit, and count invalid requests toward limits. No tool accepts a filesystem path, executable, SQL or network address. Dispatch maps names to backend functions and logs receipts/errors with actual returned IDs. Search pages and detailed get_record responses both create retrieval receipts.
- [ ] **Step 4: Implement the extraction phase and per-claim loop.** Only the model's validated extraction request invokes extraction; allow one missing-call correction then WorkflowError. Process tool batches sequentially. For each claim start a fresh context with its interpretation, coverage, role rules and explicit retrieved-record set. The core loop structure is:

```python
turn = client.chat(messages, tools=tool_schemas)
messages.append(turn.as_assistant_message())
for call in turn.tool_calls:
    result = tools.dispatch(call["function"]["name"], call["function"]["arguments"],
                            claim_id=claim.claim_id)
    messages.append({"role": "tool", "tool_name": call["function"]["name"],
                     "content": json.dumps(result, ensure_ascii=False)})
```

ModelTurn.as_assistant_message preserves content/tool-call data needed by the provider and omits private thinking. Track each actual call and check ContextBudget before every request. Keep the complete ledger on disk; narrow future queries or report context exhaustion without cutting source text or evidence fields. Pagination limits and context failures are visible to the agent/report.
- [ ] **Step 5: Validate final assessment JSON with up to two repairs.** Supported, contradicted and inconclusive require cited records; a contradiction cannot be justified solely by missing coverage. Verify each ID exists in this case, was actually returned for this claim, and has a resolvable source locator and preserved raw-output location. These mechanical checks do not establish relevance: assessment quality is evaluated in Task 12. The role prompt explains all four labels, timestamp roles, source dependence, absence limits and account-versus-person attribution. Preserve alternative explanations and limitations. Exhausted repairs produce claim_errors, not invented inconclusive/unverified labels.
- [ ] **Step 6: Run tests and an actual model/tool run over the development Edge case.** Check tool receipts and every displayed source ID. Commit message: `feat: verify testimony through logged forensic tool calls`.

## Task 8: Reusable service, CLI and escaped offline report

**Files:** Create service.py, report/render.py, report/templates/report.html, complete cli.py, tests/test_service.py, tests/test_report.py and docs/manual.md.

**Interfaces:** Produces run_case and render_report; consumes RunResult and all earlier contracts. No backend function depends on interactive terminal prompts.

- [ ] **Step 1: Write service tests for successful runs, one failed source, model unavailability, claim errors, integrity failure and complete JSON exports.** Write report tests for hostile source text, literal paths, embedded record anchors, coverage/error banners and missing citations. The HTML test is:

```python
def test_case_text_is_escaped(run_result, tmp_path):
    from veritrace.report.render import render_report
    result = run_result.model_copy(update={"testimony": '<script>alert("x")</script>'})
    html = render_report(result, tmp_path).read_text(encoding="utf-8")
    assert '<script>alert("x")</script>' not in html
    assert "&lt;script&gt;" in html
```

Populate RunResult.testimony and testimony_sha256 from the registered case. run_result is a complete synthetic result fixture with resolved citations/coverage. Use the standard-library HTMLParser to collect generated anchors and assert every assessment link resolves; do not merely compare template text.
- [ ] **Step 2: Run `uv --cache-dir .uv-cache run pytest tests/test_service.py tests/test_report.py -q` and confirm initial failures.**
- [ ] **Step 3: Implement the service and output contract.** Register/hash, extract claims, execute verification/extraction, validate citations, check originals again and render. Always preserve run metadata and errors after registration succeeds; avoid presenting integrity-compromised records as validated findings. Export report.html, claims.json, assessments.json, coverage.json, run.json, tool_calls.jsonl, evidence.sqlite and raw parser outputs. Run metadata includes enabled coverage, model/runtime/digest/quantization, prompt/config hashes, timing/token/resource measurements where available and unknowns otherwise. Final state is complete, partial or error.
- [ ] **Step 4: Implement escaped rendering and command routing.** Use Jinja2 autoescape, inline CSS, generated safe record-ID anchors and no remote scripts/assets. Show testimony beside interpretation, assessments/citations/alternatives/limits, coverage and operational errors. Case text cannot supply link URLs or trusted HTML. CLI commands are doctor, benchmark, run and later evaluate. Exit codes: 0 completed, 2 invalid input/configuration, 3 dependency/model/workflow failure, 4 partial run. The backend service still returns typed results for non-CLI callers.

```powershell
uv --cache-dir .uv-cache run python -m veritrace run --case .cases/dev01 --output .runs/dev01 --config veritrace.example.toml
```

- [ ] **Step 5: Verify the first Edge-only acquired-case report with actual model/tool calls.** Inspect the report in a browser, resolve one visit/download citation to the working database and preserved original, confirm the unsupported-family disclosure, and check source hashes. Do not present this intermediate milestone as the six-family prototype.
- [ ] **Step 6: Run service/report tests and commit.** Commit message: `feat: generate investigator reports through a reusable case service`.

## Task 9: LNK, Jump List, Prefetch and Recycle Bin adapters

**Files:** Create parsers/lnk.py, jumplist.py, prefetch.py, recyclebin.py, tests/test_windows_adapters.py, versioned synthetic/golden parser fixtures and parser configuration examples.

**Interfaces:** Produces LnkAdapter, JumpListAdapter, PrefetchAdapter and RecycleBinAdapter, each implementing ParserAdapter.extract.

- [ ] **Step 1: Install/pin LECmd, JLECmd, PECmd and RBCmd from their official distributions.** Record executable hashes, versions, required runtime and help output. Use each tool's supported file/directory input and explicit CSV/JSON output directory/name. Run only supplied working-copy sources, not the live machine. Capture actual output headers/schema on a known lab sample before writing field maps; retain the mapping with its version hash.
- [ ] **Step 2: Write per-family tests for a genuine target/time record, valid empty output, corrupt source, schema mismatch and precise provenance.** Include both automatic/custom Jump Lists, multiple Prefetch runtime slots and Recycle Bin metadata without its corresponding content file. Parameterize the common contract test:

```python
import pytest

@pytest.mark.parametrize("family", ["lnk", "jumplist", "prefetch", "recyclebin"])
def test_adapter_has_resolvable_original_and_raw_output(family, adapter_case, adapters):
    case = adapter_case(family)
    result = adapters[family].extract(case, case.manifest.items)
    record = result.records[0]
    assert record.locator.resolution == "resolved"
    assert record.source_sha256 == case.manifest.items[0].calculated_sha256
    assert record.raw_output_locator["path"]
```

Use the calculated_sha256 recorded by registration in Task 2. adapter_case writes controlled source fixtures and raw exports; adapters inject the test runner. Add family-specific assertions for target identity, timestamp role and parser/raw-output locator, using expected values independently transcribed from the source sample.
- [ ] **Step 3: Run `uv --cache-dir .uv-cache run pytest tests/test_windows_adapters.py -q` and confirm initial failures.**
- [ ] **Step 4: Implement the versioned mappings.** LNK records cite their source file and validated parser item; Jump Lists cite the original file plus stream/entry identifiers when available, with an explicit raw-item locator otherwise; Prefetch execution traces retain each reported runtime slot and its meaning; Recycle Bin records retain original path, deletion time, source metadata file and content-companion presence. Do not equate deletion-to-Recycle-Bin with permanent deletion or assume Prefetch establishes a human actor. Reject unsupported output schemas rather than filling guessed fields. Build IDs through stable_record_id and apply Task 4 time helpers only to declared encodings/bases.
- [ ] **Step 5: Enable each family only after its acquired-sample comparison passes.** Re-run the case service, verify all supplied items were processed independently of testimony, and check originals. Commit each adapter's validated slice separately with message `feat: add sourced <family> evidence adapter`, using the concrete family name.

## Task 10: Decoded Registry UserAssist adapter

**Files:** Create parsers/userassist.py, versioned UserAssist batch/configuration instructions, tests/test_userassist.py and update docs/setup.md.

**Interfaces:** Produces UserAssistAdapter implementing ParserAdapter.extract; consumes retained hive/log working copies and known account mapping.

- [ ] **Step 1: Pin RECmd and a demonstrated UserAssist-capable plugin/configuration.** Inspect the official batch examples and installed plugin capabilities; create a minimal pinned configuration restricted to the UserAssist keys. Record configuration/plugin hashes. Do not guess a batch-file name or claim generic Registry search provides decoded UserAssist support. [RECmd documentation](https://github.com/EricZimmerman/RECmd) is the initial reference.
- [ ] **Step 2: Write tests with independently verified decoded target, raw encoded value name, Registry key/value locator, runtime/counter semantics, account mapping, retained transaction logs and an unavailable decoder.** The missing-decoder fixture must produce a dependency/coverage failure rather than parsed-with-no-records.
- [ ] **Step 3: Run `uv --cache-dir .uv-cache run pytest tests/test_userassist.py -q` and confirm initial failures.**
- [ ] **Step 4: Implement the restricted adapter.** Preserve raw names/data and the plugin's decoded fields, source hive hash, complete key/value identity, plugin/version metadata and raw-output locator. Mark plugin-specific time/counter limits explicitly. Never use Registry key last-write time as a substitute for an action timestamp. Account/SID is taken from known source metadata; it is not guessed from the analyst's current account. Log replay operates on copies with supplied companions and is recorded.
- [ ] **Step 5: Compare a known GUI launch in the victim against the decoded hive value, then enable userassist.** The final enabled coverage is now the six design families. Run all adapter tests and a complete-source acquired-case service run. Commit message: `feat: add decoded and sourced UserAssist records`.

## Task 11: Reproducible acquisition rehearsal and real-case integration

**Files:** Complete docs/acquisition.md, add examples/case.json and tests/test_acquired_case.py. Real acquisitions and ground-truth logs remain outside source control.

**Interfaces:** Produces a documented acquisition procedure and a real development case conforming to CaseManifest. Consumes the six enabled adapters and run_case.

- [ ] **Step 1: Rehearse preservation/export on a disposable development experiment before collecting the evaluation corpus.** Check host storage for the VM, model weights, acquisition copies and retained RAM dumps without using the excluded physical spare SSD. Record VMware 17.6.1 product/edition, actual snapshot identifier, FTK Imager version and the chosen disk-preservation/export method. For a stopped-VM preservation method retain the complete required VM/disk snapshot chain; do not assume a single base VMDK contains the current state. Demonstrate that the preserved copy can be examined and supported source files exported. If the installed image reader cannot open that representation, resolve the conversion/access procedure on the copy and document it before using it for evaluation. This is manual acquisition, not application disk-image ingestion.
- [ ] **Step 2: Select/test a Windows-compatible RAM capture tool on the disposable case.** Record its official source, version/hash, output destination and capture start/end times; retain the dump and SHA-256. Capture before shutdown/restart and document live-collection effects. No RAM interpretation is performed by the prototype. The exact capture utility is a feasibility result; do not invent a successful capture from a snapshot or configuration report.
- [ ] **Step 3: Define the owner-run experiment sequence in the manual.** Restore the confirmed experiment baseline, check guest/host clocks, record test start on the investigator machine, download a known harmless PDF in Edge, open the downloaded local PDF, launch Notepad through the GUI, and delete the PDF to the Recycle Bin. Record actual paths/URLs, hashes, account, action times and observed outcomes on the investigator machine. Avoid adding the ground-truth script/log to agent input.
- [ ] **Step 4: Preserve RAM and disk, then export supported files from the preserved disk.** Include all applicable Edge profiles, relevant hives/logs, LNK files, automatic/custom Jump Lists, Prefetch and Recycle Bin metadata/available content companions. Record absent/uncollected sources and reasons. Preserve original Windows path mappings; register/hash the exported files. Retain the original acquisition and work only on copies. The manifest must include snapshot/acquisition identities and the recorded baseline configuration.
- [ ] **Step 5: Run an opt-in integration test with the real model and parsers.** The test requires explicit local fixture/config paths and never runs automatically in unit CI. Assert the required extraction receipt exists, all supplied supported items have coverage entries, every displayed citation resolves to retrieved records and source/raw-output locations, and original hashes remain equal. Manually check one record from each present family against the source. Missing families are not silently credited as validated.

```powershell
uv --cache-dir .uv-cache run pytest -m integration tests/test_acquired_case.py -q
```

- [ ] **Step 6: Run source-removal and malformed-source variants of the development case.** Assert absence alone does not yield contradicted; malformed-source errors are explicit; retained positive evidence can still support a qualified assessment. Keep variants associated with their base case.
- [ ] **Step 7: Commit the acquisition manual, public synthetic manifest example and opt-in integration test.** Commit message: `test: validate the prototype on preserved victim acquisitions`.

## Task 12: Evaluation, packaging and project delivery

**Files:** Create evaluation/metrics.py, corpus.py, tests/test_metrics.py, tests/test_corpus.py; complete README.md, docs/manual.md, evaluation.md and delivery.md.

**Interfaces:** Produces evaluate_corpus and macro_f1, evaluate CLI, reproducible metrics and a runnable distribution. Consumes run_case and frozen labelled corpus metadata.

- [ ] **Step 1: Create and independently review the corpus labels.** Target six independent acquired cases: three development and three held-out, at least ten claims each. Preserve both actual action ground truth and evidence-aware expected assessments. Include true, false/negated, unclear-time/target and unsupported claims, plus source-removal/corruption variants. Two team members review labels independently and record resolutions. Freeze model/prompts/parser settings before held-out runs; base cases and every variant stay in the same split.
- [ ] **Step 2: Test split leakage, contradictory labels for missing-only evidence, citation-existence versus relevance denominators, and metrics that retain operational failures.** A perfect balanced classification test is:

```python
def test_macro_f1_for_all_four_correct_labels():
    from veritrace.evaluation.metrics import macro_f1
    labels = ["supported", "contradicted", "unverified", "inconclusive"]
    assert macro_f1(labels, labels) == 1.0
```

Add a test with all predictions operational_error and expect macro-F1 0, plus a known partially correct confusion matrix with independently calculated expected values.
- [ ] **Step 3: Run `uv --cache-dir .uv-cache run pytest tests/test_metrics.py tests/test_corpus.py -q` and confirm initial failures.**
- [ ] **Step 4: Implement corpus checking and metrics.** Report a four-truth-class confusion table with a separate operational-error prediction column, macro-F1, classification accuracy and operational failure rate. Zero denominators yield 0 with an explicit policy note. Include field correctness, known-record retrieval, actual tool success/count, source-span preservation, citation existence, human relevance/sufficiency, latency/resource data and repeated-run agreement with denominators. The class F1 calculation includes errors as false negatives:

```python
for label in labels:
    tp = sum(e == label and p == label for e, p in zip(expected, predicted, strict=True))
    fp = sum(e != label and p == label for e, p in zip(expected, predicted, strict=True))
    fn = sum(e == label and p != label for e, p in zip(expected, predicted, strict=True))
    scores.append(0.0 if 2 * tp + fp + fn == 0 else 2 * tp / (2 * tp + fp + fn))
```

macro_f1 defines labels as the four assessment identifiers and returns sum(scores)/4. The evaluator treats a missing/failed assessment as operational_error, never excludes it to improve accuracy. Keep human relevance ratings separate from machine ID validation.
- [ ] **Step 5: Run the frozen evaluation and manual baseline.** Compare a timeline/keyword workflow over the same available records. Record participant experience and counterbalance order/cases where participants are available; otherwise label descriptive findings accordingly. Save exact run configurations, outputs and corpus split hashes. Do not claim time or accuracy improvement without measured results.
- [ ] **Step 6: Package and test a clean installation.** Build with `uv --cache-dir .uv-cache run python -m build`; install the wheel in a new Python 3.12 environment, run CLI help/doctor and a documented acquired-case command with external prerequisites. The manual explains installation, local model setup, parser/version configuration, input layout, source coverage, four labels, errors, output locations and reproduction. Model weights and parser binaries remain separate prerequisites unless redistribution rights are checked.
- [ ] **Step 7: Complete the delivery checklist without inventing results.** GitHub source/runnable distribution/manual; 6-10-page IEEE Word/PDF report with at least 70% journal/conference references; 5-10-minute subtitled 1080p video; generative-AI-use statement; deadline 29 November 2026. Reserve the final two weeks for evaluation, report, packaging and video. Academic report/video production follows measured evaluation; disk-image ingestion, RAM analysis, cloud isolation, UI and stronger prompt-injection defences are clearly labelled later work until separately implemented/tested.
- [ ] **Step 8: Run the appropriate full checks once, review the final branch and commit.** `uv --cache-dir .uv-cache run pytest -q` excludes opt-in integration tests by default; explicitly run the real integration check when prerequisites exist. Inspect `git diff --check` and the distribution contents. Commit message: `feat: add reproducible evaluation and prototype delivery documentation`. Obtain an independent whole-branch review under the selected execution workflow before any later merge/publication decision.

## Self-review and readiness

Spec coverage: purpose/lab constraints -> global constraints and Tasks 1/11; case/acquisition boundary -> Tasks 2/11; six-family parsing and coverage -> Tasks 3/4/9/10; claims/provenance/timestamps -> Tasks 2/4/6; actual tools, limits and citations -> Tasks 1/5/7; assessment meanings/attribution -> Tasks 6/7/12; HTML/reusable backend -> Task 8; evaluation/acceptance -> Tasks 11/12; later scope and rubric -> Task 12; recorded baseline -> acquisition manifest in Task 11. No product implementation or desktop benchmark has been performed by writing this plan.

Execution readiness: the architecture and victim baseline are sufficient to begin. Early checks must establish desktop runtime performance, a defensible prompt-budget profile, supported parser schemas/provenance and a tested acquisition procedure. These are measured implementation tasks. Owner-run desktop steps can be pending while deterministic backend development proceeds; live-model and acquired-case success must remain unclaimed until their checks actually pass.
