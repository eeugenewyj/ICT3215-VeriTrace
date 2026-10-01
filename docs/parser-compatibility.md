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

Production family enablement requires a recorded comparison against the
victim's acquired samples. The remaining five parser families have not yet
been validated. Do not credit absent tools or an unconfigured decoder as
successful parsing.
