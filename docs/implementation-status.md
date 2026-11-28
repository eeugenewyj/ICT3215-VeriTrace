# Implementation and validation status

Updated 28 November 2026 after controlled development tests and integration of
upstream commits 737b03e (denials and uncertainty) and 5e8cd16 (clock checks).
Fresh native pipeline and bounded tool-limit validation are recorded below.

## Current desktop checkpoint: fresh native pipeline checks

The latest merged code was exercised through the actual CLI, local qwen3:8b and
all six configured native parsers on the existing standard01 acquisition. The
six selected scenarios cover the five-positive baseline, wrong day, wrong clock,
approximate wrong clock, download denial and compound denial/no-recall wording.
Each uses a fresh output directory; no external parser-output cache or recorded
model response is substituted. Ordinary within-run extraction caching remains
part of the product. The VM is checked stopped before each inference request.

The first six runs produced 12 claims and 11 assessments. All fresh native
source-derived fields matched the earlier 238-record corpus. The wrong-day
assessment was inconclusive; exact/approximate wrong clocks and the download
denial were contradicted. The compound case returned supported, contradicted
and inconclusive. One baseline opening claim exhausted its twelve-tool-call
allowance after successful searches and lost its assessment; that failed run is
retained in `.runs/standard01-development06-native/`.

The bounded fix stops retrieval at the existing cap and requests a schema-only
assessment from returned evidence, preserving citations, early-stop limitations
and the two-repair budget. Missing successful searches still produce an error.
Five new regressions reproduced the original failure; the isolated preview and
actual project both pass **358 tests, one integration test deselected** after
the fix. The second six-scenario native/model run completed all **12 assessments**:
five supported baseline claims, an inconclusive wrong-day claim, contradicted
exact/approximate wrong-clock claims, a contradicted download denial, and
supported/contradicted/inconclusive compound-case assessments. No run, claim or
tool errors occurred. The formerly missing PDF-opening assessment reached the
same twelve-call cap, then finalized with validated citations and an explicit
early-stop limitation; the cap was not increased.

All six fresh 238-record corpora matched the reference fields. Original export
hashes, all six case inputs, actual model-facing interpretations, dates/clock
precision, citations and offline report links were checked. The largest observed
provider prompt was 5,322 tokens with the 8,192-token context/768-token response
cap unchanged; no response was length-limited. Reviewed reports retain 143 parsed
Prefetch inputs and 41 source-bound explanations. The results and completion
audit are `.runs/standard01-development07-native/comparison.html` and
`completion.json`.

One baseline opening explanation overstates browser-download/deletion context
alongside its LNK/Jump List citations. A source-bound note flags that wording for
independent relevance/sufficiency and attribution review; the model output is
unchanged. Citation identity checks do not certify reasoning. Two actual human
reviews remain pending; the separate worksheets contain 31 blank atomic slots
across 15 development scenarios on one acquisition. No formal accuracy, held-out
result or investigation-time improvement is claimed. The exact validated source
fingerprint and original reports are retained in the private run pack.

## Earlier desktop checkpoint: controlled development tests

The latest merge combines the incoming bounded case-index clock-mismatch check
with the existing calendar and generic-target guards. Date-only statements do
not enable clock contradiction, and records found only on another local day
leave the time assessment inconclusive. Same-day clock mismatches retain the
incoming behavior. The merged suite reports **353 passed, one integration test
deselected**, including three added calendar/clock interaction regressions.
These checks are recorded under `.runs/merge-20261128-time-checks/`.
The cached-output model results in this earlier checkpoint predate the clock-check
merge; the fresh native results are recorded above. No formal accuracy is claimed.

The original test pack contains 13 scenarios and 27 draft atomic label rows from
one standard01 acquisition. Four recorded source versions completed 23 live
local-model workflow runs, including retained failures. Three original baseline
repetitions agreed on all five claim interpretations, verdicts and citation
sets; agreement is not accuracy. A later five-positive baseline also completed.

Testing exposed cropped source fragments, ten-claim response truncation,
calendar-date mismatches and generic targets inheriting previous filenames.
The fixes enforce complete source sentences at clear boundaries, batch longer
testimony within the existing response limit, compare explicit dates in the
source timezone, and reserve filename inheritance for explicit pronouns.
Prior context contains entity/time references rather than full assertions.
The final pre-merge ten-claim run completed five supported, three contradicted
and two unverified assessments without run, claim or tool errors. The generic
document stayed generic in the actual model-facing claim and search hint.

