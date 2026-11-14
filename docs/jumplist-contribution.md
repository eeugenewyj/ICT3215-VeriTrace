# Jump List support for Agent 2

The contribution connects acquired Windows Jump Lists to bounded, traceable
Agent 2 evidence searches. It builds on the existing JLECmd parser and preserves
the original evidence, full normalized records and tool audit results.

## Controlled development sample

On 14 November 2026 the owner opened JL01-notes.txt in Notepad in the Windows 10
victim VM, observed it under Recent, and closed Notepad. JL01-budget.txt was the
comparison file to leave unopened in applications. File preparation and hashing
are separate from the recorded document-opening experiment.

The owner captured RAM before shutdown, verified its transfer, shut down the
victim and exported Jump Lists from the newly preserved disk using FTK Imager.
Ground truth remains outside agent input. The exports contain four automatic
and four custom Jump Lists plus two NTFS index extras. Actual JLECmd execution
produced 20 records: five populated sources and three valid empty custom lists.
Independent OLE/byte reads checked the records with zero mismatches; acquired
exports and registered inputs remained unchanged.

The notes file appears in both Notepad and Quick Access lists. The Notepad
entry's DestList modification time is 13:40:27.202372 UTC, or 21:40:27 in
Singapore, inside the owner's recorded opening interval. No matching budget-file
target occurs in these supplied Jump List records. This absence does not prove
that a document was never opened.

## Implementation

| File | Contribution |
| --- | --- |
| src/veritrace/agents/hints.py | Builds a proposed search call with case_id and nested filters. The model still makes the actual request; arguments are not silently rewritten. |
| src/veritrace/agents/verify.py | Supplies that hint, passes the case timezone to model-facing evidence views, and applies record-reference compaction after tool responses. |
| src/veritrace/agents/context.py and src/veritrace/service.py | Replace only identical repeated record projections with explicit references to retained details; keep full audit receipts and record the policy/count in run metadata. |
| src/veritrace/agents/tools.py | Describes Jump Lists as application-associated destinations/tasks, retains application and automatic/custom identity, presents the relevant activity time in UTC/local time, and limits repeated metadata. |
| src/veritrace/agents/timecheck.py | Uses DestList modification context for document-opening clock comparisons; target-file and UUID-derived dates cannot satisfy that check. |
| src/veritrace/prompts/verify.txt | Explains argument structure, timestamp meanings, application-label limits and the approved supported/contradicted/unverified/inconclusive rubric. |
| src/veritrace/prompts/claims.txt | Clarifies that action categories are not a checklist to enumerate and that stated clock times are local to the supplied timezone. |
| pyproject.toml and uv.lock | Declare and lock tzdata so Windows can resolve IANA zones such as Asia/Singapore. |
| tests/test_jumplist_context.py, tests/test_hints.py and tests/test_context.py | Check application context, argument validity, timestamp roles, timezone conversion, specific warnings, lossless duplicate references, unchanged tool receipts and valid citations. |

Search results give concise record IDs, targets, application associations and
activity times. get_record gives selected additional fields, including entry
identity, interaction count, pin status and relevant arguments/notes. Noninteraction
timestamp values are omitted from the model projection; their roles are listed
in the detailed view. Full timestamps, raw fields and limitations remain in the
index, audit result and investigator report. Record-specific warnings are kept
in the model view; repeated general rules are supplied in the system prompt.

Application names are JLECmd lookup labels. A Quick Access or static custom-task
entry must not be treated as proof that Notepad opened a document. DestList
modification is activity context; it is not independently sufficient to identify
a human actor or establish that document contents were read.

The approved rubric defines supported as positive relevant evidence consistent
with interpreted activity at the claim's target/time precision, with explicit
limits. It does not require certainty or a direct opening event log. Relevant
but genuinely ambiguous evidence belongs under inconclusive; missing sufficient
relevant evidence belongs under unverified. Absence alone never contradicts.
No host rule promotes a matching Jump List to supported. The model still judges
the retrieved evidence, and its classifications need independent evaluation.

