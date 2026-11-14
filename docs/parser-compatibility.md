# Parser compatibility record

14 November update: the controlled jumplist01 acquisition supplied eight Jump
List files and two unsupported NTFS index extras. JLECmd 2026.5.0 produced 20
records; independent OLE/byte comparisons matched all 20, with three valid empty
sources and no parser failures. A refreshed Jump List-only profile pins the
current normalizer and passed genuine model-generated extraction/retrieval.
The general private configuration retains older normalizer pins and needs
revalidation before a broader run. See [Jump List integration](jumplist-contribution.md).

## Historical deployment and source comparisons: 2–3 October 2026

Desktop deployment review on 2 October 2026: LECmd, JLECmd, PECmd and RBCmd
2026.5.0 are present, digitally signed and pass help/launch checks. FTK Imager
8.3.0.27 is installed. Hindsight 2026.06 at the inspected revision now has an
isolated Python 3.12 environment with passing dependency and CLI checks.
RECmd 2026.5.0 and its signed UserAssist 0.5 plugin are now deployed; a restricted
batch is prepared. The designated WinPmem signed-driver release is present on
the host. The owner's victim RAM capture and matching desktop transfer hash
were subsequently verified. The complete stopped-VM preservation copy and its
included file hashes also passed. The owner-run FTK NTFS access check passed
with a supplied screenshot. NTUSER.DAT, LOG1/LOG2 and Default's History have now
been exported, inventoried and hashed. UserAssist's genuine acquired-sample
comparison passed, followed by LNK, Jump Lists, Prefetch and Recycle Bin on
3 October. Edge's nonempty-source comparison remains pending. See
[current installation inventory and setup steps](tools-setup.md).

