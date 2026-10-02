# Implementation and validation status

Updated 2 October 2026. Development is inline in the existing checkout on
codex/veritrace-prototype, starting from d1e2b36. Changes are local; no GitHub
push or merge has been performed. This is an implemented backend prototype,
with live-model and acquired-evidence acceptance checks still pending.

## Implemented locally

- Python 3.12 package and doctor/benchmark/run/evaluate commands.
- Local Ollama API boundary, model identity checks and runtime-bound prompt budget.
- Immutable case registration, working copies, source inventories and hashes.
- Controlled parser subprocesses, retained output/diagnostics, coverage and cache.
- Six source-derived adapter mappings, typed timestamps and scoped SQLite queries.
- Exact testimony spans, bounded model/tool loops and claim-specific citation checks.
- Escaped offline HTML plus JSON, index and tool-call audit outputs.
- Reviewed corpus schema and evaluation that retains operational failures.

The final local suite reported **88 passed, 1 integration test deselected**.
The real pinned Hindsight subprocess smoke check produced **63 records, all 63
resolved**, on its upstream Chromium 60 fixture. This is not the victim's Edge
154 evidence. Wheel/source-archive builds and isolated wheel installation have
been checked; CLI help works, and doctor correctly reports the absent local
Ollama server. The final release verification record is retained locally.

Browser layout QA used a prominently labelled synthetic fixture at desktop and
390-pixel widths. Internal citation anchors resolved; no external assets were
requested. A long-hash overflow was corrected and report escaping/link tests
were rerun successfully. This preview is not a genuine forensic assessment.

## Fresh review and rulings

An independent whole-branch review covered d1e2b36..30b5a30. Its verdict was
"with fixes". All nine material findings received a single regression-tested
fix pass; no cosmetic findings or deferred minor fixes were reported.

| Finding | Resolution |
| --- | --- |
| Final JSON grammar applied to native tool turns | Separate retrieval and schema-only finalization; benchmark the same stages, their token counts and retention. Require a successful search for each claim. |
| Evaluation writes could overlap another acquired input | Preflight every output against all corpus inputs and label/configuration/prerequisite files, checking reparse ancestors before writes. |
| Partial Edge exports reported complete | Reconcile every supported native visit/download row ID; missing or ambiguous identities fail that source and retain its raw export. |
| Unrelated hashes could authorize a PATH command | Resolve actual command files, require their hashes and execute absolute pinned paths. Module/inline dispatch is unsupported. |
| Malformed nested provider calls aborted reporting | Validate tool-function envelopes and model inventories at the API boundary; preserve explicit operational error reports. |
| Failed cases vanished from retrieval denominator | Derive known-relevant totals from all labels before running cases; failures contribute zero retrieval and comparison rows. |
| One prediction could satisfy several atomic labels | Enforce one-to-one alignment; ambiguous labels are errors. Explicit atomic occurrence indexes are available, with target/negation measured separately. |
| Renamed WAL/Registry logs ignored | Resolve declared companions by original-source role, stage them under parser-required names, record hashes/IDs and missing roles; reject ambiguous roles. A real SQLite WAL fixture tests retained committed rows. |
| Equal bytes from distinct profiles collided | Bind record IDs to source item identity as well as case/family/hash/locator, preserving distinct accounts and citations. |

The native protocol issue was identified from provider/parser behavior, not
observed on the desktop. Its live selected-version check remains pending.
The review explicitly did not certify desktop GPU performance, victim parser
accuracy, acquisition feasibility, human relevance or measured forensic benefit.
CodeRabbit CLI was unavailable; no CodeRabbit review was claimed or case data
uploaded. Review used a fresh read-only agent under the execution workflow.

Implementation rulings carried forward:

1. User-selected inline execution takes precedence over worktree defaults.
2. Owner checks may remain pending while independent backend work proceeds.
   Missing results never become fabricated passed gates.
3. The initial UTF-8 estimate was too restrictive at 4,096 tokens; a pinned
   tokenizer plus empirical overhead is supported. The runtime/model/template/
   tokenizer/context/protocol profile requires observed counts and retention.
   It is not an exact rendering of every provider template.
4. Inspected UserAssist plugin output does not include binary value bytes;
   retain encoded names and exact hive locators, with bytes preserved in the hive.
5. Six mappings were derived from pinned official source and controlled export
   fixtures. Their acquired-sample gates remain closed until manually validated.
6. Windows staging/copy tooling and an ignored execution ledger replace shell
   helpers incompatible with this environment; the ledger is retained because
   the full implementation plan still has owner-run acceptance work outstanding.

## Pending acceptance work

| Work | Required evidence |
| --- | --- |
| Desktop model | Install Ollama, download qwen3:8b, pass the synthetic benchmark; retain model/runtime identity, ollama ps and GPU/resource observations. |
| Victim acquisition rehearsal | Preserve RAM before shutdown, preserve the required VM disk/snapshot chain, demonstrate FTK/export access and record hashes/tools/times. |
| Parser deployment | Actual binaries/runtime/help/export schemas, dependency pins and one independently compared victim sample for each present family. |
| Genuine end-to-end run | Local model-generated extraction/retrieval receipts, report/source checks, unchanged originals and opt-in acquired integration test. |
| Evaluation | Reviewed development/held-out corpus, frozen configuration, source-removal variants, independent relevance/sufficiency ratings, repeatability and manual baseline. |
| Submission | Measured-results IEEE report, AI-use statement, final package/manual and subtitled demonstration video. |

No classification accuracy, investigation-time improvement, GPU compatibility
or six-family victim-validation result has been measured yet. Direct disk-image
ingestion and memory interpretation are future milestones; current input is an
acquired artefact folder.
