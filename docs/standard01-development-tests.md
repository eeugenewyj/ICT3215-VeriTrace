# standard01 development fault checks

Updated 28 November 2026. These checks reuse the frozen 245-file standard01
acquisition. Every scenario and variant stays in the development split; they
are not independent acquisitions or a held-out evaluation corpus. Draft labels
have no recorded independent human reviewers, so no classification accuracy or
F1 score is reported.

## Test pack and evidence boundary

The original private pack contains 13 scenarios and 27 draft atomic label rows, including
repeated statements in the capacity test. Expected interpretations, provisional
statuses and invariants were saved before the runs. Labels and the action log
remain outside every agent input. Separate blank reviewer A/B sheets support
independent ratings; no reviewer identity or completed review was fabricated.

| Scenario | Check |
| --- | --- |
| Baseline, three repetitions | Five positive activities; compare extracted fields, verdicts and citation sets. |
| Download denial | Preserve negative polarity and retrieve the actual download evidence. |
| Never-used Notepad | Preserve the program-use denial as a supported activity type. |
| Deletion denial | Compare with the positive Recycle Bin metadata, retaining attribution limits. |
| Mixed polarity | Denied download and positive opening in the same sentence. |
| Wrong day | A 28-November record must not support a 27-November occurrence solely because the clock matches. |
| Wrong clock | A 00:10 record must not support an explicitly claimed 17:10 occurrence. |
| Ambiguous document | Preserve the unknown target rather than inventing a filename. |
| Unsupported email | Keep the actual unsupported activity; report coverage limits. |
| Unlocated ZIP target | Search genuinely; unrelated PDF records do not show this ZIP download. |
| Missing Edge input | Disclose unavailable coverage; source absence alone cannot contradict occurrence. |
| Corrupted Edge input | Disclose the actual adapter failure and retain other families. |
| Ten-claim testimony | Check extraction completeness and the bounded response limit. |

The missing-source variant omits only the registered Edge History file. The
corruption variant zeroes its first 64 bytes on a new disposable copy and updates
that copy's supplied hash. Before/after hashes and recipes are retained outside
the inputs. Original sources, RAM and the preserved VM are not modified.

Unchanged families use hash-verified native outputs from the existing acquired
run. Item IDs, source hashes, original paths, accounts, SIDs and companions must
match; raw output hashes and locators are verified and copied into each run.
Normalized IDs are rebound to the new case ID. Changed inputs enter their actual
configured adapter. Replay events are recorded separately and disclosed in run
metadata. These runs exercise genuine local inference and host tool dispatch;
they do not claim fresh native-parser validation or native-parser timing for all
six families.

## Original-version observations

The first version completed 15 runs: 13 scenarios with three baseline repetitions.
All three baseline runs agreed on the five claim interpretations, five supported
verdicts and citation sets. They took 238.5, 223.9 and 225.7 seconds under the
recorded native-output replay conditions. Agreement does not establish accuracy.
Download, Notepad and deletion denials returned contradicted; mixed polarity
returned one contradicted and one supported assessment. Missing/corrupted Edge,
unsupported email and the ambiguous document were reported unverified. The
wrong-clock case was inconclusive.

Three defects were demonstrated:

1. Agent 1 accepted the cropped source fragment `using Edge` as an independent
   launch claim in the unlocated-target scenario. The download was unverified,
   but the extra program claim received a supported assessment.
2. The ten-claim request reached the 768-token response cap on all three attempts.
   Extraction ended with an explicit model error and no assessments. It did not
   silently accept a truncated claim list.
3. The clock-only host guard ignored the calendar date. The wrong-day case was
   incorrectly supported by a 28-November download. A deterministic probe using
   that same acquired record also reproduced the false time/action match.

One wrong-clock attempt stopped without a final run.json. The cause is unknown;
the earlier process and local Ollama service were no longer running on resume.
Its partial outputs remain unchanged, and the replacement run is explicitly
identified. The installed service was restarted locally with the same runtime,
model digest, template and verified context profile. The incomplete attempt is
not assigned a fabricated model verdict.

## Targeted changes and validation

Source-span validation now rejects cropped clauses at clear sentence boundaries,
including fragments beginning or ending at a period inside a filename.
Long, clearly separated testimony is extracted in batches of three sentences
when more than five are present. Exact global spans are retained, prior entity
and stated-time references are supplied as context, and IDs are made unique
across batches. The two-repair budget remains global to the extraction. A
16-batch limit prevents unbounded model calls. Complex single sentences can
still exceed the output cap and fail explicitly; this is not a general sentence
or semantic completeness parser.