Context compaction compares JSON values exactly, including boolean/number
distinctions. Search rows may reference a retained full projection only when
every field is identical; unique fields, pagination and errors are preserved.
Repeated identical full projections reference the latest complete response.
Original records and tool receipts are retained in full. This reduces repeated
context without silently dropping unique evidence or changing citation IDs.

## Verification on this desktop

The normal suite reports **159 passed, 1 integration deselected**. A fresh
enabled acquired-case integration check reports **1 passed, 159 deselected**,
using the live local model, installed parser, resolvable citations and unchanged
registered originals.
The integration repeat again returned qualified support for the notes-file
claim without a context-budget stop. The separate audit checks all three latest
outputs' citations, original hashes, HTML fragment links and lack of external
assets, plus the hashes of all ten acquired exports. It is retained in
.runs/disk-jumplist01/parser-validation01/assessment-fix-verification.json.

Ollama had changed from 0.35.0 to 0.40.16, so the old budget profile correctly
blocked case execution. A fresh genuine benchmark passed all three tool trials
and retention/token probes using the already-installed qwen3:8b at 4,096 tokens,
with the victim stopped. Real conversations still reached that limit. A new
8,192-token benchmark then passed the same three trials and all probes before
case inference. The focused 8,192-token configuration points to its verified
profile. The general private configuration was left unchanged.

Two host-prepared development testimonies were run through both real agents:

| Case | Statement | Observed result |
| --- | --- | --- |
| jumplist01a | Opened JL01-notes.txt at 21:40 on 14 November | Complete workflow; supported with two citations and explicit limits. It reports matching activity at 21:40:27 as consistent with opening, without claiming direct proof. |
| jumplist01b | Opened JL01-budget.txt at the same time | Complete workflow; unverified assessment without citations, rather than contradiction from missing evidence. |

Latest runs extract one opening claim each at the stated local time, with no
tool errors or retrieval-budget stops. Earlier attempts are retained, including
argument errors, wrong timestamp interpretation, context exhaustion and an
overly strict unverified verdict despite matching evidence. Another repeat,
agent05b, invented extra actions and misresolved the local time. Agent 1's
instructions were clarified, but successful later runs do not establish that
the semantic extraction problem is eliminated. These are development examples,
not held-out accuracy measurements. Classification, extraction, relevance,
sufficiency, attribution and repeatability require independent evaluation.

## Local artefacts and reproduction

Acquisitions, tools, cases and private configuration are ignored by Git and do
not accompany a clone. On this desktop:

- .runs/disk-jumplist01/parser-validation01: inventories, native comparisons,
  action correlation, test receipts and integration preparation.
- .external/parser-profiles/jumplist-2026.5.0-jumplist01.json: independently
  validated candidate for the current normalizer.
- .runs/jumplist01-preparation/veritrace.jumplist01-8k-validated.toml: latest Jump List-only settings.
- .runs/jumplist01-agent06a and .runs/jumplist01-agent06b: latest development reports.
- .runs/jumplist01-integration-test02: latest acquired integration-test output;
  integration-test01 retains the earlier result.
- .runs/disk-jumplist01/model-benchmark01.json and its budget profile: current
  local-runtime evidence at 4,096 tokens; model-benchmark03-8k.json and its budget
  profile validate the larger context used in the latest runs.

Run the unit suite from the repository:

```powershell
.\.venv\Scripts\python.exe -m pytest -q
```

To repeat the acquired case, keep the victim stopped and choose a fresh output:

```powershell
.\.venv\Scripts\python.exe -m veritrace run --config .runs\jumplist01-preparation\veritrace.jumplist01-8k-validated.toml --case .cases\jumplist01a --output .runs\jumplist01-review01
```

The general desktop configuration still needs its older model/profile references
revalidated before a broader multi-family run. Direct image ingestion and RAM
interpretation remain outside this prototype. See the approved design and the
current implementation-status document for the remaining acceptance work.