All 245 original export hashes, all 13 prepared inputs and the reference native
output cache were rechecked unchanged. Matching inputs reuse hash-verified
native outputs while changed inputs enter their configured adapter; these are
genuine local-model/dispatcher checks, not fresh six-parser validation or parser
latency measurements. Earlier extraction errors, a context-echo failure, the
known intermediate generic-target projection defect and an interrupted attempt
remain available. The interrupted attempt has no fabricated verdict.

The pre-merge suite passed 318 tests with one integration test deselected. The
last filename-boundary guard was checked against all six actual recorded Agent 1
turns: requests, schemas and all ten claims were identical under deterministic
replay. Live and final pre-merge source fingerprints are retained separately.
Reviewed report views show 143 parsed Prefetch inputs and explain all 41
unparsed inputs while retaining original outcomes and byte-identical run JSON.
The comparison and audit are `.runs/standard01-development04/comparison.html`
and `completion.json`. See [development test details](standard01-development-tests.md).

Upstream 737b03e adds compound-denial completeness checks, explicit no-recall
uncertainty handling and assessment guidance for relevant but limited records.
It was fast-forwarded into this checkout and combined with the local fixes;
the merged suite passes **340 tests, one integration deselected**, including
later-batch denial repair and uncertainty isolation. The recovery stash and
merge receipts are recorded under `.runs/merge-20261128-agent-fixes/`.
Post-merge live regressions are recorded separately in
`.runs/standard01-development05/`; earlier observations are not relabelled as
results of the merged prompts.

Both post-merge runs completed. The ten-claim case returned five supported,
three contradicted and two unverified assessments. One mistyped case ID in a
get_record request was rejected, then corrected successfully on the next call;
both receipts remain recorded. The new compound-denial/no-recall case returned
supported, contradicted and inconclusive. Its first extraction omitted the
opening denial; the completeness guard rejected it and the repair retained all
three claims. Neither run has run or claim errors. Actual model-facing generic
targets and no-recall uncertainty were checked, along with spans and citations.

Across versions there are now **25 completed workflow runs, 14 development
scenarios and 30 draft atomic rows**, all from one acquisition. All original
exports, all 14 prepared inputs and the reference native cache remain unchanged.
The latest index is `.runs/standard01-development05/comparison.html`; its reviewed
reports retain the 143 parsed Prefetch inputs and all 41 diagnostic explanations.
Separate 30-row reviewer A/B sheets are in that version's `independent-review/`
directory. Only two scenarios were rerun under the merged prompts.

No independent human label reviews or formal classification scores have been
completed. The separate reviewer A/B sheets include case-specific source
availability and timezone metadata. These descriptive development scenarios
are not independent acquisitions or blind held-out cases. Formal evaluation
still requires independent adjudication, additional acquired cases and a
frozen configuration. RAM remains preserved for later analysis.

## Earlier desktop checkpoint: standard01 acquisition and coverage

The frozen development case contains 245 owner-exported files from the stopped
Windows 10 Pro victim. Independent source-field comparisons matched 238 decoded
records across all six families: Edge 7, LNK 17, Jump Lists 30, Prefetch 143,
UserAssist 38 and Recycle Bin 3. Coverage retains 173 parsed inputs, four valid
empty Jump Lists, 41 failed Prefetch inputs and 27 unsupported extras/companions.
The failures comprise 35 zero-byte files and six nonempty invalid signatures;
the owner selected all .pf/.PF entries and did not confirm deleted-entry status.

A subsequent read-only check against the complete preserved VMDK chain diagnosed
the 41 failed input items: 30 are historical filenames in NTFS directory-index
slack with no matching Prefetch-file MFT record; five are empty short-name alias
exports whose actual streams are already supplied and parsed under long names;
four refer to deleted files whose old clusters now belong to other live objects;
two are deleted-file remnants whose invalid remaining bytes match their exports.
Of the 30 directory remnants, 26 have complete stale references to reused MFT
records and four have fragmentary entry headers. All 143 successfully parsed
Prefetch exports match the image streams, including 138 allocated files and
five readable deleted files. Notepad's trace is intact. All 245 original export
hashes remain unchanged. The detailed report and raw metadata are retained in
.runs/disk-standard01/prefetch-diagnosis01/diagnosis.html and diagnosis.json.
Exact FTK empty-alias/zero-fill behavior and residual-corruption chronology remain
unconfirmed; no free-space carving or older-snapshot recovery was performed.
This isolated diagnostic reader does not implement product disk-image intake.
Frozen input cases and their original failure coverage have not been rewritten.