Hindsight source inspected: commit `4cf136fd70577b0da540b9a69750b769c6c27f32`,
display version 2026.06, from the [official repository](https://github.com/RyanDFIR/hindsight).
Its actual CLI advertises `--only history,downloads` and JSONL export.

The adapter maps `chrome:history:page_visited` and
`chrome:history:file_downloaded`, retaining visit_id/download_id and checking
them against fixed SQLite queries on working copies. Original native timestamp
values and a line/hash locator into the JSONL export are retained.

An actual subprocess run against the upstream Chromium 60 History test fixture
produced 63 records; all 63 resolved to native source rows. Original hashes
remained unchanged. Fixture SHA-256:
`c9f52bd6d4089807982b6e10a7d0d8e1e932262fd3558530073f46dd00435191`.
This is a parser smoke check, **not a Windows 10 victim acquisition or proof of
compatibility with Edge 154**. The actual local output and dependency freeze are
kept in ignored .runs and .external folders.

Source revisions inspected for the remaining mappings:

| Source | Commit |
| --- | --- |
| LECmd | 8107efc4f9f9b4f80fd7b50ed659ffb736e29dd1 |
| JLECmd | ba276d761682d7abaf2d07da9aad4120b28f0938 |
| PECmd | acdf082f1c2e946b0c358cdf6ef71607e00cfea0 |
| RBCmd | 756498f9b5e94327abe5398b19435b7142f7265c |
| RECmd | bcd0ac33ed98de61ea6de551eef96052bddbbd49 |
| RegistryPlugins | c16219db698f7ee66fbd97de7ec5d17fc10bdf8e |

Production family enablement requires a recorded comparison against the
victim's acquired samples. Five of six families now pass; Edge remains pending.
RECmd's restricted batch produced 31 records from the preserved victim hive.
An independent python-registry 1.3.1 reader traversed every Count key and matched
the complete key/value identity set, ROT13 targets, run/focus counters, focus
time and raw/normalized timestamps against the plugin and adapter exports.
All 31 matched; 20 have timestamps. Four UEME control/session records are
retained without crediting them as application executions. The clean hive's
matching sequence numbers mean transaction-log replay was not exercised.
Binary bytes and field comparisons are retained privately with the source hash
in .runs/disk-rehearsal01/parser-validation01/userassist-comparison.json.

The private userassist profile pins 70 deployed package/batch files. The
production build_adapters path verified those pins and repeated the same
31-record field result on fresh working copies; acquired hashes stayed
unchanged. Five families were enabled in veritrace.local.toml at that check.
The model and benchmark settings were preserved. Their current hash/runtime
revalidation status is described in the November update above.

The acquired Default History passes SQLite integrity checks, but every activity
table is empty, including both the standard and Edge-specific tables. Hindsight
returned zero records, matching the source counts. The owner reports Default
as the only profile and History-wal/History-shm absent. This is an empty-source
rehearsal, not a passed nonempty visit/download compatibility gate. A controlled
browser action and fresh acquisition are needed. On 3 October, nine LNK files,
three automatic/four custom Jump Lists and 207 nonempty Prefetch files were
received and hashed; their parser/native comparisons subsequently passed. Recycle
Bin subsequently received two matching nonempty $I/$R pairs after an owner
directory-export warning; its native parser comparison subsequently passed.
Twenty-two zero-byte .copy0 Prefetch extras are retained without treating them
as usable .pf sources. Do not credit absent sources or unconfigured decoders as
successful parsing.

The retained native check matched 9 LNK, 16 Jump List, 207 Prefetch and 2 Recycle
Bin records. The LNK check validates target FILETIMEs and available embedded
LinkInfo paths; shell-only display-path resolution is not independently certified.
Jump List checks use independent OLE access, DestList fields and embedded links.
Prefetch checks use native Windows XPRESS-Huffman decompression followed by
byte-field inspection; Recycle Bin checks compare metadata fields and matching
content sizes/hashes. Three valid 24-byte known-category custom containers have
no stored entries. They produce no JLECmd CSV and now receive empty coverage
only after strict structure validation. Missing CSV for other input remains an error.

SourceCreated/SourceModified/SourceAccessed describe parser working-copy
filesystem metadata and are retained only as annotated raw fields. They are not
victim LNK activity timestamps. Embedded LocalPath is preferred to shell display
paths, which can omit filename extensions. Automatic Jump List CreationTime
derived from FileBirthDroid is identified as a birth-object UUID time; it is not
an independently recorded interaction timestamp. Known-folder display labels
remain in raw output while the target retains the original known-folder identifier.

The five-family configured dispatcher check produced 265 records, no failed
sources and matching original hashes; a repeated request was cached. Profiles
for the four Windows CSV tools pin the executable and normalizer dependencies.
Comparisons and execution receipts are under .runs/disk-rehearsal01/parser-validation02.
This does not complete genuine LLM-agent integration or evaluation.

## Configure a validated family

Copy examples/parser-profile.json to a private profile. This template is
intentionally unverified. Fill observed version, schema, command_hashes (absolute
file paths to SHA-256 values), acquired_sample.source_sha256 and a retained
comparison record. Set verified to true only after checking a victim sample
against its source. Hash the completed profile with Get-FileHash -Algorithm SHA256.
Do not enable a family merely because its unit fixtures pass.

In veritrace.local.toml, set parser_commands, parser_versions,
parser_config_hashes and parser_profiles for that family. For example, the
Edge command prefix is an absolute Python interpreter path followed by the
absolute path to hindsight.py. Include the interpreter, script and required
source/configuration dependencies in command_hashes. The host resolves PATH
executables and relative files before changing the parser working directory,
verifies their hashes and launches pinned absolute paths. Module/inline-code
entry points such as python -m or -c are not supported; use a script entry point.

Accepted schema identifiers:

| Family | Parser | Schema |
| --- | --- | --- |
| edge_history | Hindsight | hindsight-history-2026.06-v1 |
| lnk | LECmd | zimmerman-csv-source-v1 |
| jumplist | JLECmd | zimmerman-csv-source-v1 |
| prefetch | PECmd | zimmerman-csv-source-v1 |
| recyclebin | RBCmd | zimmerman-csv-source-v1 |
| userassist | RECmd and RegistryPlugin.UserAssist 0.5 | userassist-plugin-0.5-v1 |

UserAssist additionally requires batch_path, a pinned minimal UserAssist batch,
plugin_version = "0.5", and hashes for the deployed decoder/plugin dependencies.
The deployed batch is .external/RECmd/BatchExamples/VeriTraceUserAssist.reb.
Its actual batch parsing and decoded export have now been compared against a
preserved victim hive with supplied logs; the pass applies to this clean hive
and does not establish replay behavior for a dirty hive.
Raw binary UserAssist values remain
in the preserved hive because this inspected plugin does not export them.

Use official [Hindsight](https://github.com/RyanDFIR/hindsight),
[LECmd](https://github.com/EricZimmerman/LECmd),
[JLECmd](https://github.com/EricZimmerman/JLECmd),
[PECmd](https://github.com/EricZimmerman/PECmd),
[RBCmd](https://github.com/EricZimmerman/RBCmd),
[RECmd](https://github.com/EricZimmerman/RECmd) and
[RegistryPlugins](https://github.com/EricZimmerman/RegistryPlugins) sources.
Keep binaries, actual --help output, runtime requirements and export headers
beside the private comparison record. The earlier development checks used
inspected source and controlled export fixtures. The desktop now has the
selected .NET runtime and executed the installed RECmd package against a real
victim hive; no local source build is claimed.
