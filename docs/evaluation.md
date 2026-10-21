# Reproducible evaluation

Target six independent acquired cases, three development and three held-out,
at least ten reviewed claims each. Variants stay in the base case's split.
Freeze model digest, runtime, prompts, tokenizer/budget profile, parser versions
and configuration before held-out runs. The evaluator checks a fingerprint of
settings, prompts and prerequisite profiles. Labels stay outside case inputs.

Record action ground truth separately from expected available-evidence status.
A true action with missing evidence can correctly be unverified. Absence alone
cannot justify contradicted. Two team members independently review labels and
record resolutions. Every executable label needs exact source_sentence/start/end
anchors; generated IDs are not assumed to match the labels. Optional action,
target, negation and known relevant record IDs support separate field/retrieval
measurements.

Alignment is one-to-one. For multiple atomic claims sharing the same source span
and action, labels may specify atomic_index (zero-based order within that group).
Without an unambiguous occurrence mapping, labels count as operational errors;
one generated claim cannot satisfy several labels. Review this order against
the extracted claims during development and freeze it before held-out runs.
Target/negation values measure field correctness and are not used to select a
more favorable prediction. Failed cases contribute zero retrieved records and
remain in the known-relevant denominator. All output/input relationships across
the corpus are checked before any output directory is created.

```powershell
uv run veritrace evaluate --config veritrace.local.toml --corpus .cases/labels.json --output .runs/evaluation01
```

evaluation.json retains a four-truth-class confusion matrix with an operational
error column, macro-F1, accuracy, failure counts, tool dispatches, parser failures,
known-record retrieval and a human citation-review packet. Missing/ambiguous
claim alignments count as operational errors. Extra generated claims are reported
separately. Zero denominators yield 0 with an explicit policy note. This metric
engine is tested; **no acquired corpus or measured forensic results exist yet**.

Human reviewers rate relevance/sufficiency separately from citation identity.
Record repeated-run agreement, latency/resource observations and participant
experience. Compare a manual timeline/keyword workflow over the same available
records; counterbalance case/order where possible. Do not claim time or accuracy
improvements from unit tests or the upstream parser smoke check.