The reporting follow-up now shows **143 successfully parsed Prefetch inputs**
and **41 unparsed inputs**, with all four diagnosis groups and file-by-file
explanations. Supplied-file counts are separate from extracted-record counts;
all 245 original coverage entries, original parser errors and assessment results
remain available. Generic reports inspect failed working inputs for empty bytes
or unrecognized Prefetch headers without inferring deleted/alias status.
The case-specific image findings use a diagnostic addendum bound to the exact
case/item IDs, source hashes and a hashed supporting report. Hash checks establish
identity, not the correctness of a diagnostic interpretation. The new report
command renders a fresh view without model inference or parser execution.
.runs/standard01-true-report03/report.html is the reviewed view of run02; its
run.json and registration.json are byte-identical to the originals. All 41
diagnostic notes, ten existing assessment citations and original case hashes
were checked. The suite now reports **240 passed, 1 integration deselected**.
The recorded partial status remains: source limitations are explained separately
from the five completed claim assessments, rather than converting failures into
successful parses.

The first complete-system attempt extracted five claims but all five stopped
before evidence retrieval: the initial per-item coverage consumed the verified
8,192-token budget. Including response reserve, requests required 8,472-8,514
estimated tokens. The later final-answer fallback cannot repair an initial
request that fails before any evidence search.

Coverage is now computed by family/status/count, with unknown families grouped
as other. Initial requests include response reserve and need 3,073-3,115
estimated tokens. get_source_coverage defaults to a summary; filtered source
details use bounded pages and labelled diagnostic excerpts. Complete coverage,
failure messages, companion notes and extraction receipts remain in outputs.
Continuation cursors bind to the case, filters and coverage snapshot. The unit
suite reports **222 passed, 1 integration deselected**. A host-generated tool
diagnostic retrieved all 41 actual failures exactly once across nine pages;
this diagnostic is distinguished from model-generated requests.

The genuine qwen3:8b replay used the same frozen 245-file case and matching
8,192-token runtime profile. Both agents completed all five assessments with
no claim errors, context errors or tool errors; the model returned supported
for each positive statement. The report remains partial because the same 41
Prefetch inputs failed. All 245 original export hashes, all original coverage
entries/diagnostics, ten assessment citations and HTML fragment links were
checked. These are mechanical and development checks, not measured accuracy.
Repeated coverage queries and limited retrieval for the notes-file claim remain
visible in the audit; independent relevance/attribution review is still needed.

A separate earlier end-to-end denial statement did not pass semantic validation. Agent 1
returned action='did not download' with negated=true, rather than the canonical
download_file action, so the host marked it outside coverage and searched no
records. The failed report remains .runs/standard01-denial-run01/report.html.
An explicitly host-structured Agent 2 control changed only that action field,
reused the recorded parser corpus through a genuine model-requested cache hit,
and retrieved the conflicting download evidence. Its first supported answer was
rejected by the existing host denial check; the corrected answer was contradicted
with two validated citations. This component diagnostic does not turn the failed
end-to-end denial into a pass. Its scope and outputs are retained in
.runs/standard01-denial-agent2-control01/result.json.

The Agent 1 fix now separates neutral action names from negation in the prompt
and host normalization. Clear aliases, auxiliaries and contractions map to
canonical actions with an interpretation note; placeholders request repair.
Compound/qualified labels with ambiguous scope also request repair. Unsupported
activities such as send_email and run_sql_query remain explicit. Source spans,
targets and uncertainty are retained. Narrow activity-word and instrumental-app
scope checks reject observed over-splits, then request a corrected complete
batch within the existing two-repair limit. They do not silently delete claims
or constitute a general language/negation validator.

