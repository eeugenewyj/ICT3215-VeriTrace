# Delivery checklist

The deadline recorded from the project rubric is **29 November 2026**. Reserve
the final two weeks for evaluation, report preparation, packaging and video.

- Source repository, installable distribution and investigator manual.
- Rehearsed victim RAM/disk preservation, demonstrable export access and recorded
  source hashes. RAM is preserved for later analysis.
- Desktop model benchmark and per-family acquired-source parser comparisons.
- Three development and three held-out base cases, at least ten reviewed claims
  each; related variants remain within the same split.
- Frozen model/runtime/prompts/parser configuration, actual case runs, manual
  baseline, independent citation ratings and explicit operational failures.
- IEEE report in Word/PDF, 6–10 pages; at least ten references, with at least
  70% journal/conference sources. Check the final rubric before submission.
- A 5–10 minute, subtitled, 1080p demonstration video and required YouTube link.
- A generative-AI-use declaration describing assistance, checking and limitations.

Package commands:

```powershell
uv sync --frozen
uv run pytest -q
uv run python -m build
uv venv --python 3.12 .external/release-check
uv pip install --python .external/release-check/Scripts/python.exe dist/veritrace-0.1.0-py3-none-any.whl
.external/release-check/Scripts/veritrace.exe --help
```

After external prerequisites are validated, use the same environment to run
`doctor`, `benchmark` and a genuine acquired case following manual.md. The
wheel contains application code, prompts and the report template; models,
tokenizer data, forensic binaries, private configurations and acquisitions
are separate prerequisites. `uv.lock` records development dependencies; retain
a dependency freeze for any release validation environment too.

Do not fill report tables with unit-test outcomes as forensic classification
results. The actual corpus, manual baseline, human ratings, report and video
are still pending. Future-work sections may cover direct disk-image ingestion,
memory analysis, phishing/execution/privilege-escalation evidence families,
cloud isolation records, a local interface and stronger prompt-injection defenses.
