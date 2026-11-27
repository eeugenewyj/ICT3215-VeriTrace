# Investigator manual

Use Python 3.12 and follow setup.md. The victim is the Windows 10 Pro VM on
the desktop. VeriTrace runs on the investigator's working copy; inference
runs on the desktop host. It does not acquire a live device or analyse RAM.

A case contains case.json, UTF-8 testimony.txt and evidence/. case.json maps
item_id, acquired_path, original_path, family and optional account/SID,
supplied_sha256 and companion_item_ids. Unknown metadata stays null. Family
identifiers: edge_history, lnk, jumplist, prefetch, userassist, recyclebin.
All supplied files are inventoried; undeclared files are unknown/unsupported.
Ground-truth labels stay outside this input folder.

When exports are renamed, declare companion_item_ids and preserve the companion's
original_path relative to the main source, such as History-wal or NTUSER.DAT.LOG1.
The adapters stage supplied companions under the parser-required names, record
their item IDs/hashes and disclose missing companions. An unidentifiable declared
companion or two candidates for the same role causes a parsing failure. Registry
logs are retained and staged; successful replay still needs parser-log and source
comparison checks. Companion files are inventoried even when their family is
unknown; their use is reported on the parent source's coverage entry.

```powershell
uv run veritrace run --case .cases/dev01 --output .runs/dev01 --config veritrace.local.toml
```

Choose a fresh output folder for every run. Input/output overlap, traversal,
reparse points, missing declared files and supplied-hash mismatches are refused.
Originals are hashed before and after processing; parsers use copies.

The backend runs claim extraction, requires an actual model-generated
extract_case call, permits bounded evidence queries and validates every cited
record against claim-specific retrieval receipts. No arbitrary shell, SQL,
file-path selection or network-fetch tool is exposed to either agent.

Agent 1 keeps the activity separate from its polarity: a denial of downloading
uses action=download_file and negated=true. Clear noncanonical action labels
such as "did not download" are normalized with an interpretation note. The
original sentence, target and source span stay intact. Placeholder actions and
ambiguous compound/qualified action labels request repair, with at most two
repairs before an explicit model error. Actual unsupported activities remain
explicit; a shared verb does not turn run_sql_query into launch_program.
A narrow scope check also rejects an extra program claim when its only literal
app mention is instrumental, such as "download ... using Edge". It asks Agent 1
to repair the complete batch rather than silently deleting a claim. Independent
program assertions remain valid. When a sentence uses recognized activity words,
an added action type with no matching activity words also requires repair;
unrecognized wording is not automatically rewritten. These checks are not a general language/negation
validator; semantic completeness, scope and attribution still require evaluation.

The model receives a computed coverage summary grouped by the six supported
families, with unknown/undeclared families grouped as other. Each row reports
supplied item and record counts plus counts of parsed, valid empty, failed,
unavailable and unsupported coverage entries. Family-level markers count as
entries, not supplied files. Complete per-item coverage and diagnostics remain
in coverage.json, the HTML report and extraction receipts in tool_calls.jsonl.

get_source_coverage returns the summary by default. Set details=true to request
per-source coverage, optionally filtering by family, status or item_id. Pages
default to five entries (maximum 25); reuse next_cursor with the same case and
filters. family=other selects unknown/undeclared families. Continuations are
bound to the coverage snapshot as well as the filters. Model-facing diagnostic
strings and companion notes are bounded, labelled excerpts; full values remain
in the output files and tool receipts. Coverage describes processing, not proof
of activity. Evidence searches and citation checks still govern assessments.

Retrieval uses native tool turns without an assessment JSON constraint. Final
assessment is a separate schema-only turn, retaining the returned evidence.
Every claim requires a successful evidence search; extraction alone cannot
justify an unverified assessment. Identical source bytes from distinct item IDs
retain distinct record IDs and account provenance. Edge parsing requires every
supported native visit/download row identity to resolve in the export; omitted
or ambiguous rows fail that source while its raw export remains preserved.

Open report.html locally. Review exact testimony, interpretation, uncertainty,
time roles, coverage, citations, alternatives and operational errors. Links
lead to embedded records with original-source and preserved-parser-output
locations. The SQLite index retains the extracted corpus. JSON exports and
tool_calls.jsonl support reproduction without scraping the HTML.

The report separates supplied-file counts from extracted-record counts and shows
a family summary followed by explanations for inputs that could not be parsed.
Complete original coverage remains available in the report and coverage.json;
coverage-summary.json stores the report summary and explanations. Empty inputs
and invalid Prefetch headers get byte-based explanations after checking the
working-source hash. A filename alone never establishes that an input is a
deleted file, directory remnant or duplicate alias.

An investigator can attach source diagnostic notes and regenerate a recorded
report without calling Ollama or rerunning parsers:

```powershell
uv run veritrace report --run .runs/dev01 --output .runs/dev01-reviewed --diagnostics .runs/dev01-diagnostics/coverage-diagnostics.json
```

Omit --diagnostics for a summary with the default byte-based explanations. Always
choose a new output outside the recorded run and original case input. The new
view retains the recorded run status, assessments and parser outcomes; the
original run is unchanged. A partial source-coverage result is distinguished
from missing claim assessments rather than being relabelled complete.

The optional diagnostic JSON has schema_version=1, the exact case_id, a method,
a relative supporting_report filename, its supporting_report_sha256, and notes.
Each note identifies item_id, source_sha256, category, explanation, limitations
and optional related_item_ids. The supporting file stays beside the diagnostic
JSON. Case membership, failed-input status, working-source hashes, related-item
membership and supporting-report hash are checked. Duplicate or mismatched notes
are refused. Notes are supplied interpretations, not model evidence or proof of
their own correctness. Their provenance and limits are embedded in the HTML;
the note file and supporting report are retained with the regenerated view.

Supported means relevant positive evidence is consistent with the interpreted
claim. Contradicted requires positive conflicting evidence. Unverified means
insufficient evidence in available supported sources, or outside coverage.
Inconclusive requires relevant evidence whose ambiguity/conflict prevents a
conclusion. Absence alone is never contradiction. Mechanical ID/source checks
do not establish evidential relevance or identify the person using an account.

Exit codes: 0 complete, 2 invalid input/configuration, 3 model/dependency/workflow
error, 4 partial run. Error/partial reports retain valid available results and
explicit errors; they do not substitute failures with forensic labels.

All six families have recorded source-field comparisons for the standard01
development acquisition. New parser versions, schemas or source types still
require validation before enabling their profiles. Parser commands and profiles
are configured by the investigator, not selected by the model. Failed/unsupported
sources remain disclosed. See implementation-status.md for the current checkpoint
and parser-compatibility.md and acquisition.md for the validation procedures.