Three intermediate attempts are retained in standard01-denial-run02/run03/run04.
Prompt changes alone did not prevent an extra Edge-launch denial; a later repair
substituted an unasserted opening denial. These attempts are not acceptance
passes. The final guards rejected both extra claims in live Agent 1 probes.
The frozen denial, historical "never used Notepad", mixed polarity and unsupported
email denial probes passed. The frozen denial used both allowed repairs; complete
model responses and feedback are retained in the private probe receipt.
The suite now reports **284 passed, 1 integration deselected**.

The genuine end-to-end replay in .runs/standard01-denial-run05/ produced exactly
one download_file claim with negated=true from the unchanged statement, searched
the actual Edge records and returned contradicted with two validated citations.
The existing host verdict check rejected the model's initial supported answer
and requested correction; that intervention remains visible in the assessment.
No run, claim or tool errors occurred. All 245 original export hashes, 238 indexed
records, original coverage/diagnostics and report links were checked. The run
remains partial for the same 41 Prefetch inputs. These are bounded development
regressions; independent scope, citation relevance, sufficiency and attribution
review and held-out evaluation remain required.

The positive-case replay in .runs/standard01-true-run03/ also retained the five
expected neutral action/target pairs and returned five supported assessments
without run, claim or tool errors. Its ten citations, all original coverage
entries and source hashes were checked. The notes-file assessment retrieved
both LNK and Jump List records. This confirms the observed extraction/routing
regressions; it does not establish classification accuracy or citation sufficiency.
The detailed receipts and retained intermediate-source snapshots are in
.runs/standard01-preparation/denial-fix-result01.json and denial-fix-iteration*/.

Private records are in .runs/standard01-preparation/, with the new report at
.runs/standard01-true-run02/report.html and the initial failure retained in
.runs/standard01-true-run01/. An additional 204 .copy exports appeared after the
first inventory; they are retained separately from the frozen comparison and
are not silently treated as new independently acquired sources.

## Historical checkpoint: 15 November 2026

Development and analysis use the desktop checkout on codex/veritrace-prototype.
The owner committed the acquired Jump List integration as f199b7b, based on
6f413ac's published Agent 1/2 and PECmd updates. The original desktop clone was
clean at ee34968. The feature commit is local at this review; the broader desktop
documentation is being prepared as a separate commit. No push was made by the assistant.
The backend prototype and recorded desktop model capability check are complete;
acquired-evidence acceptance and measured evaluation remain pending.

## Latest controlled case: jumplist01

On 14 November the owner logged four VM actions: launching Notepad, opening
C:\Users\eugene\Downloads\VeriTrace-JL01\JL01-notes.txt, observing that filename
under Recent in the taskbar menu, and closing Notepad without a save prompt.
The opening is bracketed by desktop observations at 13:40:11.8218784Z and
13:40:32.7415972Z. These are owner-operated action intervals, not exact guest
event timestamps. Ground truth stays outside agent input in
.runs/jumplist01-preparation/action-log.tsv. The owner accepted clock alignment;
the manual clock-reading bracket is about ten minutes wide and does not establish
a precise measured offset. Other preparation-note fields remain unknown.

Victim WinPmem capture completed at 13:42:15.9485166Z with exit code 0. The
5 GiB dump was transferred and independently rehashed on the desktop; SHA-256 is
3B238641155E79250CAC37991B0FCA18FF31DFD484E66F5BD9F7143CB764CCB8.
Capture logs and transfer receipts are in .runs/acquisition-jumplist01/.
RAM content interpretation remains deferred.

After owner shutdown, vmrun reported zero running VMs, no vmware-vmx process
remained, checkpoint.vmState was empty and VMX recorded a clean soft shutdown.
The new preservation contains 339 files (76,094,471,165 bytes, about 70.87 GiB),
with every source/copy SHA-256 matching after full re-verification. Source
size/write-time inventories remained unchanged. Only the residual configuration
lock directory was excluded and left untouched. One older Snapshot3.vmem copy
initially mismatched; the source was stable and matched its October verification.
The failed bytes were retained separately, the file was copied again, and all
339 pairs were then rehashed successfully. Initial failure and retry records
remain beside the final manifest; no initial mismatch was silently discarded.

