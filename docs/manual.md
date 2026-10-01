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

Open report.html locally. Review exact testimony, interpretation, uncertainty,
time roles, coverage, citations, alternatives and operational errors. Links
lead to embedded records with original-source and preserved-parser-output
locations. The SQLite index retains the extracted corpus. JSON exports and
tool_calls.jsonl support reproduction without scraping the HTML.

Supported means relevant positive evidence is consistent with the interpreted
claim. Contradicted requires positive conflicting evidence. Unverified means
insufficient evidence in available supported sources, or outside coverage.
Inconclusive requires relevant evidence whose ambiguity/conflict prevents a
conclusion. Absence alone is never contradiction. Mechanical ID/source checks
do not establish evidential relevance or identify the person using an account.

Exit codes: 0 complete, 2 invalid input/configuration, 3 model/dependency/workflow
error, 4 partial run. Error/partial reports retain valid available results and
explicit errors; they do not substitute failures with forensic labels.

Current acquired-sample gates remain pending. Parser commands/version/schema
profiles are configured by the investigator after validation, not selected by
the model. Until then failed/unsupported families are disclosed. See
parser-compatibility.md and acquisition.md for the remaining validation work.
