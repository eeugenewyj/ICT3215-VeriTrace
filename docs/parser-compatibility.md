# Parser compatibility record

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
victim's acquired samples. The remaining five parser families have not yet
been validated. Do not credit absent tools or an unconfigured decoder as
successful parsing.

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
Create and test the batch against the installed RECmd version; no successful
plugin deployment has been claimed here. Raw binary UserAssist values remain
in the preserved hive because this inspected plugin does not export them.

Use official [Hindsight](https://github.com/RyanDFIR/hindsight),
[LECmd](https://github.com/EricZimmerman/LECmd),
[JLECmd](https://github.com/EricZimmerman/JLECmd),
[PECmd](https://github.com/EricZimmerman/PECmd),
[RBCmd](https://github.com/EricZimmerman/RBCmd),
[RECmd](https://github.com/EricZimmerman/RECmd) and
[RegistryPlugins](https://github.com/EricZimmerman/RegistryPlugins) sources.
Keep binaries, actual --help output, runtime requirements and export headers
beside the private comparison record. The development machine has no .NET SDK;
the Zimmerman tools were inspected from source and tested with controlled
export fixtures, rather than built or run against a victim acquisition.