The preserved current descriptor is
.runs/disk-jumplist01/vm-preserved/Windows 10 Pro x64-000005.vmdk.
Its chain is 000005 -> 000004 -> 000002 -> 000001 -> base, with five descriptors,
80 required extents, matching parent CIDs and contained dependencies. Current
snapshot metadata shows JL01-ready (UID 4); this is a post-experiment observation,
not independent proof of restoration history. The owner's original clock-log
snapshot response remains unknown. Preservation, manifests and instructions are
retained in .runs/disk-jumplist01/.

The owner's subsequent screenshot shows FTK Imager 8.3.0.27 reading the
000005.vmdk filename, the Windows NTFS volume and Users/eugene. The full source
path is outside the screenshot; the image was supplied after the preserved-copy
path was specified. The screenshot/access record is in
.runs/disk-jumplist01/ftk-access.json. All 339 preserved files' sizes/write times
were rechecked after access and remained unchanged; content hashes were not
recomputed for this access check.

The owner subsequently exported four automatic and four custom Jump Lists plus
two NTFS index extras. Actual JLECmd execution on registered working copies
produced 20 records, with five parsed and three valid empty sources, no parser
failures and unchanged originals. Independent OLE/byte comparisons checked all
20 records with zero mismatches. Notepad and Quick Access entries target
JL01-notes.txt; their DestList modification times fall within the logged opening
interval. No JL01-budget.txt target occurs in the supplied records. That absence
alone does not establish non-execution. Inventories, native comparisons and
action correlation are in .runs/disk-jumplist01/parser-validation01.

Jump List integration now supplies valid nested search arguments, preserves the
application association and container kind, focuses the model view on activity
times with host-computed local conversions, and retains complete records for
audit/reporting. The host clock guard excludes Jump List target-file/UUID times
from document-opening comparisons. tzdata is now a locked runtime dependency;
the suite reports **159 passed, 1 integration deselected**. A fresh genuine
acquired-case integration test reports **1 passed, 159 deselected** using the
validated 8,192-token configuration. It again returned a qualified supported
notes-file assessment without a context-budget stop. All three latest outputs
have resolvable citations, unchanged registered originals, valid HTML fragment
links and no external HTML assets. All ten acquired exports retain their hashes.
The audit is .runs/disk-jumplist01/parser-validation01/assessment-fix-verification.json.

Installed Ollama is now 0.40.16. Its mismatch with the October 0.35.0 budget was
detected before case inference. A fresh benchmark using existing qwen3:8b passed
all three real tool trials and all token/retention probes at 4,096 tokens with
the victim stopped. Full acquired conversations still reached that limit, even
after replacing identical repeated record projections with explicit references.
A genuine 8,192-token benchmark subsequently passed all three trials and all
token/retention probes before case use. It used the installed model without a
download. Minimum sampled available host memory was about 602 MiB; this is not
a sustained-load capacity result. A new independently validated Jump List-only
parser profile and focused 8,192-token case configuration were created; the
general private configuration was not changed and still needs older
runtime/parser references revalidated.

Both agents completed two host-prepared development cases using genuine local
inference and actual parser/retrieval calls. Latest runs extract one opening
claim per testimony at the correct local time. The notes-file statement is
supported with citations to the matching Notepad/Quick Access activity at
21:40:27, qualified as consistent activity rather than direct proof of opening.
The budget-file statement is unverified without citations; absence does not
contradict. Neither latest run records a context-budget stop or tool error.
Reports are in .runs/jumplist01-agent06a and .runs/jumplist01-agent06b.

Earlier notes-file runs incorrectly demanded definitive proof for support. The
prompt now follows the approved evidence-consistency rubric and distinguishes
missing evidence (unverified) from relevant but ambiguous evidence (inconclusive).
No deterministic rule forces a positive label. Identical record-reference
compaction keeps full receipts and unique evidence, recording policy/counts in
run metadata. A repeated earlier run, agent05b, invented additional actions and
resolved the clock incorrectly despite valid source spans. Agent 1 instructions
were clarified; the latest two runs do not reproduce it, but that failure is
retained as a semantic reliability issue for evaluation. Earlier argument,
timestamp and context failures are also retained. These are operational
development examples, not measured held-out accuracy. See
[Jump List contribution and reproduction](jumplist-contribution.md).

## Historical desktop checks: 2–3 October 2026