The time guard now compares unambiguous full calendar dates in the source
timezone. Clock tolerance still applies across midnight. Date-only mismatches
can withhold support, and differently scoped records no longer trigger the
positive-evidence consistency nudge. Ambiguous numeric dates, relative dates
and multiple-date scope still require interpretation; approximate/range date
wording is not forced into one exact day.

A further projection check found that the host converted "a document" into a
previous PDF filename before passing the claim to Agent 2. Reference resolution
is now limited to explicit pronouns. Generic/missing targets stay generic in
both the claim view and search hint; pronoun hints and views use the same nearest
reference. The named-target projections/hints from ten actual prior claims were
unchanged by this correction.

The isolated preview and the actual project checkout both passed **307 tests,
1 integration deselected**. The acquired-record time probe now rejects the
same wrong-day match. These changes retain the installed model, verified
8,192-token context and 768-token response limit. New-version model replays
are recorded separately from the original results.

The first batching replay fitted within the response limit but the model
re-extracted prior sentences supplied as context, exhausting the repair budget.
That failed v02 attempt is retained. v03 removes source sentences, action labels
and negation from preceding context, retaining only target, actor and stated-time
references. The live Agent 1 component probe then extracted all ten statements
in four batches/six model calls, preserving unique IDs and exact source spans.
This component check is distinguished from the subsequent full-pipeline replay.

The intermediate v03 pipeline completed ten assessments but its generic last
claim still had the projection defect, which is explicitly flagged and retained.
The final pre-merge v04 replay completed all ten assessments: five supported, three
contradicted and two unverified. Email remained outside coverage, and the
generic document target stayed unspecified in actual model-facing messages and
search hints. No run, claim or tool errors occurred in that final run. The separate
v03 standalone baseline also completed five supported assessments.

The pre-merge suite reports **318 passed, 1 integration deselected**. A final
filename-boundary validation check was added after the live run; deterministic
replay of all six recorded Agent 1 turns confirmed identical requests, schemas,
IDs, fields and global spans. This is not counted as new inference. Both the live
and current source fingerprints are retained. Across versions there are 23
completed workflow runs, with errors/known bad intermediate results preserved.
All 245 original export hashes, all 13 prepared inputs and the reference native
cache were rechecked unchanged. Reviewed ten-claim and baseline HTML views retain
143 parsed Prefetch inputs and all 41 diagnostic explanations without changing
their original run JSON, registration, assessments or parser outcomes.

Scenario names are descriptive development IDs and are visible in model tool
prompts. The unlocated target also has a descriptive filename. This diagnostic
pack is not a blind accuracy experiment; future held-out cases need opaque IDs
and filenames. Separate reviewer sheets omit draft statuses and model verdicts,
with case-specific source availability provided so omitted/corrupted Edge data
is not credited from the complete reference corpus.

Private records are under `.runs/standard01-development01/` and
`.runs/standard01-development02/` and `.runs/standard01-development03/`;
`review.html` and `review-worksheet.tsv`
provide the review packet. The unchanged-input and unchanged-draft-label
comparison is recorded in the new version's pack. Formal evaluation remains
pending independent label and citation relevance/sufficiency review, additional
independent acquisitions and a frozen held-out configuration.
The final comparison and audit receipt are
`.runs/standard01-development04/comparison.html` and `completion.json`.
Independent-review sheets and case-specific source/timezone metadata are in
`.runs/standard01-development02/independent-review/`.

## Upstream merge and additional development check

Upstream commit 737b03e adds compound-denial completeness checks, no-recall
uncertainty handling and assessment guidance for relevant but limited records.
The desktop checkout fast-forwarded to that commit, then reapplied the preserved
local fixes. The overlapping extraction code and prompt merged without textual
conflicts. A recovery stash remains recorded under
`.runs/merge-20261128-agent-fixes/`. The combined suite reports **340 passed,
1 integration deselected**, including later-batch denial repair and uncertainty
isolation across the global-span batching boundary.

The post-merge pack reuses the unchanged 13 original inputs and expectations,
then adds one three-claim development scenario: "I downloaded STD01-reference.pdf
but I didn't open it. I don't remember deleting STD01-reference.pdf." It uses a
new verified copy of the same acquired sources; it is not a new acquisition.
Its expectations were saved before inference. Across versions, this makes
14 scenarios and 30 draft atomic rows. The ten-claim testimony and this new
compound-denial/memory case are rerun under the merged prompts; the earlier
scenarios are not represented as rerun under this source version.

Version records, model traces and parser-replay receipts are retained in
`.runs/standard01-development05/`. Its separate reviewer A/B sheets contain
30 blank review rows and case-specific source/timezone metadata, omitting model
outcomes and draft classifications. The original 27-row review packet remains
unchanged. The host's narrow lexical denial/hedge checks do not establish
general semantic completeness or handle every target/scope construction.