All six external parser tools are now present on the desktop. RECmd's complete
2026.5.0 package includes a signed UserAssist decoder reporting plugin version
0.5; its restricted batch passed a genuine victim-sample comparison. The designated
WinPmem Go signed-driver release is downloaded and its embedded driver signature
verified. The owner then staged it in the victim and completed RAM capture
with exit code 0; desktop review confirmed the 5 GiB dump matches the guest's
checksum and capture transcript. After owner shutdown, the complete required
VM/disk snapshot chain was copied and all 309 included files passed independent
source/copy SHA-256 comparison. Current snapshot metadata names
"Acquisition-ready baseline" (UID 3). Historical capture linkage, security-setting
metadata, a nonempty Edge parser comparison and genuine agent integration remain pending.
The owner-run FTK filesystem-access check passed: the supplied screenshot shows
FTK 8.3.0.27 reading NTFS, Windows and Users/eugene. Export destinations are
prepared. NTUSER.DAT, both transaction logs and Default's History were exported
and hashed. RECmd produced 31 UserAssist records; an independent python-registry
reader matched all source identities, decoded names, counters, focus fields and
timestamps with zero mismatches. Twenty records have timestamps; four are UEME
control/session values, not application executions. The hive is clean, so this
does not validate transaction-log replay. A profile pins 70 package/batch files,
and the configured production adapter repeated the matching 31-record result.
UserAssist was initially enabled in the private desktop configuration; model settings
and the benchmark budget are preserved.

Default's History passes SQLite integrity checks but all activity tables are
empty, including visits and downloads; Hindsight returned zero records. The
owner reports no other Edge profiles and no History-wal/History-shm. This cannot
pass a nonempty browser-record comparison. On 3 October, the next inventory
received all nine owner-listed LNK files, three automatic and four custom Jump
Lists, and 207 nonempty Prefetch files in the expected directories. The complete
initial 253-file export inventory was hashed; the original four export hashes remain
unchanged. Twenty-two zero-byte .copy0 extras and four auxiliary Prefetch files
were retained separately. A subsequent owner-reported Recycle Bin directory
creation error was investigated. The SID destination already exists with
Hidden/System attributes and eugen FullControl; the exact FTK error cause is
unconfirmed. Six files subsequently arrived, including two nonempty matching
$I/$R pairs, $I30 and desktop.ini. The new 259-file inventory was hashed. Do not
interpret the earlier empty export as absence in the victim. Source comparisons
for LNK, Jump Lists, Prefetch and Recycle Bin subsequently passed. The dated export-check record is
retained beside the earlier parser evidence under .runs/disk-rehearsal01.
Private parser evidence is retained under
.runs/disk-rehearsal01/parser-validation01. See
[desktop tool inventory and remaining steps](tools-setup.md).

The 3 October native comparisons checked nine LNK records, 16 automatic/custom
Jump List records, 207 Prefetch records and two Recycle Bin deletion records
with zero mismatches. Independent byte checks cover embedded target timestamps
and available LinkInfo paths, DestList identities/paths/last-modified times and
embedded links, Prefetch executable/counter/eight runtime slots after native
decompression, and Recycle Bin original path/size/deletion time with $R hashes.
Three complete 24-byte custom Jump Lists store no entries and are reported as
parsed-with-no-records. The independent OLE reader is olefile 0.47 in the separate
validation environment; project dependencies remain unchanged.

Real-source checks corrected four normalization details: working-copy LNK
filesystem times are excluded from victim evidence times; embedded local paths
take precedence over shell display paths; known-folder identifiers retain their
identity separately from parser labels; and birth-object-ID-derived creation
times carry an explicit semantic role. Strict empty-container handling was added
without accepting missing CSV for malformed/unknown input. Four regression
tests were added; the suite now reports **92 passed, 1 integration deselected**.

Five families are now enabled with pinned executable/normalizer profiles. The
configured host extraction dispatcher produced 265 records (9 LNK, 16 Jump
List, 207 Prefetch, 31 UserAssist, 2 Recycle Bin), with 223 parsed items, three
valid empty items, 33 unsupported items and zero failures. All 259 supplied
files have coverage; unknown extras/companions and the disabled Edge source are
explicitly unsupported. Original/export hashes stayed unchanged and the cached
repeat passed. This is a real host-dispatcher check, not a model-generated tool
request or testimony assessment. Actual evidence is retained in
.runs/disk-rehearsal01/parser-validation02. A preparation-only action-log template
for dev01 is outside agent input at .runs/dev01-preparation/action-log.tsv.

## Implemented locally

- Python 3.12 package and doctor/benchmark/run/evaluate commands.
- Local Ollama API boundary, model identity checks and runtime-bound prompt budget.
- Immutable case registration, working copies, source inventories and hashes.
- Controlled parser subprocesses, retained output/diagnostics, coverage and cache.
- Six source-derived adapter mappings, typed timestamps and scoped SQLite queries.
- Exact testimony spans, bounded model/tool loops and claim-specific citation checks.
- Escaped offline HTML plus JSON, index and tool-call audit outputs.
- Reviewed corpus schema and evaluation that retains operational failures.

The laptop's final suite and the recreated desktop Python 3.12.15 environment
both reported **88 passed, 1 integration test deselected**.
The real pinned Hindsight subprocess smoke check produced **63 records, all 63
resolved**, on its upstream Chromium 60 fixture. This is not the victim's Edge
154 evidence. Wheel/source-archive builds and isolated wheel installation have
been checked on the laptop. Desktop locked installation and CLI help succeeded;
the October doctor identified Ollama 0.35.0 and the installed qwen3:8b model.
The current runtime and focused acceptance results are recorded above.
The earlier release verification record remains on the laptop.

## Historical desktop model acceptance: 2 October 2026

The genuine CLI benchmark passed at 12:02 SGT on 2 October 2026 with VMware
reporting zero running VMs before and after. All three native-tool trials
executed host-generated nonce lookups and returned the exact nonce through
schema-only finalization. All nine trial-stage token checks and the short,
Unicode and near-boundary retention probes passed. The matching 4,096-token
budget profile is configured in the ignored veritrace.local.toml.

Ollama server logs identify Vulkan on the RX 6750 XT and 37/37 layers offloaded;
ollama ps reports 100% GPU and 5.6 GB. Trial times were 10.40 seconds cold,
2.17 and 1.81 seconds warm. Host memory briefly reached 99% usage, with only
50.73 MiB available. This establishes capability under the observed desktop
conditions, not sustained-load capacity or forensic accuracy. Keep experiments
and inference separate and close unnecessary applications before acquired runs.

See [desktop benchmark evidence](desktop-benchmark.md) for identities,
measurements, retained local artefacts and remaining acceptance work.

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

The native protocol issue was identified from provider/parser behavior.
The corrected native-tools-then-json-v1 protocol passed the desktop capability
benchmark on Ollama 0.35.0; acquired-case verification was pending at that review.
The focused November integration subsequently passed, as recorded above.
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
   fixtures. The October checkpoint passed five acquired-source comparisons;
   standard01 subsequently passed source-field comparisons across all six,
   including nonempty Edge visits/downloads, with pinned configured extraction.
6. Windows staging/copy tooling and an ignored execution ledger replace shell
   helpers incompatible with this environment; the ledger is retained because
   the full implementation plan still has owner-run acceptance work outstanding.

## Pending acceptance work

| Work | Required evidence |
| --- | --- |
| Acquisition | standard01 RAM capture/transfer and stopped-VM disk preservation are verified; six-family exports are received/hashed. Retain source limitations and confirm historical snapshot/security metadata where still unknown. New independent acquisitions remain necessary for the target corpus. |
| Parser deployment | All six standard01 source-field comparisons passed (238 records). Validate new parser versions/source types before enabling them; the 41 diagnosed Prefetch input limitations remain explicit. |
| Genuine end-to-end run | Six-family development runs and controlled variants completed with live local inference. Complete independent claim/citation relevance, sufficiency and attribution review; repeat the frozen final configuration for formal repeatability. |
| Evaluation | Two actual independent reviewers, additional development/held-out acquisitions, opaque held-out identifiers, frozen configuration and manual baseline. Source-removal/corruption development checks and initial repeated-run agreement are recorded, without accuracy claims. |
| Submission | Measured-results IEEE report, AI-use statement, final package/manual and subtitled demonstration video. |

No formal classification accuracy, investigation-time improvement
or held-out forensic quality has been measured yet. Six-family source-field
comparisons and bounded development observations are recorded above. GPU acceleration
was observed for the pinned desktop benchmark. Direct disk-image
ingestion and memory interpretation are future milestones; current input is an
acquired artefact folder.