Both post-merge live runs completed. The ten-claim case returned five supported,
three contradicted and two unverified assessments in 517.5 seconds. One
get_record request used a mistyped case ID; the host rejected it and the next
request corrected the ID successfully. This recovered tool error remains
visible, rather than being described as an error-free run.

The new three-claim case returned supported, contradicted and inconclusive in
212.4 seconds. Its first response omitted the opening denial; the host requested
repair and the corrected response kept all three claims. The no-recall deletion
statement retained its uncertainty instead of becoming a flat denial. Neither
run has run/claim errors or findings in the recorded field/projection checks.
These comparisons still use provisional expectations, not human-reviewed truth.

There are 25 completed workflow runs across versions. The completion audit
rechecked all 245 original export hashes, all 14 prepared inputs, unchanged native
reference cache, actual model-facing generic/uncertainty projections, citation
identities and source spans. Report regeneration retained byte-identical run JSON
and registrations, with 143 parsed Prefetch inputs and 41 diagnostic notes.
The offline results index and completion receipt are
`.runs/standard01-development05/comparison.html` and `completion.json`.

## Fresh native CLI checks after the clock-check merge

Commit 49a1509 was tested with the actual CLI entry point, installed native
parsers and live local inference. Six scenarios cover the baseline, wrong day,
wrong clock, approximate wrong clock, download denial and compound denial with
uncertain memory. The approximate-clock scenario adds one new source-equivalent
development variant, bringing the review packet to 15 scenarios and 31 draft
atomic slots on the same acquisition. Expectations were recorded before model
inference; the separate reviewer sheets omit them and model outcomes.

Each run uses a fresh output directory and the unmodified configured adapters.
Only the Ollama transport is wrapped to retain request/response traces. There is
no recorded-response or external native-output replay. The six installed parser
families execute in every run; normal extraction caching within a single run
remains enabled. The model digest, runtime, template, 8,192-token context and
768-token response cap remain unchanged, and the VM is checked stopped before
each inference request. RAM and the preserved disk chain are not analysed.

The first version completed six runs with 12 claims and 11 assessments. Every
fresh 238-record corpus matched the reference source identities, locators,
targets, applications, accounts/SIDs and typed timestamp fields. Native-output
filesystem paths are excluded from that comparison. This is not a new
independent parser certification or formal accuracy measurement.

One baseline opening claim reached the twelve-tool-call cap after retrieving
relevant records, then failed with a workflow error and no assessment. The other
baseline claims completed. The wrong-day result was inconclusive; exact and
approximate wrong-clock cases and the download denial were contradicted. The
compound case returned supported, contradicted and inconclusive. The baseline
failure remains unchanged under `.runs/standard01-development06-native/`.

Five regression checks reproduced the cap failure. The fix finalizes from
returned evidence after a successful search when the cap is reached or a new
batch would exceed it. No extra retrieval is executed, and the assessment
discloses incomplete retrieval. Empty successful searches can finalize
unverified; no successful search still yields a workflow error. Invalid
citations still require repair, with the existing two-repair ceiling enforced.
The isolated preview and actual checkout both passed **358 tests, one integration
test deselected**. The fixed-source native rerun is recorded separately in
`.runs/standard01-development07-native/`; original inputs and expectations are
unchanged. These observations are development checks pending independent human
review, not accuracy or investigation-time improvement results.

The fixed-source rerun completed all six scenarios and all 12 assessments,
without run, claim or tool errors. The baseline returned five supported
assessments. The PDF-opening claim again executed twelve retrieval calls; this
time it finalized with five mechanically validated citations and a recorded
early-stop limitation. The live branch was exercised without increasing the
cap. Wrong day returned inconclusive; exact/approximate wrong clocks and the
download denial returned contradicted. The compound case returned supported,
contradicted and inconclusive. All provisional status expectations were met;
they remain unreviewed development expectations.

All six fresh native corpora matched the same 238 reference source-derived
records. The final audit checked all 245 original export hashes, all six input
hash maps, exact spans, actual model-facing claims, date/clock precision,
citations and HTML links. Provider counts stayed within the validated context
headroom: the maximum observed prompt was 5,322 tokens, with no length-limited
responses at the existing 768-token cap. New report views retain byte-identical
run JSON/registrations, 143 parsed Prefetch inputs and 41 diagnostic explanations.
The result index is `.runs/standard01-development07-native/comparison.html`.

An interpretation review note flags the baseline opening explanation's use of
browser-download and later-deletion context as support for opening. LNK/Jump List
citations are also present, and the model's limitations qualify the other traces.
The source-bound note and unchanged model output are available for independent
relevance/sufficiency and attribution review. Valid citation identities and
provisional outcome agreement do not certify that prose. Both human reviewer
sheets remain blank; no formal classification score has been generated.
